#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core import execute
from nepi.core.attributes import Attribute
from nepi.core.metadata import Metadata
from nepi.util import validation
from nepi.util.constants import AF_INET, AF_INET6

TIME_NOW = "0s"

class TestbedInstance(execute.TestbedInstance):
    def __init__(self, testbed_id, testbed_version, configuration):
        super(TestbedInstance, self).__init__(testbed_id, testbed_version,
                configuration)
        self._factories = dict()
        self._elements = dict()
        self._create = dict()
        self._set = dict()
        self._connect = dict()
        self._cross_connect = dict()
        self._add_trace = dict()
        self._add_address = dict()
        self._add_route = dict()        

        self._metadata = Metadata(self._testbed_id, self._testbed_version)
        for factory in self._metadata.build_execute_factories():
            self._factories[factory.factory_id] = factory

    @property
    def elements(self):
        return self._elements

    def create(self, guid, factory_id):
        if factory_id not in self._factories:
            raise RuntimeError("Invalid element type %s for Netns version %s" %
                    (factory_id, self._testbed_version))
        if guid in self._create:
            raise RuntimeError("Cannot add elements with the same guid: %d" %
                    guid)
        self._create[guid] = factory_id

    def create_set(self, guid, name, value):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if not factory.has_attribute(name):
            raise RuntimeError("Invalid attribute %s for element type %s" %
                    (name, factory_id))
        factory.set_attribute_value(name, value)
        if guid not in self._set:
            self._set[guid] = dict()
        self._set[guid][name] = value
       
    def connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2):
        factory_id1 = self._create[guid1]
        factory_id2 = self._create[guid2]
        count = self._get_connection_count(guid1, connector_type_name1)
        factory1 = self._factories[factory_id1]
        connector_type = factory1.connector_type(connector_type_name1)
        connector_type.can_connect(self._testbed_id, factory_id2, 
                connector_type_name2, count)
        if not guid1 in self._connect:
            self._connect[guid1] = dict()
        if not connector_type_name1 in self._connect[guid1]:
             self._connect[guid1][connector_type_name1] = dict()
        self._connect[guid1][connector_type_name1][guid2] = \
               connector_type_name2
        if not guid2 in self._connect:
            self._connect[guid2] = dict()
        if not connector_type_name2 in self._connect[guid2]:
             self._connect[guid2][connector_type_name2] = dict()
        self._connect[guid2][connector_type_name2][guid1] = \
                connector_type_name1

    def cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name):
        factory_id = self._create[guid]
        count = self._get_connection_count(guid, connector_type_name)
        factory = self._factories[factory_id]
        connector_type = factory.connector_type(connector_type_name)
        connector_type.can_connect(cross_testbed_id, cross_factory_id, 
                cross_connector_type_name, count, must_cross = True)
        if not guid in self._connect:
            self._cross_connect[guid] = dict()
        if not connector_type_name in self._cross_connect[guid]:
             self._cross_connect[guid][connector_type_name] = dict()
        self._cross_connect[guid][connector_type_name] = \
                (cross_guid, cross_testbed_id, cross_factory_id, 
                        cross_connector_type_name)

    def add_trace(self, guid, trace_id):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if not trace_id in factory.traces:
            raise RuntimeError("Element type '%s' has no trace '%s'" %
                    (factory_id, trace_id))
        if not guid in self._add_trace:
            self._add_trace[guid] = list()
        self._add_trace[guid].append(trace_id)

    def add_adddress(self, guid, family, address, netprefix, broadcast):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if not factory.allow_addresses:
            raise RuntimeError("Element type '%s' doesn't support addresses" %
                    factory_id)
        max_addresses = factory.get_attribute_value("MaxAddresses")
        if guid in self._add_address:
            count_addresses = len(self._add_address[guid])
            if max_addresses == count_addresses:
                raise RuntimeError("Element guid %d of type '%s' can't accept \
                        more addresses" % (guid, family_id))
        else:
            self._add_address[guid] = list()
        self._add_address[guid].append((family, address, netprefix, broadcast))

    def add_route(self, guid, destination, netprefix, nexthop):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if not factory.allow_routes:
            raise RuntimeError("Element type '%s' doesn't support routes" %
                    factory_id)
        if not guid in self._add_route:
            self._add_route[guid] = list()
        self._add_route[guid].append((destination, netprefix, nexthop)) 

    def do_create(self):
        guids = dict()
        for guid, factory_id in self._create.iteritems():
            if not factory_id in guids:
               guids[factory_id] = list()
            guids[factory_id].append(guid)
        for factory_id in self._metadata.factories_order:
            if factory_id not in guids:
                continue
            factory = self._factories[factory_id]
            for guid in guids[factory_id]:
                parameters = dict() if guid not in self._set else \
                        self._set[guid]
                factory.create_function(self, guid, parameters)
                for name, value in parameters.iteritems():
                    self.set(TIME_NOW, guid, name, value)

    def do_connect(self):
        for guid1, connections in self._connect.iteritems():
            element1 = self._elements[guid1]
            factory_id1 = self._create[guid1]
            factory1 = self._factories[factory_id1]
            for connector_type_name1, connections2 in connections.iteritems():
                connector_type1 = factory1.connector_type(connector_type_name1)
                for guid2, connector_type_name2 in connections2.iteritems():
                    element2 = self._elements[guid2]
                    factory_id2 = self._create[guid2]
                    # Connections are executed in a "From -> To" direction only
                    # This explicitly ignores the "To -> From" (mirror) 
                    # connections of every connection pair. 
                    code_to_connect = connector_type1.code_to_connect(
                            self._testbed_id, factory_id2, 
                            connector_type_name2)
                    if code_to_connect:
                        code_to_connect(element1, element2)

    def do_configure(self):
        raise NotImplementedError

    def do_cross_connect(self):
        for guid, cross_connections in self._cross_connect.iteritems():
            element = self._elements[guid]
            factory_id = self._create[guid]
            factory = self._factories[factory_id]
            for connector_type_name, cross_connection in \
                    cross_connections.iteritems():
                connector_type = factory.connector_type(connector_type_name)
                (cross_testbed_id, cross_factory_id, 
                        cross_connector_type_name) = cross_connection
                code_to_connect = connector_type.code_to_connect(
                    cross_guid, cross_testbed_id, cross_factory_id, 
                    cross_conector_type_name)
                if code_to_connect:
                    code_to_connect(element, cross_guid)       

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError

    def start(self, time = TIME_NOW):
        for guid, factory_id in self._create.iteritems():
            factory = self._factories[factory_id]
            start_function = factory.start_function
            if start_function:
                traces = [] if guid not in self._add_trace else \
                        self._add_trace[guid]
                parameters = dict() if guid not in self._set else \
                        self._set[guid]
                start_function(self, guid, parameters, traces)

    def action(self, time, guid, action):
        raise NotImplementedError

    def stop(self, time = TIME_NOW):
        for guid, factory_id in self._create.iteritems():
            factory = self._factories[factory_id]
            stop_function = factory.stop_function
            if stop_function:
                traces = [] if guid not in self._add_trace else \
                        self._add_trace[guid]
                stop_function(self, guid, traces)

    def status(self, guid):
          for guid, factory_id in self._create.iteritems():
            factory = self._factories[factory_id]
            status_function = factory.status_function
            if status_function:
                result = status_function(self, guid)

    def trace(self, guid, trace_id):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def get_connected(self, guid, connector_type_name, 
            other_connector_type_name):
        """searchs the connected elements for the specific connector_type_name 
        pair"""
        if guid not in self._connect:
            return []
        # all connections for all connectors for guid
        all_connections = self._connect[guid]
        if connector_type_name not in all_connections:
            return []
        # all connections for the specific connector
        connections = all_connections[connector_type_name]
        specific_connections = [otr_guid for otr_guid, otr_connector_type_name \
                in connections.iteritems() if \
                otr_connector_type_name == other_connector_type_name]
        return specific_connections

    def _get_connection_count(self, guid, connection_type_name):
        count = 0
        cross_count = 0
        if guid in self._connect and connection_type_name in \
                self._connect[guid]:
            count = len(self._connect[guid][connection_type_name])
        if guid in self._cross_connect and connection_type_name in \
                self._cross_connect[guid]:
            cross_count = len(self._cross_connect[guid][connection_type_name])
        return count + cross_count


