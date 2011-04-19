#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute, AttributesMap
from nepi.util import proxy, validation
from nepi.util.constants import STATUS_FINISHED, TIME_NOW
from nepi.util.parser._xml import XmlExperimentParser
import sys
import re
import threading
import ConfigParser
import os

ATTRIBUTE_PATTERN_BASE = re.compile(r"\{#\[(?P<label>[-a-zA-Z0-9._]*)\](?P<expr>(?P<component>\.addr\[[0-9]+\]|\.route\[[0-9]+\]|\.trace\[[0-9]+\]|).\[(?P<attribute>[-a-zA-Z0-9._]*)\])#}")
ATTRIBUTE_PATTERN_GUID_SUB = r"{#[%(guid)s]%(expr)s#}"
COMPONENT_PATTERN = re.compile(r"(?P<kind>[a-z]*)\[(?P<index>.*)\]")

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
            stop_function, status_function, configure_function,
            allow_addresses = False, allow_routes = False):
        super(Factory, self).__init__()
        self._factory_id = factory_id
        self._allow_addresses = (allow_addresses == True)
        self._allow_routes = (allow_routes == True)
        self._create_function = create_function
        self._start_function = start_function
        self._stop_function = stop_function
        self._status_function = status_function
        self._configure_function = configure_function
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
    def configure_function(self):
        return self._configure_function

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

class TestbedController(object):
    def __init__(self, testbed_id, testbed_version):
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version

    @property
    def guids(self):
        raise NotImplementedError

    def defer_configure(self, name, value):
        """Instructs setting a configuartion attribute for the testbed instance"""
        raise NotImplementedError

    def defer_create(self, guid, factory_id):
        """Instructs creation of element """
        raise NotImplementedError

    def defer_create_set(self, guid, name, value):
        """Instructs setting an initial attribute on an element"""
        raise NotImplementedError

    def defer_factory_set(self, guid, name, value):
        """Instructs setting an attribute on a factory"""
        raise NotImplementedError

    def defer_connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2): 
        """Instructs creation of a connection between the given connectors"""
        raise NotImplementedError

    def defer_cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name):
        """
        Instructs creation of a connection between the given connectors 
        of different testbed instances
        """
        raise NotImplementedError

    def defer_add_trace(self, guid, trace_id):
        """Instructs the addition of a trace"""
        raise NotImplementedError

    def defer_add_address(self, guid, address, netprefix, broadcast): 
        """Instructs the addition of an address"""
        raise NotImplementedError

    def defer_add_route(self, guid, destination, netprefix, nexthop):
        """Instructs the addition of a route"""
        raise NotImplementedError

    def do_setup(self):
        """After do_setup the testbed initial configuration is done"""
        raise NotImplementedError

    def do_create(self):
        """
        After do_create all instructed elements are created and 
        attributes setted
        """
        raise NotImplementedError

    def do_connect(self):
        """
        After do_connect all internal connections between testbed elements
        are done
        """
        raise NotImplementedError

    def do_configure(self):
        """After do_configure elements are configured"""
        raise NotImplementedError

    def do_cross_connect(self):
        """
        After do_cross_connect all external connections between different testbed 
        elements are done
        """
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError
    
    def get_route(self, guid, index, attribute):
        """
        Params:
            
            guid: guid of box to query
            index: number of routing entry to fetch
            attribute: one of Destination, NextHop, NetPrefix
        """
        raise NotImplementedError

    def get_address(self, guid, index, attribute='Address'):
        """
        Params:
            
            guid: guid of box to query
            index: number of inteface to select
            attribute: one of Address, NetPrefix, Broadcast
        """
        raise NotImplementedError

    def action(self, time, guid, action):
        raise NotImplementedError

    def status(self, guid):
        raise NotImplementedError

    def trace(self, guid, trace_id, attribute='value'):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

