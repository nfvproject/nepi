#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import testbed_impl
from nepi.core.metadata import Parallel
from nepi.util.constants import TIME_NOW
from nepi.util.graphtools import mst
from nepi.util import ipaddr2
from nepi.util import environ
from nepi.util.parallel import ParallelRun
import sys
import os
import os.path
import time
import resourcealloc
import collections
import operator
import functools
import socket
import struct
import tempfile
import subprocess
import random
import shutil
import logging
import metadata

class TempKeyError(Exception):
    pass

class TestbedController(testbed_impl.TestbedController):
    def __init__(self):
        super(TestbedController, self).__init__(TESTBED_ID, TESTBED_VERSION)
        self._home_directory = None
        self.slicename = None
        self._traces = dict()

        import node, interfaces, application
        self._node = node
        self._interfaces = interfaces
        self._app = application
        
        self._blacklist = set()
        self._just_provisioned = set()
        
        self._load_blacklist()
        
        self._logger = logging.getLogger('nepi.testbeds.planetlab')

    @property
    def home_directory(self):
        return self._home_directory

    @property
    def plapi(self):
        if not hasattr(self, '_plapi'):
            import plcapi

            if self.authUser:
                self._plapi = plcapi.PLCAPI(
                    username = self.authUser,
                    password = self.authString,
                    hostname = self.plcHost,
                    urlpattern = self.plcUrl
                    )
            else:
                # anonymous access - may not be enough for much
                self._plapi = plcapi.PLCAPI()
        return self._plapi

    @property
    def slice_id(self):
        if not hasattr(self, '_slice_id'):
            slices = self.plapi.GetSlices(self.slicename, fields=('slice_id',))
            if slices:
                self._slice_id = slices[0]['slice_id']
            else:
                # If it wasn't found, don't remember this failure, keep trying
                return None
        return self._slice_id
    
    @property
    def vsys_vnet(self):
        if not hasattr(self, '_vsys_vnet'):
            slicetags = self.plapi.GetSliceTags(
                name = self.slicename,
                tagname = 'vsys_vnet',
                fields=('value',))
            if slicetags:
                self._vsys_vnet = slicetags[0]['value']
            else:
                # If it wasn't found, don't remember this failure, keep trying
                return None
        return self._vsys_vnet
    
    def _load_blacklist(self):
        blpath = environ.homepath('plblacklist')
        
        try:
            bl = open(blpath, "r")
        except:
            self._blacklist = set()
            return
            
        try:
            self._blacklist = set(
                map(int,
                    map(str.strip, bl.readlines())
                )
            )
        finally:
            bl.close()
    
    def _save_blacklist(self):
        blpath = environ.homepath('plblacklist')
        bl = open(blpath, "w")
        try:
            bl.writelines(
                map('%s\n'.__mod__, self._blacklist))
        finally:
            bl.close()
    
    def do_setup(self):
        self._home_directory = self._attributes.\
            get_attribute_value("homeDirectory")
        self.slicename = self._attributes.\
            get_attribute_value("slice")
        self.authUser = self._attributes.\
            get_attribute_value("authUser")
        self.authString = self._attributes.\
            get_attribute_value("authPass")
        self.sliceSSHKey = self._attributes.\
            get_attribute_value("sliceSSHKey")
        self.sliceSSHKeyPass = None
        self.plcHost = self._attributes.\
            get_attribute_value("plcHost")
        self.plcUrl = self._attributes.\
            get_attribute_value("plcUrl")
        self.logLevel = self._attributes.\
            get_attribute_value("plLogLevel")
        self.tapPortBase = self._attributes.\
            get_attribute_value("tapPortBase")
        self.p2pDeployment = self._attributes.\
            get_attribute_value("p2pDeployment")
        self.dedicatedSlice = self._attributes.\
            get_attribute_value("dedicatedSlice")
        
        self._logger.setLevel(getattr(logging,self.logLevel))
        
        super(TestbedController, self).do_setup()

    def do_post_asynclaunch(self, guid):
        # Dependencies were launched asynchronously,
        # so wait for them
        dep = self._elements[guid]
        if isinstance(dep, self._app.Dependency):
            dep.async_setup_wait()
    
    # Two-phase configuration for asynchronous launch
    do_poststep_preconfigure = staticmethod(do_post_asynclaunch)
    do_poststep_configure = staticmethod(do_post_asynclaunch)

    def do_preconfigure(self):
        while True:
            # Perform resource discovery if we don't have
            # specific resources assigned yet
            self.do_resource_discovery()

            # Create PlanetLab slivers
            self.do_provisioning()
            
            try:
                # Wait for provisioning
                self.do_wait_nodes()
                
                # Okkey...
                break
            except self._node.UnresponsiveNodeError:
                # Oh... retry...
                pass
        
        if self.p2pDeployment:
            # Plan application deployment
            self.do_spanning_deployment_plan()

        # Configure elements per XML data
        super(TestbedController, self).do_preconfigure()

    def do_resource_discovery(self, recover = False):
        to_provision = self._to_provision = set()
        
        reserved = set(self._blacklist)
        for guid, node in self._elements.iteritems():
            if isinstance(node, self._node.Node) and node._node_id is not None:
                reserved.add(node._node_id)
        
        # Initial algo:
        #   look for perfectly defined nodes
        #   (ie: those with only one candidate)
        for guid, node in self._elements.iteritems():
            if isinstance(node, self._node.Node) and node._node_id is None:
                # Try existing nodes first
                # If we have only one candidate, simply use it
                candidates = node.find_candidates(
                    filter_slice_id = self.slice_id)
                candidates -= reserved
                if len(candidates) == 1:
                    node_id = iter(candidates).next()
                    node.assign_node_id(node_id)
                    reserved.add(node_id)
                elif not candidates:
                    # Try again including unassigned nodes
                    candidates = node.find_candidates()
                    candidates -= reserved
                    if len(candidates) > 1:
                        continue
                    if len(candidates) == 1:
                        node_id = iter(candidates).next()
                        node.assign_node_id(node_id)
                        to_provision.add(node_id)
                        reserved.add(node_id)
                    elif not candidates:
                        raise RuntimeError, "Cannot assign resources for node %s, no candidates sith %s" % (guid,
                            node.make_filter_description())
        
        # Now do the backtracking search for a suitable solution
        # First with existing slice nodes
        reqs = []
        nodes = []
        for guid, node in self._elements.iteritems():
            if isinstance(node, self._node.Node) and node._node_id is None:
                # Try existing nodes first
                # If we have only one candidate, simply use it
                candidates = node.find_candidates(
                    filter_slice_id = self.slice_id)
                candidates -= reserved
                reqs.append(candidates)
                nodes.append(node)
        
        if nodes and reqs:
            if recover:
                raise RuntimeError, "Impossible to recover: unassigned host for Nodes %r" % (nodes,)
            
            try:
                solution = resourcealloc.alloc(reqs)
            except resourcealloc.ResourceAllocationError:
                # Failed, try again with all nodes
                reqs = []
                for node in nodes:
                    candidates = node.find_candidates()
                    candidates -= reserved
                    reqs.append(candidates)
                
                solution = resourcealloc.alloc(reqs)
                to_provision.update(solution)
            
            # Do assign nodes
            for node, node_id in zip(nodes, solution):
                node.assign_node_id(node_id)

    def do_provisioning(self):
        if self._to_provision:
            # Add new nodes to the slice
            cur_nodes = self.plapi.GetSlices(self.slicename, ['node_ids'])[0]['node_ids']
            new_nodes = list(set(cur_nodes) | self._to_provision)
            self.plapi.UpdateSlice(self.slicename, nodes=new_nodes)

        # cleanup
        self._just_provisioned = self._to_provision
        del self._to_provision
    
    def do_wait_nodes(self):
        for guid, node in self._elements.iteritems():
            if isinstance(node, self._node.Node):
                # Just inject configuration stuff
                node.home_path = "nepi-node-%s" % (guid,)
                node.ident_path = self.sliceSSHKey
                node.slicename = self.slicename
            
                # Show the magic
                self._logger.info("PlanetLab Node %s configured at %s", guid, node.hostname)
            
        try:
            for guid, node in self._elements.iteritems():
                if isinstance(node, self._node.Node):
                    self._logger.info("Waiting for Node %s configured at %s", guid, node.hostname)
                    
                    node.wait_provisioning(
                        (20*60 if node._node_id in self._just_provisioned else 60)
                    )
                    
                    self._logger.info("READY Node %s at %s", guid, node.hostname)
                    
                    # Prepare dependency installer now
                    node.prepare_dependencies()
        except self._node.UnresponsiveNodeError:
            # Uh... 
            self._logger.warn("UNRESPONSIVE Node %s", node.hostname)
            
            # Mark all dead nodes (which are unresponsive) on the blacklist
            # and re-raise
            for guid, node in self._elements.iteritems():
                if isinstance(node, self._node.Node):
                    if not node.is_alive():
                        self._logger.warn("Blacklisting %s for unresponsiveness", node.hostname)
                        self._blacklist.add(node._node_id)
                        node.unassign_node()
            
            try:
                self._save_blacklist()
            except:
                # not important...
                import traceback
                traceback.print_exc()
            
            raise
    
    def do_spanning_deployment_plan(self):
        # Create application groups by collecting all applications
        # based on their hash - the hash should contain everything that
        # defines them and the platform they're built
        
        def dephash(app):
            return (
                frozenset((app.depends or "").split(' ')),
                frozenset((app.sources or "").split(' ')),
                app.build,
                app.install,
                app.node.architecture,
                app.node.operatingSystem,
                app.node.pl_distro,
            )
        
        depgroups = collections.defaultdict(list)
        
        for element in self._elements.itervalues():
            if isinstance(element, self._app.Dependency):
                depgroups[dephash(element)].append(element)
            elif isinstance(element, self._node.Node):
                deps = element._yum_dependencies
                if deps:
                    depgroups[dephash(deps)].append(deps)
        
        # Set up spanning deployment for those applications that
        # have been deployed in several nodes.
        for dh, group in depgroups.iteritems():
            if len(group) > 1:
                # Pick root (deterministically)
                root = min(group, key=lambda app:app.node.hostname)
                
                # Obtain all IPs in numeric format
                # (which means faster distance computations)
                for dep in group:
                    dep._ip = socket.gethostbyname(dep.node.hostname)
                    dep._ip_n = struct.unpack('!L', socket.inet_aton(dep._ip))[0]
                
                # Compute plan
                # NOTE: the plan is an iterator
                plan = mst.mst(
                    group,
                    lambda a,b : ipaddr2.ipdistn(a._ip_n, b._ip_n),
                    root = root,
                    maxbranching = 2)
                
                # Re-sign private key
                try:
                    tempprk, temppuk, tmppass = self._make_temp_private_key()
                except TempKeyError:
                    continue
                
                # Set up slaves
                plan = list(plan)
                for slave, master in plan:
                    slave.set_master(master)
                    slave.install_keys(tempprk, temppuk, tmppass)
                    
        # We don't need the user's passphrase anymore
        self.sliceSSHKeyPass = None
    
    def _make_temp_private_key(self):
        # Get the user's key's passphrase
        if not self.sliceSSHKeyPass:
            if 'SSH_ASKPASS' in os.environ:
                proc = subprocess.Popen(
                    [ os.environ['SSH_ASKPASS'],
                      "Please type the passphrase for the %s SSH identity file. "
                      "The passphrase will be used to re-cipher the identity file with "
                      "a random 256-bit key for automated chain deployment on the "
                      "%s PlanetLab slice" % ( 
                        os.path.basename(self.sliceSSHKey), 
                        self.slicename
                    ) ],
                    stdin = open("/dev/null"),
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE)
                out,err = proc.communicate()
                self.sliceSSHKeyPass = out.strip()
        
        if not self.sliceSSHKeyPass:
            raise TempKeyError
        
        # Create temporary key files
        prk = tempfile.NamedTemporaryFile(
            dir = self.root_directory,
            prefix = "pl_deploy_tmpk_",
            suffix = "")

        puk = tempfile.NamedTemporaryFile(
            dir = self.root_directory,
            prefix = "pl_deploy_tmpk_",
            suffix = ".pub")
            
        # Create secure 256-bits temporary passphrase
        passphrase = ''.join(map(chr,[rng.randint(0,255) 
                                      for rng in (random.SystemRandom(),)
                                      for i in xrange(32)] )).encode("hex")
                
        # Copy keys
        oprk = open(self.sliceSSHKey, "rb")
        opuk = open(self.sliceSSHKey+".pub", "rb")
        shutil.copymode(oprk.name, prk.name)
        shutil.copymode(opuk.name, puk.name)
        shutil.copyfileobj(oprk, prk)
        shutil.copyfileobj(opuk, puk)
        prk.flush()
        puk.flush()
        oprk.close()
        opuk.close()
        
        # A descriptive comment
        comment = "%s#NEPI_INTERNAL@%s" % (self.authUser, self.slicename)
        
        # Recipher keys
        proc = subprocess.Popen(
            ["ssh-keygen", "-p",
             "-f", prk.name,
             "-P", self.sliceSSHKeyPass,
             "-N", passphrase,
             "-C", comment ],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            stdin = subprocess.PIPE
        )
        out, err = proc.communicate()
        
        if err:
            raise RuntimeError, "Problem generating keys: \n%s\n%r" % (
                out, err)
        
        prk.seek(0)
        puk.seek(0)
        
        # Change comment on public key
        puklines = puk.readlines()
        puklines[0] = puklines[0].split(' ')
        puklines[0][-1] = comment+'\n'
        puklines[0] = ' '.join(puklines[0])
        puk.seek(0)
        puk.truncate()
        puk.writelines(puklines)
        del puklines
        puk.flush()
        
        return prk, puk, passphrase
    
    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        # TODO: take on account schedule time for the task
        element = self._elements[guid]
        if element:
            setattr(element, name, value)

            if hasattr(element, 'refresh'):
                # invoke attribute refresh hook
                element.refresh()

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        element = self._elements.get(guid)
        try:
            return getattr(element, name)
        except (KeyError, AttributeError):
            return value

    def get_address(self, guid, index, attribute='Address'):
        index = int(index)

        # try the real stuff
        iface = self._elements.get(guid)
        if iface and index == 0:
            if attribute == 'Address':
                return iface.address
            elif attribute == 'NetPrefix':
                return iface.netprefix
            elif attribute == 'Broadcast':
                return iface.broadcast

        # if all else fails, query box
        return super(TestbedController, self).get_address(guid, index, attribute)

    def action(self, time, guid, action):
        raise NotImplementedError

    def shutdown(self):
        for trace in self._traces.itervalues():
            trace.close()
        
        def invokeif(action, testbed, guid):
            element = self._elements[guid]
            if hasattr(element, action):
                getattr(element, action)()
        
        self._do_in_factory_order(
            functools.partial(invokeif, 'cleanup'),
            metadata.shutdown_order)

        self._do_in_factory_order(
            functools.partial(invokeif, 'destroy'),
            metadata.shutdown_order)
            
        self._elements.clear()
        self._traces.clear()

    def trace(self, guid, trace_id, attribute='value'):
        app = self._elements[guid]

        if attribute == 'value':
            path = app.sync_trace(self.home_directory, trace_id)
            if path:
                fd = open(path, "r")
                content = fd.read()
                fd.close()
            else:
                content = None
        elif attribute == 'path':
            content = app.remote_trace_path(trace_id)
        else:
            content = None
        return content

    def follow_trace(self, trace_id, trace):
        self._traces[trace_id] = trace

    def recover(self):
        # Create and connect do not perform any real tasks against
        # the nodes, it only sets up the object hierarchy,
        # so we can run them normally
        self.do_create()
        self.do_connect_init()
        self.do_connect_compl()
        
        # Manually recover nodes, to mark dependencies installed
        # and clean up mutable attributes
        self._do_in_factory_order(
            lambda self, guid : self._elements[guid].recover(), 
            [
                metadata.NODE,
            ])
        
        # Assign nodes - since we're working off exeucte XML, nodes
        # have specific hostnames assigned and we don't need to do
        # real assignment, only find out node ids and check liveliness
        self.do_resource_discovery(recover = True)
        self.do_wait_nodes()
        
        # Pre/post configure, however, tends to set up tunnels
        # Execute configuration steps only for those object
        # kinds that do not have side effects
        
        # Do the ones without side effects,
        # including nodes that need to set up home 
        # folders and all that
        self._do_in_factory_order(
            "preconfigure_function", 
            [
                metadata.INTERNET,
                Parallel(metadata.NODE),
                metadata.NODEIFACE,
            ])
        
        # Tunnels require a home path that is configured
        # at this step. Since we cannot run the step itself,
        # we need to inject this homepath ourselves
        for guid, element in self._elements.iteritems():
            if isinstance(element, self._interfaces.TunIface):
                element._home_path = "tun-%s" % (guid,)
        
        # Manually recover tunnels, applications and
        # netpipes, negating the side effects
        self._do_in_factory_order(
            lambda self, guid : self._elements[guid].recover(), 
            [
                Parallel(metadata.TAPIFACE),
                Parallel(metadata.TUNIFACE),
                metadata.NETPIPE,
                Parallel(metadata.NEPIDEPENDENCY),
                Parallel(metadata.NS3DEPENDENCY),
                Parallel(metadata.DEPENDENCY),
                Parallel(metadata.APPLICATION),
            ])

        # Tunnels are not harmed by configuration after
        # recovery, and some attributes get set this way
        # like external_iface
        self._do_in_factory_order(
            "preconfigure_function", 
            [
                Parallel(metadata.TAPIFACE),
                Parallel(metadata.TUNIFACE),
            ])

        # Post-do the ones without side effects
        self._do_in_factory_order(
            "configure_function", 
            [
                metadata.INTERNET,
                Parallel(metadata.NODE),
                metadata.NODEIFACE,
                Parallel(metadata.TAPIFACE),
                Parallel(metadata.TUNIFACE),
            ])
        
        # There are no required prestart steps
        # to call upon recovery, so we're done
        
    
    def _make_generic(self, parameters, kind):
        app = kind(self.plapi)

        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr,val in parameters.iteritems():
            setattr(app, attr, val)

        return app

    def _make_node(self, parameters):
        node = self._make_generic(parameters, self._node.Node)
        node.enable_cleanup = self.dedicatedSlice
        return node

    def _make_node_iface(self, parameters):
        return self._make_generic(parameters, self._interfaces.NodeIface)

    def _make_tun_iface(self, parameters):
        return self._make_generic(parameters, self._interfaces.TunIface)

    def _make_tap_iface(self, parameters):
        return self._make_generic(parameters, self._interfaces.TapIface)

    def _make_netpipe(self, parameters):
        return self._make_generic(parameters, self._interfaces.NetPipe)

    def _make_internet(self, parameters):
        return self._make_generic(parameters, self._interfaces.Internet)

    def _make_application(self, parameters):
        return self._make_generic(parameters, self._app.Application)

    def _make_dependency(self, parameters):
        return self._make_generic(parameters, self._app.Dependency)

    def _make_nepi_dependency(self, parameters):
        return self._make_generic(parameters, self._app.NepiDependency)

    def _make_ns3_dependency(self, parameters):
        return self._make_generic(parameters, self._app.NS3Dependency)

