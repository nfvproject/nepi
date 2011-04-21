#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
import os

class TestbedController(testbed_impl.TestbedController):
    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)
        self._home_directory = None
        self.slicename = None
        self._traces = dict()
        
        import node, interfaces
        self._node = node
        self._interfaces = interfaces

    @property
    def home_directory(self):
        return self._home_directory

    def do_setup(self):
        self._home_directory = self._attributes.\
            get_attribute_value("homeDirectory")
        self.slicename = self._attributes.\
            get_attribute_value("slice")

    def do_create(self):
        # Create node elements per XML data
        super(TestbedController, self).do_create()
        
        # Perform resource discovery if we don't have
        # specific resources assigned yet
        self.do_resource_discovery()
        
        # Create PlanetLab slivers
        self.do_provisioning()
        
        # Wait for all nodes to be ready
        self.wait_nodes()

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
        # TODO: fetch real data from planetlab
        try:
            return self.box_get_address(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None


    def action(self, time, guid, action):
        raise NotImplementedError

    def shutdown(self):
        for trace in self._traces.values():
            trace.close()
        for element in self._elements.values():
            element.destroy()

    def trace_filename(self, guid, trace_id):
        # TODO: Need to be defined inside a home!!!! with and experiment id_code
        return os.path.join(self.home_directory, "%d_%s" % (guid, trace_id))

    def follow_trace(self, trace_id, trace):
        self._traces[trace_id] = trace

    def _make_node(self, parameters):
        node = self._node.Node()
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr in parameters.get_attribute_names():
            setattr(node, attr, parameters.get_attribute_value(attr))
        
        return node
    
    def _make_node_iface(self, parameters):
        iface = self._interfaces.NodeIface()
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr in parameters.get_attribute_names():
            setattr(iface, attr, parameters.get_attribute_value(attr))
        
        return iface
    
    def _make_tun_iface(self, parameters):
        iface = self._interfaces.TunIface()
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr in parameters.get_attribute_names():
            setattr(iface, attr, parameters.get_attribute_value(attr))
        
        return iface
    
    def _make_internet(self, parameters):
        return self._node.Internet()
    
    def _make_application(self, parameters):
        app = self._app.Application()
        
        # Note: there is 1-to-1 correspondence between attribute names
        #   If that changes, this has to change as well
        for attr in parameters.get_attribute_names():
            setattr(app, attr, parameters.get_attribute_value(attr))
        
        return app
        


