#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import plcapi
import operator
import rspawn
import time
import os
import collections

from nepi.util import server

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
        'operating_system' : ('fcdistro','value'),
        'pl_distro' : ('pldistro','value'),
        'min_reliability' : ('reliability%(timeframe)s', ']value'),
        'max_reliability' : ('reliability%(timeframe)s', '[value'),
        'min_bandwidth' : ('bw%(timeframe)s', ']value'),
        'max_bandwidth' : ('bw%(timeframe)s', '[value'),
    }    
    
    DEPENDS_PIDFILE = '/tmp/nepi-depends.pid'
    DEPENDS_LOGFILE = '/tmp/nepi-depends.log'
    
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        
        # Attributes
        self.hostname = None
        self.architecture = None
        self.operating_system = None
        self.pl_distro = None
        self.site = None
        self.emulation = None
        self.min_reliability = None
        self.max_reliability = None
        self.min_bandwidth = None
        self.max_bandwidth = None
        self.min_num_external_ifaces = None
        self.max_num_external_ifaces = None
        self.timeframe = 'm'
        
        # Applications and routes add requirements to connected nodes
        self.required_packages = set()
        self.required_vsys = set()
        
        # Testbed-derived attributes
        self.slicename = None
        self.ident_path = None
        self.server_key = None
        self.home_path = None
        
        # Those are filled when an actual node is allocated
        self._node_id = None
    
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
        fields = ('node_id',)
        replacements = {'timeframe':self.timeframe}
        
        # get initial candidates (no tag filters)
        basefilters = self.build_filters({}, self.BASEFILTERS)
        if filter_slice_id:
            basefilters['|slice_ids'] = (filter_slice_id,)
        
        # keyword-only "pseudofilters"
        extra = {}
        if self.site:
            extra['peer'] = self.site
            
        candidates = set(map(operator.itemgetter('node_id'), 
            self._api.GetNodes(filters=basefilters, fields=fields, **extra)))
        
        # filter by tag, one tag at a time
        applicable = self.applicable_filters
        for tagfilter in self.TAGFILTERS.iteritems():
            attr, (tagname, expr) = tagfilter
            
            # don't bother if there's no filter defined
            if attr in applicable:
                tagfilter = basefilters.copy()
                tagfilter['tagname'] = tagname % replacements
                tagfilter[expr % replacements] = getattr(self,attr)
                tagfilter['node_id'] = list(candidates)
                
                candidates &= set(map(operator.itemgetter('node_id'),
                    self._api.GetNodeTags(filters=tagfilter, fields=fields)))
        
        # filter by vsys tags - special case since it doesn't follow
        # the usual semantics
        if self.required_vsys:
            newcandidates = collections.defaultdict(set)
            
            vsys_tags = self._api.GetNodeTags(
                tagname='vsys', 
                node_id = list(candidates), 
                fields = ['node_id','value'])
            
            vsys_tags = map(
                operator.itemgetter(['node_id','value']),
                vsys_tags)
            
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
            # fetch interfaces for all, in one go
            filters = basefilters.copy()
            filters['node_id'] = list(candidates)
            ifaces = dict(map(operator.itemgetter('node_id','interface_ids'),
                self._api.GetNodes(filters=basefilters, fields=('node_id','interface_ids')) ))
            
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
            
        return candidates

    def assign_node_id(self, node_id):
        self._node_id = node_id
        self.fetch_node_info()
    
    def fetch_node_info(self):
        info = self._api.GetNodes(self._node_id)[0]
        tags = dict( (t['tagname'],t['value'])
                     for t in self._api.GetNodeTags(node_id=self._node_id, fields=('tagname','value')) )

        self.min_num_external_ifaces = None
        self.max_num_external_ifaces = None
        self.timeframe = 'm'
        
        replacements = {'timeframe':self.timeframe}
        for attr, tag in self.BASEFILTERS.iteritems():
            if tag in info:
                value = info[tag]
                setattr(self, attr, value)
        for attr, (tag,_) in self.TAGFILTERS.iteritems():
            tag = tag % replacements
            if tag in tags:
                value = tags[tag]
                setattr(self, attr, value)
        
        if 'peer_id' in info:
            self.site = self._api.peer_map[info['peer_id']]
        
        if 'interface_ids' in info:
            self.min_num_external_ifaces = \
            self.max_num_external_ifaces = len(info['interface_ids'])
        
        if 'ssh_rsa_key' in info:
            self.server_key = info['ssh_rsa_key']

    def validate(self):
        if self.home_path is None:
            raise AssertionError, "Misconfigured node: missing home path"
        if self.ident_path is None or not os.access(self.ident_path, os.R_OK):
            raise AssertionError, "Misconfigured node: missing slice SSH key"
        if self.slicename is None:
            raise AssertionError, "Misconfigured node: unspecified slice"

    def install_dependencies(self):
        if self.required_packages:
            # TODO: make dependant on the experiment somehow...
            pidfile = self.DEPENDS_PIDFILE
            logfile = self.DEPENDS_LOGFILE
            
            # Start process in a "daemonized" way, using nohup and heavy
            # stdin/out redirection to avoid connection issues
            (out,err),proc = rspawn.remote_spawn(
                "yum -y install %(packages)s" % {
                    'packages' : ' '.join(self.required_packages),
                },
                pidfile = pidfile,
                stdout = logfile,
                stderr = rspawn.STDOUT,
                
                host = self.hostname,
                port = None,
                user = self.slicename,
                agent = None,
                ident_key = self.ident_path,
                server_key = self.server_key,
                sudo = True
                )
            
            if proc.wait():
                raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)
    
    def wait_dependencies(self, pidprobe=1, probe=0.5, pidmax=10, probemax=10):
        if self.required_packages:
            pidfile = self.DEPENDS_PIDFILE
            
            # get PID
            pid = ppid = None
            for probenum in xrange(pidmax):
                pidtuple = rspawn.remote_check_pid(
                    pidfile = pidfile,
                    host = self.hostname,
                    port = None,
                    user = self.slicename,
                    agent = None,
                    ident_key = self.ident_path,
                    server_key = self.server_key
                    )
                if pidtuple:
                    pid, ppid = pidtuple
                    break
                else:
                    time.sleep(pidprobe)
            else:
                raise RuntimeError, "Failed to obtain pidfile for dependency installer"
        
            # wait for it to finish
            while rspawn.RUNNING is rspawn.remote_status(
                    pid, ppid,
                    host = self.hostname,
                    port = None,
                    user = self.slicename,
                    agent = None,
                    ident_key = self.ident_path,
                    server_key = self.server_key
                    ):
                time.sleep(probe)
                probe = min(probemax, 1.5*probe)
        
    def is_alive(self):
        # Make sure all the paths are created where 
        # they have to be created for deployment
        (out,err),proc = server.popen_ssh_command(
            "echo 'ALIVE'",
            host = self.hostname,
            port = None,
            user = self.slicename,
            agent = None,
            ident_key = self.ident_path,
            server_key = self.server_key
            )
        
        if proc.wait():
            return False
        elif not err and out.strip() == 'ALIVE':
            return True
        else:
            return False
    

