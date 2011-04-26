#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
import os
import time

class TestbedController(testbed_impl.TestbedController):
    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)
        self._home_directory = None
        self.slicename = None
        self._traces = dict()
        
        import node, interfaces, application
        self._node = node
        self._interfaces = interfaces
        self._app = application

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
                    password = self.authString)
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

    def do_preconfigure(self):
        # Perform resource discovery if we don't have
        # specific resources assigned yet
        self.do_resource_discovery()
        
        # Create PlanetLab slivers
        self.do_provisioning()
        
        # Configure elements per XML data
        super(TestbedController, self).do_preconfigure()
    
    def do_resource_discovery(self):
        # Do what?
        
        # Provisional algo:
        #   look for perfectly defined nodes
        #   (ie: those with only one candidate)
        to_provision = self._to_provision = set()
        for guid, node in self._elements.iteritems():
            if isinstance(node, self._node.Node) and node._node_id is None:
                # Try existing nodes first
                # If we have only one candidate, simply use it
                candidates = node.find_candidates(
                    filter_slice_id = self.slice_id)
                if len(candidates) == 1:
                    node.assign_node_id(iter(candidates).next())
                else:
                    # Try again including unassigned nodes
                    candidates = node.find_candidates()
                    if len(candidates) > 1:
                        raise RuntimeError, "Cannot assign resources for node %s, too many candidates" % (guid,)
                    if len(candidates) == 1:
                        node_id = iter(candidates).next()
                        node.assign_node_id(node_id)
                        to_provision.add(node_id)
                    elif not candidates:
                        raise RuntimeError, "Cannot assign resources for node %s, no candidates" % (guid,)

    def do_provisioning(self):
        if self._to_provision:
            # Add new nodes to the slice
            cur_nodes = self.plapi.GetSlices(self.slicename, ['node_ids'])[0]['node_ids']
            new_nodes = list(set(cur_nodes) | self._to_provision)
            self.plapi.UpdateSlice(self.slicename, nodes=new_nodes)
    
        # cleanup
        del self._to_provision
    

    def set(self, time, guid, name, value):
        super(TestbedController, self).set(time, guid, name, value)
        # TODO: take on account schedule time for the task 
        element = self._elements[guid]
        if element:
            setattr(element, name, value)

    def get(self, time, guid, name):
        # TODO: take on account schedule time for the task
        element = self._elements.get(guid)
        if element:
            try:
                if hasattr(element, name):
                    # Runtime attribute
                    return getattr(element, name)
                else:
                    # Try design-time attributes
                    return self.box_get(time, guid, name)
            except KeyError, AttributeError:
                return None

    def get_route(self, guid, index, attribute):
        # TODO: fetch real data from planetlab
        try:
            return self.box_get_route(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None

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
        try:
            return self.box_get_address(guid, index, attribute)
        except KeyError, AttributeError:
            return None


    def action(self, time, guid, action):
        raise NotImplementedError

    def shutdown(self):
        for trace in self._traces.values():
            trace.close()
        for element in self._elements.values():
            pass
            #element.destroy()

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

    def _make_node(self, parameters):
        node = self._node.Node(self.plapi)
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr,val in parameters.iteritems():
            setattr(node, attr, val)
        
        return node
    
    def _make_node_iface(self, parameters):
        iface = self._interfaces.NodeIface(self.plapi)
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr,val in parameters.iteritems():
            setattr(iface, attr, val)
        
        return iface
    
    def _make_tun_iface(self, parameters):
        iface = self._interfaces.TunIface(self.plapi)
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr,val in parameters.iteritems():
            setattr(iface, attr, val)
        
        return iface
    
    def _make_internet(self, parameters):
        return self._interfaces.Internet(self.plapi)
    
    def _make_application(self, parameters):
        app = self._app.Application(self.plapi)
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr,val in parameters.iteritems():
            setattr(app, attr, val)
        
        return app
        

