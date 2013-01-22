# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import plcapi
import operator
import rspawn
import time
import os
import collections
import cStringIO
import resourcealloc
import socket
import sys
import logging
import ipaddr
import operator
import re

from nepi.util import server
from nepi.util import parallel

import application

import ipdb

MAX_VROUTE_ROUTES = 5

class UnresponsiveNodeError(RuntimeError):
    pass

def _castproperty(typ, propattr):
    def _get(self):
        return getattr(self, propattr)
    def _set(self, value):
        if value is not None or (isinstance(value, basestring) and not value):
            value = typ(value)
        return setattr(self, propattr, value)
    def _del(self, value):
        return delattr(self, propattr)
    _get.__name__ = propattr + '_get'
    _set.__name__ = propattr + '_set'
    _del.__name__ = propattr + '_del'
    return property(_get, _set, _del)

class Node(object):
    BASEFILTERS = {
        # Map Node attribute to plcapi filter name
        'hostname' : 'hostname',
    }
    
    TAGFILTERS = {
        # Map Node attribute to (<tag name>, <plcapi filter expression>)
        #   There are replacements that are applied with string formatting,
        #   so '%' has to be escaped as '%%'.
        'architecture' : ('arch','value'),
        'operatingSystem' : ('fcdistro','value'),
        'pl_distro' : ('pldistro','value'),
        'city' : ('city','value'),
        'country' : ('country','value'),
        'region' : ('region','value'),
        'minReliability' : ('reliability%(timeframe)s', ']value'),
        'maxReliability' : ('reliability%(timeframe)s', '[value'),
        'minBandwidth' : ('bw%(timeframe)s', ']value'),
        'maxBandwidth' : ('bw%(timeframe)s', '[value'),
        'minLoad' : ('load%(timeframe)s', ']value'),
        'maxLoad' : ('load%(timeframe)s', '[value'),
        'minCpu' : ('cpu%(timeframe)s', ']value'),
        'maxCpu' : ('cpu%(timeframe)s', '[value'),
        'reservable': ('','')
    }
    
    RATE_FACTORS = (
        # (<tag name>, <weight>, <default>)
        ('bw%(timeframe)s', -0.001, 1024.0),
        ('cpu%(timeframe)s', 0.1, 40.0),
        ('load%(timeframe)s', -0.2, 3.0),
        ('reliability%(timeframe)s', 1, 100.0),
    )
    
    DEPENDS_PIDFILE = '/tmp/nepi-depends.pid'
    DEPENDS_LOGFILE = '/tmp/nepi-depends.log'
    RPM_FUSION_URL = 'http://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-stable.noarch.rpm'
    RPM_FUSION_URL_F12 = 'http://download1.rpmfusion.org/free/fedora/releases/12/Everything/x86_64/os/rpmfusion-free-release-12-1.noarch.rpm'
    
    minReliability = _castproperty(float, '_minReliability')
    maxReliability = _castproperty(float, '_maxReliability')
    minBandwidth = _castproperty(float, '_minBandwidth')
    maxBandwidth = _castproperty(float, '_maxBandwidth')
    minCpu = _castproperty(float, '_minCpu')
    maxCpu = _castproperty(float, '_maxCpu')
    minLoad = _castproperty(float, '_minLoad')
    maxLoad = _castproperty(float, '_maxLoad')
    
    def __init__(self, api=None, sliceapi=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        self._sliceapi = sliceapi or api
        
        # Attributes
        self.hostname = None
        self.architecture = None
        self.operatingSystem = None
        self.pl_distro = None
        self.site = None
        self.city = None
        self.country = None
        self.region = None
        self.minReliability = None
        self.maxReliability = None
        self.minBandwidth = None
        self.maxBandwidth = None
        self.minCpu = None
        self.maxCpu = None
        self.minLoad = None
        self.maxLoad = None
        self.min_num_external_ifaces = None
        self.max_num_external_ifaces = None
        self._timeframe = 'w'
        
        # Applications and routes add requirements to connected nodes
        self.required_packages = set()
        self.required_vsys = set()
        self.pythonpath = []
        self.rpmFusion = False
        self.env = collections.defaultdict(list)
        
        # Some special applications - initialized when connected
        self.multicast_forwarder = None
        
        # Testbed-derived attributes
        self.slicename = None
        self.ident_path = None
        self.server_key = None
        self.home_path = None
        self.enable_proc_cleanup = False
        self.enable_home_cleanup = False
        
        # Those are filled when an actual node is allocated
        self._node_id = None
        self._yum_dependencies = None
        self._installed = False

        # Logging
        self._logger = logging.getLogger('nepi.testbeds.planetlab')

    def set_timeframe(self, timeframe):
        if timeframe == "latest":
            self._timeframe = ""
        elif timeframe == "month":
            self._timeframe = "m"
        elif timeframe == "year":
            self._timeframe = "y"
        else:
            self._timeframe = "w"

    def get_timeframe(self):
        if self._timeframe == "":
            return "latest"
        if self._timeframe == "m":
            return "month"
        if self._timeframe == "y":
            return "year"
        return "week"

    timeframe = property(get_timeframe, set_timeframe)
    
    def _nepi_testbed_environment_setup_get(self):
        command = cStringIO.StringIO()
        command.write('export PYTHONPATH=$PYTHONPATH:%s' % (
            ':'.join(["${HOME}/"+server.shell_escape(s) for s in self.pythonpath])
        ))
        command.write(' ; export PATH=$PATH:%s' % (
            ':'.join(["${HOME}/"+server.shell_escape(s) for s in self.pythonpath])
        ))
        if self.env:
            for envkey, envvals in self.env.iteritems():
                for envval in envvals:
                    command.write(' ; export %s=%s' % (envkey, envval))
        return command.getvalue()

    def _nepi_testbed_environment_setup_set(self, value):
        pass

    _nepi_testbed_environment_setup = property(
        _nepi_testbed_environment_setup_get,
        _nepi_testbed_environment_setup_set)
    
    def build_filters(self, target_filters, filter_map):
        for attr, tag in filter_map.iteritems():
            value = getattr(self, attr, None)
            if value is not None:
                target_filters[tag] = value
        return target_filters
    
    @property
    def applicable_filters(self):
        has = lambda att : getattr(self,att,None) is not None
        return (
            filter(has, self.BASEFILTERS.iterkeys())
            + filter(has, self.TAGFILTERS.iterkeys())
        )
    
    def find_candidates(self, filter_slice_id=None):
        self._logger.info("Finding candidates for %s", self.make_filter_description())
        
        fields = ('node_id',)
        replacements = {'timeframe':self._timeframe}
        
        print 1,replacements
        
        # get initial candidates (no tag filters)
        basefilters = self.build_filters({}, self.BASEFILTERS)

        print 2,basefilters

        rootfilters = basefilters.copy()

        print 3,rootfilters

        print 4,filter_slice_id

        if filter_slice_id:
            basefilters['|slice_ids'] = (filter_slice_id,)
        
        # only pick healthy nodes
        basefilters['run_level'] = 'boot'
        basefilters['boot_state'] = 'boot'
        basefilters['node_type'] = 'regular' # nepi can only handle regular nodes (for now)
        basefilters['>last_contact'] = int(time.time()) - 2*3600 # allow 5h out of contact, for timezone discrepancies

        print 5,basefilters

        # keyword-only "pseudofilters"
        extra = {}
        if self.site:
            print 6,self.site
            extra['peer'] = self.site
            
        # Solo los node_ids solo da 263 nodos, con 96 horas da 267, sacando last_contact da 809 - 20120116
        candidates = set(map(operator.itemgetter('node_id'), 
            self._sliceapi.GetNodes(filters=basefilters, fields=fields, **extra)))

        print candidates


        # filter by tag, one tag at a time
        applicable = self.applicable_filters
        print 7,applicable

        for tagfilter in self.TAGFILTERS.iteritems():
            print 8,tagfilter
            attr, (tagname, expr) = tagfilter
            print 9,attr, (tagname,expr)

            
            # don't bother if there's no filter defined
            if attr in applicable:
                print 10, attr
                tagfilter = rootfilters.copy()
                tagfilter['tagname'] = tagname % replacements
                tagfilter[expr % replacements] = str(getattr(self,attr))
                tagfilter['node_id'] = list(candidates)
                print tagfilter
        
        # and ?      
                candidates &= set(map(operator.itemgetter('node_id'),
                    self._sliceapi.GetNodeTags(filters=tagfilter, fields=fields)))

        #print candidates


        # filter by vsys tags - special case since it doesn't follow
        # the usual semantics
        if self.required_vsys:
            print 11
            newcandidates = collections.defaultdict(set)
            
            vsys_tags = self._sliceapi.GetNodeTags(
                tagname='vsys', 
                node_id = list(candidates), 
                fields = ['node_id','value'])

            print 12,vsys_tags

            vsys_tags = map(
                operator.itemgetter(['node_id','value']),
                vsys_tags)

            print 13,vsys_tags

            
            required_vsys = self.required_vsys
            for node_id, value in vsys_tags:
                if value in required_vsys:
                    newcandidates[value].add(node_id)
            
            # take only those that have all the required vsys tags
            newcandidates = reduce(
                lambda accum, new : accum & new,
                newcandidates.itervalues(),
                candidates)
        
        # filter by iface count
        if self.min_num_external_ifaces is not None or self.max_num_external_ifaces is not None:
            print 14
            # fetch interfaces for all, in one go
            filters = basefilters.copy()
            filters['node_id'] = list(candidates)
            ifaces = dict(map(operator.itemgetter('node_id','interface_ids'),
                self._sliceapi.GetNodes(filters=basefilters, fields=('node_id','interface_ids')) ))
            
            # filter candidates by interface count
            if self.min_num_external_ifaces is not None and self.max_num_external_ifaces is not None:
                predicate = ( lambda node_id : 
                    self.min_num_external_ifaces <= len(ifaces.get(node_id,())) <= self.max_num_external_ifaces )
            elif self.min_num_external_ifaces is not None:
                predicate = ( lambda node_id : 
                    self.min_num_external_ifaces <= len(ifaces.get(node_id,())) )
            else:
                predicate = ( lambda node_id : 
                    len(ifaces.get(node_id,())) <= self.max_num_external_ifaces )
            
            candidates = set(filter(predicate, candidates))
       
        # make sure hostnames are resolvable
        hostnames = dict()
        print 15, hostnames
 
        if candidates:
            self._logger.info("  Found %s candidates. Checking for reachability...", len(candidates))
           
            hostnames = dict(map(operator.itemgetter('node_id','hostname'),
                self._sliceapi.GetNodes(list(candidates), ['node_id','hostname'])
            ))
    
            print hostnames

            def resolvable(node_id):
                try:
                    addr = socket.gethostbyname(hostnames[node_id])
                    print addr
                    return addr is not None
                except:
                    return False

            candidates = set(parallel.pfilter(resolvable, candidates,
                maxthreads = 16))

            self._logger.info("  Found %s reachable candidates.", len(candidates))

            for h in hostnames.keys():
                if h not in candidates:
                    del hostnames[h]

            hostnames = dict((v,k) for k, v in hostnames.iteritems())

        return hostnames
    
    def make_filter_description(self):
        """
        Makes a human-readable description of filtering conditions
        for find_candidates.
        """
        
        # get initial candidates (no tag filters)
        filters = self.build_filters({}, self.BASEFILTERS)
        
        # keyword-only "pseudofilters"
        if self.site:
            filters['peer'] = self.site
            
        # filter by tag, one tag at a time
        applicable = self.applicable_filters
        for tagfilter in self.TAGFILTERS.iteritems():
            attr, (tagname, expr) = tagfilter
            
            # don't bother if there's no filter defined
            if attr in applicable:
                filters[attr] = getattr(self,attr)
        
        # filter by vsys tags - special case since it doesn't follow
        # the usual semantics
        if self.required_vsys:
            filters['vsys'] = ','.join(list(self.required_vsys))
        
        # filter by iface count
        if self.min_num_external_ifaces is not None or self.max_num_external_ifaces is not None:
            filters['num_ifaces'] = '-'.join([
                str(self.min_num_external_ifaces or '0'),
                str(self.max_num_external_ifaces or 'inf')
            ])
            
        return '; '.join(map('%s: %s'.__mod__,filters.iteritems()))

    def assign_node_id(self, node_id):
        self._node_id = node_id
        self.fetch_node_info()
    
    def unassign_node(self):
        self._node_id = None
        self.hostip = None
        
        try:
            orig_attrs = self.__orig_attrs
        except AttributeError:
            return
            
        for key, value in orig_attrs.iteritems():
            setattr(self, key, value)
        del self.__orig_attrs
    
    def rate_nodes(self, nodes):
        rates = collections.defaultdict(int)
        tags = collections.defaultdict(dict)
        replacements = {'timeframe':self._timeframe}
        tagnames = [ tagname % replacements 
                     for tagname, weight, default in self.RATE_FACTORS ]
       
        taginfo = self._sliceapi.GetNodeTags(
            node_id=list(nodes), 
            tagname=tagnames,
            fields=('node_id','tagname','value'))

        unpack = operator.itemgetter('node_id','tagname','value')
        for value in taginfo:
            node, tagname, value = unpack(value)
            if value and value.lower() != 'n/a':
                tags[tagname][node] = float(value)
        
        for tagname, weight, default in self.RATE_FACTORS:
            taginfo = tags[tagname % replacements].get
            for node in nodes:
                rates[node] += weight * taginfo(node,default)
        
        return map(rates.__getitem__, nodes)
            
    def fetch_node_info(self):
        orig_attrs = {}
        
        info, tags = self._sliceapi.GetNodeInfo(self._node_id)
        info = info[0]
        
        tags = dict( (t['tagname'],t['value'])
                     for t in tags )

        orig_attrs['min_num_external_ifaces'] = self.min_num_external_ifaces
        orig_attrs['max_num_external_ifaces'] = self.max_num_external_ifaces
        self.min_num_external_ifaces = None
        self.max_num_external_ifaces = None
        if not self._timeframe: self._timeframe = 'w'
        
        replacements = {'timeframe':self._timeframe}

        for attr, tag in self.BASEFILTERS.iteritems():
            if tag in info:
                value = info[tag]
                if hasattr(self, attr):
                    orig_attrs[attr] = getattr(self, attr)
                setattr(self, attr, value)
        for attr, (tag,_) in self.TAGFILTERS.iteritems():
            tag = tag % replacements
            if tag in tags:
                value = tags[tag]
                if hasattr(self, attr):
                    orig_attrs[attr] = getattr(self, attr)
                if not value or value.lower() == 'n/a':
                    value = None
                setattr(self, attr, value)
        
        if 'peer_id' in info:
            orig_attrs['site'] = self.site
            self.site = self._sliceapi.peer_map[info['peer_id']]
        
        if 'interface_ids' in info:
            self.min_num_external_ifaces = \
            self.max_num_external_ifaces = len(info['interface_ids'])
        
        if 'ssh_rsa_key' in info:
            orig_attrs['server_key'] = self.server_key
            self.server_key = info['ssh_rsa_key']
        
        self.hostip = socket.gethostbyname(self.hostname)
        
        try:
            self.__orig_attrs
        except AttributeError:
            self.__orig_attrs = orig_attrs

    def validate(self):
        if self.home_path is None:
            raise AssertionError, "Misconfigured node: missing home path"
        if self.ident_path is None or not os.access(self.ident_path, os.R_OK):
            raise AssertionError, "Misconfigured node: missing slice SSH key"
        if self.slicename is None:
            raise AssertionError, "Misconfigured node: unspecified slice"

    def recover(self):
        # Mark dependencies installed
        self._installed = True
        
        # Clear load attributes, they impair re-discovery
        self.minReliability = \
        self.maxReliability = \
        self.minBandwidth = \
        self.maxBandwidth = \
        self.minCpu = \
        self.maxCpu = \
        self.minLoad = \
        self.maxLoad = None

    def install_dependencies(self):
        if self.required_packages and not self._installed:
            # If we need rpmfusion, we must install the repo definition and the gpg keys
            if self.rpmFusion:
                if self.operatingSystem == 'f12':
                    # Fedora 12 requires a different rpmfusion package
                    RPM_FUSION_URL = self.RPM_FUSION_URL_F12
                else:
                    # This one works for f13+
                    RPM_FUSION_URL = self.RPM_FUSION_URL
                    
                rpmFusion = (
                  'rpm -q $(rpm -q -p %(RPM_FUSION_URL)s) || sudo -S rpm -i %(RPM_FUSION_URL)s'
                ) % {
                    'RPM_FUSION_URL' : RPM_FUSION_URL
                }
            else:
                rpmFusion = ''
            
            if rpmFusion:
                (out,err),proc = server.popen_ssh_command(
                    rpmFusion,
                    host = self.hostname,
                    port = None,
                    user = self.slicename,
                    agent = None,
                    ident_key = self.ident_path,
                    server_key = self.server_key,
                    timeout = 600,
                    )
                
                if proc.wait():
                    if self.check_bad_host(out,err):
                        self.blacklist()
                    raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)
            
            # Launch p2p yum dependency installer
            self._yum_dependencies.async_setup()
    
    def wait_provisioning(self, timeout = 20*60):
        # Wait for the p2p installer
        sleeptime = 1.0
        totaltime = 0.0
        while not self.is_alive():
            time.sleep(sleeptime)
            totaltime += sleeptime
            sleeptime = min(30.0, sleeptime*1.5)
            
            if totaltime > timeout:
                # PlanetLab has a 15' delay on configuration propagation
                # If we're above that delay, the unresponsiveness is not due
                # to this delay.
                if not self.is_alive(verbose=True):
                    raise UnresponsiveNodeError, "Unresponsive host %s" % (self.hostname,)
        
        # Ensure the node is clean (no apps running that could interfere with operations)
        if self.enable_proc_cleanup:
            self.do_proc_cleanup()
        if self.enable_home_cleanup:
            self.do_home_cleanup()
   
    def wait_dependencies(self, pidprobe=1, probe=0.5, pidmax=10, probemax=10):
        # Wait for the p2p installer
        if self._yum_dependencies and not self._installed:
            self._yum_dependencies.async_setup_wait()
            self._installed = True
        
    def is_alive(self, verbose = False):
        # Make sure all the paths are created where 
        # they have to be created for deployment
        (out,err),proc = server.eintr_retry(server.popen_ssh_command)(
            "echo 'ALIVE'",
            host = self.hostname,
            port = None,
            user = self.slicename,
            agent = None,
            ident_key = self.ident_path,
            server_key = self.server_key,
            timeout = 60,
            err_on_timeout = False,
            persistent = False
            )
        
        if proc.wait():
            if verbose:
                self._logger.warn("Unresponsive node %s got:\n%s%s", self.hostname, out, err)
            return False
        elif not err and out.strip() == 'ALIVE':
            return True
        else:
            if verbose:
                self._logger.warn("Unresponsive node %s got:\n%s%s", self.hostname, out, err)
            return False
    
    def destroy(self):
        if self.enable_proc_cleanup:
            self.do_proc_cleanup()
        if self.enable_home_cleanup:
            self.do_home_cleanup()
    
    def blacklist(self):
        if self._node_id:
            self._logger.warn("Blacklisting malfunctioning node %s", self.hostname)
            import util
            util.appendBlacklist(self.hostname)
    
    def do_proc_cleanup(self):
        if self.testbed().recovering:
            # WOW - not now
            return
            
        self._logger.info("Cleaning up processes on %s", self.hostname)
        
        cmds = [
            "sudo -S killall python tcpdump || /bin/true ; "
            "sudo -S killall python tcpdump || /bin/true ; "
            "sudo -S kill $(ps -N -T -o pid --no-heading | grep -v $PPID | sort) || /bin/true ",
            "sudo -S killall -u %(slicename)s || /bin/true ",
            "sudo -S killall -u root || /bin/true ",
            "sudo -S killall -u %(slicename)s || /bin/true ",
            "sudo -S killall -u root || /bin/true ",
        ]

        for cmd in cmds:
            (out,err),proc = server.popen_ssh_command(
                # Some apps need two kills
                cmd % {
                    'slicename' : self.slicename ,
                },
                host = self.hostname,
                port = None,
                user = self.slicename,
                agent = None,
                ident_key = self.ident_path,
                server_key = self.server_key,
                tty = True, # so that ps -N -T works as advertised...
                timeout = 60,
                retry = 3
                )
            proc.wait()
     
    def do_home_cleanup(self):
        if self.testbed().recovering:
            # WOW - not now
            return
            
        self._logger.info("Cleaning up home on %s", self.hostname)
        
        cmds = [
            "find . -maxdepth 1 ! -name '.bash*' ! -name '.' -execdir rm -rf {} + "
        ]

        for cmd in cmds:
            (out,err),proc = server.popen_ssh_command(
                # Some apps need two kills
                cmd % {
                    'slicename' : self.slicename ,
                },
                host = self.hostname,
                port = None,
                user = self.slicename,
                agent = None,
                ident_key = self.ident_path,
                server_key = self.server_key,
                tty = True, # so that ps -N -T works as advertised...
                timeout = 60,
                retry = 3
                )
            proc.wait()
   
    def prepare_dependencies(self):
        # Configure p2p yum dependency installer
        if self.required_packages and not self._installed:
            self._yum_dependencies = application.YumDependency(self._api)
            self._yum_dependencies.node = self
            self._yum_dependencies.home_path = "nepi-yumdep"
            self._yum_dependencies.depends = ' '.join(self.required_packages)

    def routing_method(self, routes, vsys_vnet):
        """
        There are two methods, vroute and sliceip.
        
        vroute:
            Modifies the node's routing table directly, validating that the IP
            range lies within the network given by the slice's vsys_vnet tag.
            This method is the most scalable for very small routing tables
            that need not modify other routes (including the default)
        
        sliceip:
            Uses policy routing and iptables filters to create per-sliver
            routing tables. It's the most flexible way, but it doesn't scale
            as well since only 155 routing tables can be created this way.
        
        This method will return the most appropriate routing method, which will
        prefer vroute for small routing tables.
        """
        
        # For now, sliceip results in kernel panics
        # so we HAVE to use vroute
        return 'vroute'
        
        # We should not make the routing table grow too big
        if len(routes) > MAX_VROUTE_ROUTES:
            return 'sliceip'
        
        vsys_vnet = ipaddr.IPv4Network(vsys_vnet)
        for route in routes:
            dest, prefix, nexthop, metric, device = route
            dest = ipaddr.IPv4Network("%s/%d" % (dest,prefix))
            nexthop = ipaddr.IPAddress(nexthop)
            if dest not in vsys_vnet or nexthop not in vsys_vnet:
                return 'sliceip'
        
        return 'vroute'
    
    def format_route(self, route, dev, method, action):
        dest, prefix, nexthop, metric, device = route
        if method == 'vroute':
            return (
                "%s %s%s gw %s %s" % (
                    action,
                    dest,
                    (("/%d" % (prefix,)) if prefix and prefix != 32 else ""),
                    nexthop,
                    dev,
                )
            )
        elif method == 'sliceip':
            return (
                "route %s to %s%s via %s metric %s dev %s" % (
                    action,
                    dest,
                    (("/%d" % (prefix,)) if prefix and prefix != 32 else ""),
                    nexthop,
                    metric or 1,
                    dev,
                )
            )
        else:
            raise AssertionError, "Unknown method"
    
    def _annotate_routes_with_devs(self, routes, devs, method):
        dev_routes = []
        for route in routes:
            for dev in devs:
                if dev.routes_here(route):
                    dev_routes.append(tuple(route) + (dev.if_name,))
                    
                    # Stop checking
                    break
            else:
                if method == 'sliceip':
                    dev_routes.append(tuple(route) + ('eth0',))
                else:
                    raise RuntimeError, "Route %s cannot be bound to any virtual interface " \
                        "- PL can only handle rules over virtual interfaces. Candidates are: %s" % (route,devs)
        return dev_routes
    
    def configure_routes(self, routes, devs, vsys_vnet):
        """
        Add the specified routes to the node's routing table
        """
        rules = []
        method = self.routing_method(routes, vsys_vnet)
        tdevs = set()
        
        # annotate routes with devices
        dev_routes = self._annotate_routes_with_devs(routes, devs, method)
        for route in dev_routes:
            route, dev = route[:-1], route[-1]
            
            # Schedule rule
            tdevs.add(dev)
            rules.append(self.format_route(route, dev, method, 'add'))
        
        if method == 'sliceip':
            rules = map('enable '.__add__, tdevs) + rules
        
        self._logger.info("Setting up routes for %s using %s", self.hostname, method)
        self._logger.debug("Routes for %s:\n\t%s", self.hostname, '\n\t'.join(rules))
        
        self.apply_route_rules(rules, method)
        
        self._configured_routes = set(routes)
        self._configured_devs = tdevs
        self._configured_method = method
    
    def reconfigure_routes(self, routes, devs, vsys_vnet):
        """
        Updates the routes in the node's routing table to match
        the given route list
        """
        method = self._configured_method
        
        dev_routes = self._annotate_routes_with_devs(routes, devs, method)

        current = self._configured_routes
        current_devs = self._configured_devs
        
        new = set(dev_routes)
        new_devs = set(map(operator.itemgetter(-1), dev_routes))
        
        deletions = current - new
        insertions = new - current
        
        dev_deletions = current_devs - new_devs
        dev_insertions = new_devs - current_devs
        
        # Generate rules
        rules = []
        
        # Rule deletions first
        for route in deletions:
            route, dev = route[:-1], route[-1]
            rules.append(self.format_route(route, dev, method, 'del'))
        
        if method == 'sliceip':
            # Dev deletions now
            rules.extend(map('disable '.__add__, dev_deletions))

            # Dev insertions now
            rules.extend(map('enable '.__add__, dev_insertions))

        # Rule insertions now
        for route in insertions:
            route, dev = route[:-1], dev[-1]
            rules.append(self.format_route(route, dev, method, 'add'))
        
        # Apply
        self.apply_route_rules(rules, method)
        
        self._configured_routes = dev_routes
        self._configured_devs = new_devs
        
    def apply_route_rules(self, rules, method):
        (out,err),proc = server.popen_ssh_command(
            "( sudo -S bash -c 'cat /vsys/%(method)s.out >&2' & ) ; sudo -S bash -c 'cat > /vsys/%(method)s.in' ; sleep 0.5" % dict(
                home = server.shell_escape(self.home_path),
                method = method),
            host = self.hostname,
            port = None,
            user = self.slicename,
            agent = None,
            ident_key = self.ident_path,
            server_key = self.server_key,
            stdin = '\n'.join(rules),
            timeout = 300
            )
        
        if proc.wait() or err:
            raise RuntimeError, "Could not set routes (%s) errors: %s%s" % (rules,out,err)
        elif out or err:
            logger.debug("%s said: %s%s", method, out, err)

    def check_bad_host(self, out, err):
        badre = re.compile(r'(?:'
                           r"curl: [(]\d+[)] Couldn't resolve host 'download1[.]rpmfusion[.]org'"
                           r'|Error: disk I/O error'
                           r')', 
                           re.I)
        return badre.search(out) or badre.search(err)
