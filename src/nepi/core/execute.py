#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute, AttributesMap
from nepi.util import proxy, validation
from nepi.util.constants import STATUS_FINISHED
from nepi.util.parser._xml import XmlExperimentParser
import sys

class ConnectorType(object):
    def __init__(self, testbed_id, factory_id, name, max = -1, min = 0):
        super(ConnectorType, self).__init__()
        if max == -1:
            max = sys.maxint
        elif max <= 0:
                raise RuntimeError(
             "The maximum number of connections allowed need to be more than 0")
        if min < 0:
            raise RuntimeError(
             "The minimum number of connections allowed needs to be at least 0")
        # connector_type_id -- univoquely identifies a connector type 
        # across testbeds
        self._connector_type_id = (testbed_id.lower(), factory_id.lower(), 
                name.lower())
        # name -- display name for the connector type
        self._name = name
        # max -- maximum amount of connections that this type support, 
        # -1 for no limit
        self._max = max
        # min -- minimum amount of connections required by this type of connector
        self._min = min
        # from_connections -- connections where the other connector is the "From"
        # to_connections -- connections where the other connector is the "To"
        # keys in the dictionary correspond to the 
        # connector_type_id for possible connections. The value is a tuple:
        # (can_cross, connect)
        # can_cross: indicates if the connection is allowed accros different
        #    testbed instances
        # code: is the connection function to be invoked when the elements
        #    are connected
        self._from_connections = dict()
        self._to_connections = dict()

    @property
    def connector_type_id(self):
        return self._connector_type_id

    @property
    def name(self):
        return self._name

    @property
    def max(self):
        return self._max

    @property
    def min(self):
        return self._min

    def add_from_connection(self, testbed_id, factory_id, name, can_cross, code):
        self._from_connections[(testbed_id.lower(), factory_id.lower(),
            name.lower())] = (can_cross, code)

    def add_to_connection(self, testbed_id, factory_id, name, can_cross, code):
        self._to_connections[(testbed_id.lower(), factory_id.lower(), 
            name.lower())] = (can_cross, code)

    def can_connect(self, testbed_id, factory_id, name, count, 
            must_cross = False):
        connector_type_id = (testbed_id.lower(), factory_id.lower(),
            name.lower())
        if connector_type_id in self._from_connections:
            (can_cross, code) = self._from_connections[connector_type_id]
        elif connector_type_id in self._to_connections:
            (can_cross, code) = self._to_connections[connector_type_id]
        else:
            return False
        return not must_cross or can_cross

    def code_to_connect(self, testbed_id, factory_id, name):
        connector_type_id = (testbed_id.lower(), factory_id.lower(), 
            name.lower())        
        if not connector_type_id in self._to_connections.keys():
            return False
        (can_cross, code) = self._to_connections[connector_type_id]
        return code

# TODO: create_function, start_function, stop_function, status_function 
# need a definition!
class Factory(AttributesMap):
    def __init__(self, factory_id, create_function, start_function, 
            stop_function, status_function, allow_addresses = False, 
            allow_routes = False):
        super(Factory, self).__init__()
        self._factory_id = factory_id
        self._allow_addresses = (allow_addresses == True)
        self._allow_routes = (allow_routes == True)
        self._create_function = create_function
        self._start_function = start_function
        self._stop_function = stop_function
        self._status_function = status_function
        self._connector_types = dict()
        self._traces = list()
        self._box_attributes = AttributesMap()

    @property
    def factory_id(self):
        return self._factory_id

    @property
    def allow_addresses(self):
        return self._allow_addresses

    @property
    def allow_routes(self):
        return self._allow_routes

    @property
    def box_attributes(self):
        return self._box_attributes

    @property
    def create_function(self):
        return self._create_function

    @property
    def start_function(self):
        return self._start_function

    @property
    def stop_function(self):
        return self._stop_function

    @property
    def status_function(self):
        return self._status_function

    @property
    def traces(self):
        return self._traces

    def connector_type(self, name):
        return self._connector_types[name]

    def add_connector_type(self, connector_type):
        self._connector_types[connector_type.name] = connector_type

    def add_trace(self, trace_id):
        self._traces.append(trace_id)

    def add_box_attribute(self, name, help, type, value = None, range = None,
        allowed = None, flags = Attribute.NoFlags, validation_function = None):
        self._box_attributes.add_attribute(name, help, type, value, range, 
                allowed, flags, validation_function)