class ExperimentController(object):
    def __init__(self, experiment_xml, root_dir):
        self._experiment_xml = experiment_xml
        self._testbeds = dict()
        self._access_config = dict()
        self._netrefs = dict()
        self._root_dir = root_dir

        self.persist_experiment_xml()

    @property
    def experiment_xml(self):
        return self._experiment_xml

    def persist_experiment_xml(self):
        xml_path = os.path.join(self._root_dir, "experiment.xml")
        f = open(xml_path, "w")
        f.write(self._experiment_xml)
        f.close()

    def set_access_configuration(self, testbed_guid, access_config):
        self._access_config[testbed_guid] = access_config

    def trace(self, testbed_guid, guid, trace_id, attribute='value'):
        return self._testbeds[testbed_guid].trace(guid, trace_id, attribute)

    @staticmethod
    def _parallel(callables):
        threads = [ threading.Thread(target=callable) for callable in callables ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def start(self):
        self._create_testbed_instances()
        
        # persist testbed connection data, for potential recovery
        self._persist_testbed_proxies()
        
        # perform setup in parallel for all test beds,
        # wait for all threads to finish
        self._parallel([testbed.do_setup 
                        for testbed in self._testbeds.itervalues()])
        
        # perform create-connect in parallel, wait
        # (internal connections only)
        self._parallel([lambda : (testbed.do_create(), 
                                  testbed.do_connect())
                        for testbed in self._testbeds.itervalues()])
        
        # resolve netrefs
        self.do_netrefs(fail_if_undefined=True)
        
        # perform do_configure in parallel for al testbeds
        # (it's internal configuration for each)
        self._parallel([testbed.do_configure
                        for testbed in self._testbeds.itervalues()])

        # cross-connect (cannot be done in parallel)
        for testbed in self._testbeds.values():
            testbed.do_cross_connect()
        
        # start experiment (parallel start on all testbeds)
        self._parallel([testbed.start
                        for testbed in self._testbeds.itervalues()])

    def _persist_testbed_proxies(self):
        TRANSIENT = ('Recover',)
        
        # persist access configuration for all testbeds, so that
        # recovery mode can reconnect to them if it becomes necessary
        conf = ConfigParser.RawConfigParser()
        for testbed_guid, testbed_config in self._access_config.iteritems():
            testbed_guid = str(testbed_guid)
            conf.add_section(testbed_guid)
            for attr in testbed_config.attributes_name:
                if attr not in TRANSIENT:
                    conf.set(testbed_guid, attr, 
                        testbed_config.get_attribute_value(attr))
        
        f = open(os.path.join(self._root_dir, 'access_config.ini'), 'w')
        conf.write(f)
        f.close()
    
    def _load_testbed_proxies(self):
        TYPEMAP = {
            STRING : 'get',
            INTEGER : 'getint',
            FLOAT : 'getfloat',
            BOOLEAN : 'getboolean',
        }
        
        conf = ConfigParser.RawConfigParser()
        conf.read(os.path.join(self._root_dir, 'access_config.ini'))
        for testbed_guid in conf.sections():
            testbed_config = proxy.AccessConfiguration()
            for attr in conf.options(testbed_guid):
                testbed_config.set_attribute_value(attr, 
                    conf.get(testbed_guid, attr) )
                
            testbed_guid = str(testbed_guid)
            conf.add_section(testbed_guid)
            for attr in testbed_config.attributes_name:
                if attr not in TRANSIENT:
                    getter = getattr(conf, TYPEMAP.get(
                        testbed_config.get_attribute_type(attr),
                        'get') )
                    testbed_config.set_attribute_value(
                        testbed_guid, attr, getter(attr))
    
    def _unpersist_testbed_proxies(self):
        try:
            os.remove(os.path.join(self._root_dir, 'access_config.ini'))
        except:
            # Just print exceptions, this is just cleanup
            import traceback
            traceback.print_exc(file=sys.stderr)

    def stop(self):
       for testbed in self._testbeds.values():
           testbed.stop()
       self._unpersist_testbed_proxies()
   
    def recover(self):
        # reload perviously persisted testbed access configurations
        self._load_testbed_proxies()
        
        # recreate testbed proxies by reconnecting only
        self._create_testbed_instances(recover=True)

    def is_finished(self, guid):
        for testbed in self._testbeds.values():
            for guid_ in testbed.guids:
                if guid_ == guid:
                    return testbed.status(guid) == STATUS_FINISHED
        raise RuntimeError("No element exists with guid %d" % guid)    

    def shutdown(self):
       for testbed in self._testbeds.values():
           testbed.shutdown()

    @staticmethod
    def _netref_component_split(component):
        match = COMPONENT_PATTERN.match(component)
        if match:
            return match.group("kind"), match.group("index")
        else:
            return component, None

    def do_netrefs(self, fail_if_undefined = False):
        COMPONENT_GETTERS = {
            'addr' :
                lambda testbed, guid, index, name : 
                    testbed.get_address(guid, index, name),
            'route' :
                lambda testbed, guid, index, name : 
                    testbed.get_route(guid, index, name),
            'trace' :
                lambda testbed, guid, index, name : 
                    testbed.trace(guid, index, name),
            '' : 
                lambda testbed, guid, index, name : 
                    testbed.get(TIME_NOW, guid, name),
        }
        
        for (testbed_guid, guid), attrs in self._netrefs.iteritems():
            testbed = self._testbeds[testbed_guid]
            for name in attrs:
                value = testbed.get(TIME_NOW, guid, name)
                if isinstance(value, basestring):
                    match = ATTRIBUTE_PATTERN_BASE.search(value)
                    if match:
                        label = match.group("label")
                        if label.startswith('GUID-'):
                            ref_guid = int(label[5:])
                            if ref_guid:
                                expr = match.group("expr")
                                component = match.group("component")[1:] # skip the dot
                                attribute = match.group("attribute")
                                
                                # split compound components into component kind and index
                                # eg: 'addr[0]' -> ('addr', '0')
                                component, component_index = self._netref_component_split(component)
                                
                                # find object and resolve expression
                                for ref_testbed in self._testbeds.itervalues():
                                    if component not in COMPONENT_GETTERS:
                                        raise ValueError, "Malformed netref: %r - unknown component" % (expr,)
                                    else:
                                        value = COMPONENT_GETTERS[component](
                                            ref_testbed, ref_guid, component_index, attribute)
                                        if value: 
                                            break
                                else:
                                    # couldn't find value
                                    if fail_if_undefined:
                                        raise ValueError, "Unresolvable GUID: %r, in netref: %r" % (ref_guid, expr)

    def _create_testbed_instances(self, recover = False):
        parser = XmlExperimentParser()
        data = parser.from_xml_to_data(self._experiment_xml)
        element_guids = list()
        label_guids = dict()
        data_guids = data.guids
        netrefs = self._netrefs
        for guid in data_guids:
            if data.is_testbed_data(guid):
                (testbed_id, testbed_version) = data.get_testbed_data(guid)
                access_config = None if guid not in self._access_config else\
                        self._access_config[guid]
                
                if recover and access_config is None:
                    # need to create one
                    access_config = self._access_config[guid] = proxy.AccessConfiguration()
                if access_config is not None:
                    # force recovery mode 
                    access_config.set_attribute_value("recover",recover)
                
                testbed = proxy.create_testbed_instance(testbed_id, 
                        testbed_version, access_config)
                for (name, value) in data.get_attribute_data(guid):
                    testbed.defer_configure(name, value)
                self._testbeds[guid] = testbed
            else:
                element_guids.append(guid)
                label = data.get_attribute_data(guid, "label")
                if label is not None:
                    if label in label_guids:
                        raise RuntimeError, "Label %r is not unique" % (label,)
                    label_guids[label] = guid
        for guid in data_guids:
            if not data.is_testbed_data(guid):
                for name, value in data.get_attribute_data(guid):
                    if isinstance(value, basestring):
                        match = ATTRIBUTE_PATTERN_BASE.search(value)
                        if match:
                            label = match.group("label")
                            if not label.startswith('GUID-'):
                                ref_guid = label_guids.get(label)
                                if ref_guid is not None:
                                    value = ATTRIBUTE_PATTERN_BASE.sub(
                                        ATTRIBUTE_PATTERN_GUID_SUB % dict(
                                            guid='GUID-%d' % (ref_guid,),
                                            expr=match.group("expr"),
                                            label=label), 
                                        value)
                                    data.set_attribute_data(guid, name, value)
                                    
                                    # memorize which guid-attribute pairs require
                                    # postprocessing, to avoid excessive controller-testbed
                                    # communication at configuration time
                                    # (which could require high-latency network I/O)
                                    (testbed_guid, factory_id) = data.get_box_data(guid)
                                    netrefs.setdefault((testbed_guid,guid),set()).add(name)
        if not recover:
            self._program_testbed_instances(element_guids, data)

    def _program_testbed_instances(self, element_guids, data):
        for guid in element_guids:
            (testbed_guid, factory_id) = data.get_box_data(guid)
            testbed = self._testbeds[testbed_guid]
            testbed.defer_create(guid, factory_id)
            for (name, value) in data.get_attribute_data(guid):
                testbed.defer_create_set(guid, name, value)

        for guid in element_guids: 
            (testbed_guid, factory_id) = data.get_box_data(guid)
            testbed = self._testbeds[testbed_guid]
            for (connector_type_name, other_guid, other_connector_type_name) \
                    in data.get_connection_data(guid):
                (testbed_guid, factory_id) = data.get_box_data(guid)
                (other_testbed_guid, other_factory_id) = data.get_box_data(
                        other_guid)
                if testbed_guid == other_testbed_guid:
                    testbed.defer_connect(guid, connector_type_name, other_guid, 
                        other_connector_type_name)
                else:
                    testbed.defer_cross_connect(guid, connector_type_name, other_guid, 
                        other_testbed_id, other_factory_id, other_connector_type_name)
            for trace_id in data.get_trace_data(guid):
                testbed.defer_add_trace(guid, trace_id)
            for (autoconf, address, netprefix, broadcast) in \
                    data.get_address_data(guid):
                if address != None:
                    testbed.defer_add_address(guid, address, netprefix, broadcast)
            for (destination, netprefix, nexthop) in data.get_route_data(guid):
                testbed.defer_add_route(guid, destination, netprefix, nexthop)

