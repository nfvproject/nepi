#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core import execute
from nepi.core.metadata import Metadata
from nepi.util import validation
from nepi.util.constants import TIME_NOW, \
        ApplicationStatus as AS, \
        TestbedStatus as TS, \
        CONNECTION_DELAY

import collections
import copy

class TestbedController(execute.TestbedController):
    def __init__(self, testbed_id, testbed_version):
        super(TestbedController, self).__init__(testbed_id, testbed_version)
        self._status = TS.STATUS_ZERO
        # testbed attributes for validation
        self._attributes = None
        # element factories for validation
        self._factories = dict()

        # experiment construction instructions
        self._create = dict()
        self._create_set = dict()
        self._factory_set = dict()
        self._connect = dict()
        self._cross_connect = dict()
        self._add_trace = dict()
        self._add_address = dict()
        self._add_route = dict()
        self._configure = dict()

        # log of set operations
        self._setlog = dict()
        # last set operations
        self._set = dict()

        # testbed element instances
        self._elements = dict()

        self._metadata = Metadata(self._testbed_id, self._testbed_version)
        for factory in self._metadata.build_factories():
            self._factories[factory.factory_id] = factory
        self._attributes = self._metadata.testbed_attributes()
        self._root_directory = None
    
    @property
    def root_directory(self):
        return self._root_directory

    @property
    def guids(self):
        return self._create.keys()

    @property
    def elements(self):
        return self._elements
    
    def _get_factory_id(self, guid):
        """ Returns the factory ID of the (perhaps not yet) created object """
        return self._create.get(guid, None)

    def defer_configure(self, name, value):
        if not self._attributes.has_attribute(name):
            raise AttributeError("Invalid attribute %s for testbed" % name)
        # Validation
        self._attributes.set_attribute_value(name, value)
        self._configure[name] = value

    def defer_create(self, guid, factory_id):
        if factory_id not in self._factories:
            raise AttributeError("Invalid element type %s for testbed version %s" %
                    (factory_id, self._testbed_version))
        if guid in self._create:
            raise AttributeError("Cannot add elements with the same guid: %d" %
                    guid)
        self._create[guid] = factory_id

    def defer_create_set(self, guid, name, value):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        if not factory.box_attributes.has_attribute(name):
            raise AttributeError("Invalid attribute %s for element type %s" %
                    (name, factory.factory_id))
        if not factory.box_attributes.is_attribute_value_valid(name, value):
            raise AttributeError("Invalid value %s for attribute %s" % \
                (value, name))
        if guid not in self._create_set:
            self._create_set[guid] = dict()
        self._create_set[guid][name] = value

    def defer_factory_set(self, guid, name, value):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        if not factory.has_attribute(name):
            raise AttributeError("Invalid attribute %s for element type %s" %
                    (name, factory.factory_id))
        if not factory.is_attribute_value_valid(name, value):
            raise AttributeError("Invalid value %s for attribute %s" % \
                (value, name))
        if guid not in self._factory_set:
            self._factory_set[guid] = dict()
        self._factory_set[guid][name] = value

    def defer_connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2):
        factory1 = self._get_factory(guid1)
        factory_id2 = self._create[guid2]
        # TODO VALIDATE!!!
        #if self.box.guid == connector.box.guid:
        #    return False
        #if self.is_full() or connector.is_full():
        #    return False
        #if self.is_connected(connector):
        #    return False
        #count = self._get_connection_count(guid1, connector_type_name1)
        connector_type = factory1.connector_type(connector_type_name1)
        connector_type.can_connect(self._testbed_id, factory_id2, 
                connector_type_name2, False)
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

    def defer_cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_guid, cross_testbed_id, cross_factory_id, 
            cross_connector_type_name):
        factory = self._get_factory(guid)
        # TODO VALIDATE!!!
        #if self.box.guid == connector.box.guid:
        #    return False
        #if self.is_full() or connector.is_full():
        #    return False
        #if self.is_connected(connector):
        #    return False
        #count = self._get_connection_count(guid, connector_type_name)
        connector_type = factory.connector_type(connector_type_name)
        connector_type.can_connect(cross_testbed_id, cross_factory_id, 
                cross_connector_type_name, True)
        if not guid in self._cross_connect:
            self._cross_connect[guid] = dict()
        if not connector_type_name in self._cross_connect[guid]:
             self._cross_connect[guid][connector_type_name] = dict()
        self._cross_connect[guid][connector_type_name] = \
                (cross_guid, cross_testbed_guid, cross_testbed_id, 
                cross_factory_id, cross_connector_type_name)

    def defer_add_trace(self, guid, trace_name):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        if not trace_name in factory.traces_list:
            raise RuntimeError("Element type '%s' has no trace '%s'" %
                    (factory.factory_id, trace_name))
        if not guid in self._add_trace:
            self._add_trace[guid] = list()
        self._add_trace[guid].append(trace_name)

    def defer_add_address(self, guid, address, netprefix, broadcast):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        if not factory.allow_addresses:
            raise RuntimeError("Element type '%s' doesn't support addresses" %
                    factory.factory_id)
            max_addresses = 1 # TODO: MAKE THIS PARAMETRIZABLE
        if guid in self._add_address:
            count_addresses = len(self._add_address[guid])
            if max_addresses == count_addresses:
                raise RuntimeError("Element guid %d of type '%s' can't accept \
                        more addresses" % (guid, factory.factory_id))
        else:
            self._add_address[guid] = list()
        self._add_address[guid].append((address, netprefix, broadcast))

    def defer_add_route(self, guid, destination, netprefix, nexthop, metric = 0):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        if not factory.allow_routes:
            raise RuntimeError("Element type '%s' doesn't support routes" %
                    factory.factory_id)
        if not guid in self._add_route:
            self._add_route[guid] = list()
        self._add_route[guid].append((destination, netprefix, nexthop, metric)) 

    def do_setup(self):
        self._root_directory = self._attributes.\
            get_attribute_value("rootDirectory")
        self._status = TS.STATUS_SETUP

    def do_create(self):
        def set_params(self, guid):
            parameters = self._get_parameters(guid)
            for name, value in parameters.iteritems():
                self.set(guid, name, value)
            
        self._do_in_factory_order(
            'create_function',
            self._metadata.create_order,
            postaction = set_params )
        self._status = TS.STATUS_CREATED

    def _do_connect(self, init = True):
        unconnected = copy.deepcopy(self._connect)
        
        while unconnected:
            for guid1, connections in unconnected.items():
                factory1 = self._get_factory(guid1)
                for connector_type_name1, connections2 in connections.items():
                    connector_type1 = factory1.connector_type(connector_type_name1)
                    for guid2, connector_type_name2 in connections2.items():
                        factory_id2 = self._create[guid2]
                        # Connections are executed in a "From -> To" direction only
                        # This explicitly ignores the "To -> From" (mirror) 
                        # connections of every connection pair.
                        if init:
                            connect_code = connector_type1.connect_to_init_code(
                                    self._testbed_id, factory_id2, 
                                    connector_type_name2,
                                    False)
                        else:
                            connect_code = connector_type1.connect_to_compl_code(
                                    self._testbed_id, factory_id2, 
                                    connector_type_name2,
                                    False)
                        delay = None
                        if connect_code:
                            delay = connect_code(self, guid1, guid2)

                        if delay is not CONNECTION_DELAY:
                            del unconnected[guid1][connector_type_name1][guid2]
                    if not unconnected[guid1][connector_type_name1]:
                        del unconnected[guid1][connector_type_name1]
                if not unconnected[guid1]:
                    del unconnected[guid1]

    def do_connect_init(self):
        self._do_connect()

    def do_connect_compl(self):
        self._do_connect(init = False)
        self._status = TS.STATUS_CONNECTED

    def _do_in_factory_order(self, action, order, postaction = None, poststep = None):
        guids = collections.defaultdict(list)
        # order guids (elements) according to factory_id
        for guid, factory_id in self._create.iteritems():
            guids[factory_id].append(guid)
        # configure elements following the factory_id order
        for factory_id in order:
            # omit the factories that have no element to create
            if factory_id not in guids:
                continue
            factory = self._factories[factory_id]
            if not getattr(factory, action):
                continue
            for guid in guids[factory_id]:
                getattr(factory, action)(self, guid)
                if postaction:
                    postaction(self, guid)
            if poststep:
                for guid in guids[factory_id]:
                    poststep(self, guid)

    @staticmethod
    def do_poststep_preconfigure(self, guid):
        # dummy hook for implementations interested in
        # two-phase configuration
        pass

    def do_preconfigure(self):
        self._do_in_factory_order(
            'preconfigure_function',
            self._metadata.preconfigure_order,
            poststep = self.do_poststep_preconfigure )

    @staticmethod
    def do_poststep_configure(self, guid):
        # dummy hook for implementations interested in
        # two-phase configuration
        pass

    def do_configure(self):
        self._do_in_factory_order(
            'configure_function',
            self._metadata.configure_order,
            poststep = self.do_poststep_configure )
        self._status = TS.STATUS_CONFIGURED

    def do_prestart(self):
        self._do_in_factory_order(
            'prestart_function',
            self._metadata.prestart_order )

    def _do_cross_connect(self, cross_data, init = True):
        for guid, cross_connections in self._cross_connect.iteritems():
            factory = self._get_factory(guid)
            for connector_type_name, cross_connection in \
                    cross_connections.iteritems():
                connector_type = factory.connector_type(connector_type_name)
                (cross_guid, cross_testbed_guid, cross_testbed_id,
                    cross_factory_id, cross_connector_type_name) = cross_connection
                if init:
                    connect_code = connector_type.connect_to_init_code(
                        cross_testbed_id, cross_factory_id, 
                        cross_connector_type_name,
                        True)
                else:
                    connect_code = connector_type.connect_to_compl_code(
                        cross_testbed_id, cross_factory_id, 
                        cross_connector_type_name,
                        True)
                if connect_code:
                    elem_cross_data = cross_data[cross_testbed_guid][cross_guid]
                    connect_code(self, guid, elem_cross_data)       

    def do_cross_connect_init(self, cross_data):
        self._do_cross_connect(cross_data)

    def do_cross_connect_compl(self, cross_data):
        self._do_cross_connect(cross_data, init = False)
        self._status = TS.STATUS_CROSS_CONNECTED

    def set(self, guid, name, value, time = TIME_NOW):
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        if not factory.box_attributes.has_attribute(name):
            raise AttributeError("Invalid attribute %s for element type %s" %
                    (name, factory.factory_id))
        if self._status > TS.STATUS_STARTED and \
                factory.box_attributes.is_attribute_design_only(name):
            raise AttributeError("Attribute %s can only be modified during experiment design" % name)
        if not factory.box_attributes.is_attribute_value_valid(name, value):
            raise AttributeError("Invalid value %s for attribute %s" % \
                    (value, name))
        if guid not in self._set:
            self._set[guid] = dict()
            self._setlog[guid] = dict()
        if time not in self._setlog[guid]:
            self._setlog[guid][time] = dict()
        self._setlog[guid][time][name] = value
        self._set[guid][name] = value

    def get(self, guid, name, time = TIME_NOW):
        """
        gets an attribute from box definitions if available. 
        Throws KeyError if the GUID wasn't created
        through the defer_create interface, and AttributeError if the
        attribute isn't available (doesn't exist or is design-only)
        """
        if not guid in self._create:
            raise KeyError, "Element guid %d doesn't exist" % guid
        factory = self._get_factory(guid)
        if not factory.box_attributes.has_attribute(name):
            raise AttributeError, "Invalid attribute %s for element type %s" % \
            (name, factory.factory_id)
        if guid in self._set and name in self._set[guid]:
            return self._set[guid][name]
        if guid in self._create_set and name in self._create_set[guid]:
            return self._create_set[guid][name]
        return factory.box_attributes.get_attribute_value(name)

    def get_route(self, guid, index, attribute):
        """
        returns information given to defer_add_route.
        
        Raises AttributeError if an invalid attribute is requested
            or if the indexed routing rule does not exist.
        
        Raises KeyError if the GUID has not been seen by
            defer_add_route
        """
        ATTRIBUTES = ['Destination', 'NetPrefix', 'NextHop']
        
        if attribute not in ATTRIBUTES:
            raise AttributeError, "Attribute %r invalid for addresses of %r" % (attribute, guid)
        
        attribute_index = ATTRIBUTES.index(attribute)
        
        routes = self._add_route.get(guid)
        if not routes:
            raise KeyError, "GUID %r not found in %s" % (guid, self._testbed_id)
       
        index = int(index)
        if not (0 <= index < len(addresses)):
            raise AttributeError, "GUID %r at %s does not have a routing entry #%s" % (
                guid, self._testbed_id, index)
        
        return routes[index][attribute_index]

    def get_address(self, guid, index, attribute='Address'):
        """
        returns information given to defer_add_address
        
        Raises AttributeError if an invalid attribute is requested
            or if the indexed routing rule does not exist.
        
        Raises KeyError if the GUID has not been seen by
            defer_add_address
        """
        ATTRIBUTES = ['Address', 'NetPrefix', 'Broadcast']
        
        if attribute not in ATTRIBUTES:
            raise AttributeError, "Attribute %r invalid for addresses of %r" % (attribute, guid)
        
        attribute_index = ATTRIBUTES.index(attribute)
        
        addresses = self._add_address.get(guid)
        if not addresses:
            raise KeyError, "GUID %r not found in %s" % (guid, self._testbed_id)
        
        index = int(index)
        if not (0 <= index < len(addresses)):
            raise AttributeError, "GUID %r at %s does not have an address #%s" % (
                guid, self._testbed_id, index)
        
        return addresses[index][attribute_index]

    def get_attribute_list(self, guid):
        factory = self._get_factory(guid)
        attribute_list = list()
        return factory.box_attributes.attributes_list

    def get_factory_id(self, guid):
        factory = self._get_factory(guid)
        return factory.factory_id

    def start(self, time = TIME_NOW):
        self._do_in_factory_order(
            'start_function',
            self._metadata.start_order )
        self._status = TS.STATUS_STARTED

    #action: NotImplementedError

    def stop(self, time = TIME_NOW):
        self._do_in_factory_order(
            'stop_function',
            reversed(self._metadata.start_order) )
        self._status = TS.STATUS_STOPPED

    def status(self, guid = None):
        if not guid:
            return self._status
        if not guid in self._create:
            raise RuntimeError("Element guid %d doesn't exist" % guid)
        factory = self._get_factory(guid)
        status_function = factory.status_function
        if status_function:
            return status_function(self, guid)
        return AS.STATUS_UNDETERMINED

    def trace(self, guid, trace_id, attribute='value'):
        if attribute == 'value':
            fd = open("%s" % self.trace_filepath(guid, trace_id), "r")
            content = fd.read()
            fd.close()
        elif attribute == 'path':
            content = self.trace_filepath(guid, trace_id)
        else:
            content = None
        return content

    def traces_info(self):
        traces_info = dict()
        host = self._attributes.get_attribute_value("deployment_host")
        user = self._attributes.get_attribute_value("deployment_user")
        for guid, trace_list in self._add_trace.iteritems(): 
            traces_info[guid] = dict()
            for trace_id in trace_list:
                traces_info[guid][trace_id] = dict()
                filepath = self.trace(guid, trace_id, attribute = "path")
                traces_info[guid][trace_id]["host"] = host
                traces_info[guid][trace_id]["user"] = user
                traces_info[guid][trace_id]["filepath"] = filepath
        return traces_info

    def trace_filepath(self, guid, trace_id):
        """
        Return a trace's file path, for TestbedController's default 
        implementation of trace()
        """
        raise NotImplementedError

    #shutdown: NotImplementedError

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

    def _get_traces(self, guid):
        return [] if guid not in self._add_trace else self._add_trace[guid]

    def _get_parameters(self, guid):
        return dict() if guid not in self._create_set else \
                self._create_set[guid]

    def _get_factory(self, guid):
        factory_id = self._create[guid]
        return self._factories[factory_id]