class TestbedInstance(object):
    def __init__(self, testbed_id, testbed_version):
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version

    @property
    def guids(self):
        raise NotImplementedError

    def configure(self, name, value):
        """Set a configuartion attribute for the testbed instance"""
        raise NotImplementedError

    def create(self, guid, factory_id):
        """Instructs creation of element """
        raise NotImplementedError

    def create_set(self, guid, name, value):
        """Instructs setting an initial attribute on an element"""
        raise NotImplementedError

    def factory_set(self, guid, name, value):
        """Instructs setting an attribute on a factory"""
        raise NotImplementedError

    def connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2): 
        raise NotImplementedError

    def cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name):
        raise NotImplementedError

    def add_trace(self, guid, trace_id):
        raise NotImplementedError

    def add_address(self, guid, address, netprefix, broadcast): 
        raise NotImplementedError

    def add_route(self, guid, destination, netprefix, nexthop):
        raise NotImplementedError

    def do_setup(self):
        """After do_setup the testbed initial configuration is done"""
        raise NotImplementedError

    def do_create(self):
        """After do_create all instructed elements are created and 
        attributes setted"""
        raise NotImplementedError

    def do_connect(self):
        """After do_connect all internal connections between testbed elements
        are done"""
        raise NotImplementedError

    def do_configure(self):
        """After do_configure elements are configured"""
        raise NotImplementedError

    def do_cross_connect(self):
        """After do_cross_connect all external connections between different testbed 
        elements are done"""
        raise NotImplementedError

    def start(self, time):
        raise NotImplementedError

    def stop(self, time):
        raise NotImplementedError

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError

    def action(self, time, guid, action):
        raise NotImplementedError

    def status(self, guid):
        raise NotImplementedError

    def trace(self, guid, trace_id):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

class ExperimentController(object):
    def __init__(self, experiment_xml):
        self._experiment_xml = experiment_xml
        self._testbeds = dict()
        self._access_config = dict()

    @property
    def experiment_xml(self):
        return self._experiment_xml

    def set_access_configuration(self, testbed_guid, access_config):
        self._access_config[testbed_guid] = access_config

    def trace(self, testbed_guid, guid, trace_id):
        return self._testbeds[testbed_guid].trace(guid, trace_id)

    def start(self):
        self._create_testbed_instances()
        for testbed in self._testbeds.values():
            testbed.do_setup()
        for testbed in self._testbeds.values():
            testbed.do_create()
            testbed.do_connect()
            testbed.do_configure()
        for testbed in self._testbeds.values():
            testbed.do_cross_connect()
        for testbed in self._testbeds.values():
            testbed.start()

    def stop(self):
       for testbed in self._testbeds.values():
           testbed.stop()

    def is_finished(self, guid):
        for testbed in self._testbeds.values():
            for guid_ in testbed.guids:
                if guid_ == guid:
                    return testbed.status(guid) == STATUS_FINISHED
        raise RuntimeError("No element exists with guid %d" % guid)    

    def shutdown(self):
       for testbed in self._testbeds.values():
           testbed.shutdown()

    def _create_testbed_instances(self):
        parser = XmlExperimentParser()
        data = parser.from_xml_to_data(self._experiment_xml)
        element_guids = list()
        for guid in data.guids:
            if data.is_testbed_data(guid):
                (testbed_id, testbed_version) = data.get_testbed_data(guid)
                access_config = None if guid not in self._access_config else\
                        self._access_config[guid]
                testbed = proxy.create_testbed_instance(testbed_id, 
                        testbed_version, access_config)
                for (name, value) in data.get_attribute_data(guid):
                    testbed.configure(name, value)
                self._testbeds[guid] = testbed
            else:
                element_guids.append(guid)
        self._program_testbed_instances(element_guids, data)

    def _program_testbed_instances(self, element_guids, data):
        for guid in element_guids:
            (testbed_guid, factory_id) = data.get_box_data(guid)
            testbed = self._testbeds[testbed_guid]
            testbed.create(guid, factory_id)
            for (name, value) in data.get_attribute_data(guid):
                testbed.create_set(guid, name, value)

        for guid in element_guids: 
            (testbed_guid, factory_id) = data.get_box_data(guid)
            testbed = self._testbeds[testbed_guid]
            for (connector_type_name, other_guid, other_connector_type_name) \
                    in data.get_connection_data(guid):
                (testbed_guid, factory_id) = data.get_box_data(guid)
                (other_testbed_guid, other_factory_id) = data.get_box_data(
                        other_guid)
                if testbed_guid == other_testbed_guid:
                    testbed.connect(guid, connector_type_name, other_guid, 
                        other_connector_type_name)
                else:
                    testbed.cross_connect(guid, connector_type_name, other_guid, 
                        other_testbed_id, other_factory_id, other_connector_type_name)
            for trace_id in data.get_trace_data(guid):
                testbed.add_trace(guid, trace_id)
            for (autoconf, address, netprefix, broadcast) in \
                    data.get_address_data(guid):
                if address != None:
                    testbed.add_address(guid, address, netprefix, broadcast)
            for (destination, netprefix, nexthop) in data.get_route_data(guid):
                testbed.add_route(guid, destination, netprefix, nexthop)

