#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Experiment design API
"""

from nepi.core.attributes import AttributesMap, Attribute
from nepi.core.connector import ConnectorTypeBase
from nepi.core.metadata import Metadata
from nepi.util import validation
from nepi.util.guid import GuidGenerator
from nepi.util.graphical_info import GraphicalInfo
from nepi.util.parser._xml import XmlExperimentParser
import sys
    


class ConnectorType(ConnectorTypeBase):
    def __init__(self, testbed_id, factory_id, name, help, max = -1, min = 0):
        super(ConnectorType, self).__init__(testbed_id, factory_id, name, max, min)
        
        # help -- help text
        self._help = help
        
        # allowed_connections -- keys in the dictionary correspond to the 
        # connector_type_id for possible connections. The value indicates if
        # the connection is allowed accros different testbed instances
        self._allowed_connections = dict()

    @property
    def help(self):
        return self._help

    def add_allowed_connection(self, testbed_id, factory_id, name, can_cross):
        type_id = self.make_connector_type_id(testbed_id, factory_id, name)
        self._allowed_connections[type_id] = can_cross

    def can_connect(self, connector_type_id, testbed_guid1, testbed_guid2):
        for lookup_type_id in self._type_resolution_order(connector_type_id):
            if lookup_type_id in self._allowed_connections:
                can_cross = self._allowed_connections[lookup_type_id]
                return can_cross or (testbed_guid1 == testbed_guid2)
        else:
            return False

class Connector(object):
    """A Connector sepcifies the connection points in an Object"""
    def __init__(self, box, connector_type):
        super(Connector, self).__init__()
        self._box = box
        self._connector_type = connector_type
        self._connections = list()

    @property
    def box(self):
        return self._box

    @property
    def connector_type(self):
        return self._connector_type

    @property
    def connections(self):
        return self._connections

    def is_full(self):
        """Return True if the connector has the maximum number of connections
        """
        return len(self.connections) == self.connector_type.max

    def is_complete(self):
        """Return True if the connector has the minimum number of connections
        """
        return len(self.connections) >= self.connector_type.min

    def is_connected(self, connector):
        return connector in self._connections

    def connect(self, connector):
        if not self.can_connect(connector) or not connector.can_connect(self):
            raise RuntimeError("Could not connect.")
        self._connections.append(connector)
        connector._connections.append(self)

    def disconnect(self, connector):
        if connector not in self._connections or\
                self not in connector._connections:
                raise RuntimeError("Could not disconnect.")
        self._connections.remove(connector)
        connector._connections.remove(self)

    def can_connect(self, connector):
        if self.is_full() or connector.is_full():
            return False
        if self.is_connected(connector):
            return False
        connector_type_id = connector.connector_type.connector_type_id
        testbed_guid1 = self.box.testbed_guid
        testbed_guid2 = connector.box.testbed_guid
        return self.connector_type.can_connect(connector_type_id, 
                testbed_guid1, testbed_guid2)

    def destroy(self):
        for connector in self.connections:
            self.disconnect(connector)
        self._box = self._connectors = None

class Trace(AttributesMap):
    def __init__(self, trace_id, help, enabled = False):
        super(Trace, self).__init__()
        self._trace_id = trace_id
        self._help = help       
        self.enabled = enabled
    
    @property
    def trace_id(self):
        return self._trace_id

    @property
    def help(self):
        return self._help

class Address(AttributesMap):
    def __init__(self):
        super(Address, self).__init__()
        self.add_attribute(name = "AutoConfigure", 
                help = "If set, this address will automatically be assigned", 
                type = Attribute.BOOL,
                value = False,
                flags = Attribute.DesignOnly,
                validation_function = validation.is_bool)
        self.add_attribute(name = "Address",
                help = "Address number", 
                type = Attribute.STRING,
                flags = Attribute.HasNoDefaultValue,
                validation_function = validation.is_ip_address)
        self.add_attribute(name = "NetPrefix",
                help = "Network prefix for the address", 
                type = Attribute.INTEGER, 
                range = (0, 128),
                value = 24,
                flags = Attribute.HasNoDefaultValue,
                validation_function = validation.is_integer)
        self.add_attribute(name = "Broadcast",
                help = "Broadcast address", 
                type = Attribute.STRING,
                validation_function = validation.is_ip4_address)
                
class Route(AttributesMap):
    def __init__(self):
        super(Route, self).__init__()
        self.add_attribute(name = "Destination", 
                help = "Network destintation",
                type = Attribute.STRING, 
                validation_function = validation.is_ip_address)
        self.add_attribute(name = "NetPrefix",
                help = "Network destination prefix", 
                type = Attribute.INTEGER, 
                range = (0, 128),
                value = 24,
                flags = Attribute.HasNoDefaultValue,
                validation_function = validation.is_integer)
        self.add_attribute(name = "NextHop",
                help = "Address for the next hop", 
                type = Attribute.STRING,
                flags = Attribute.HasNoDefaultValue,
                validation_function = validation.is_ip_address)

class Box(AttributesMap):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(Box, self).__init__()
        # guid -- global unique identifier
        self._guid = guid
        # factory_id -- factory identifier or name
        self._factory_id = factory.factory_id
        # testbed_guid -- parent testbed guid
        self._testbed_guid = testbed_guid
        # container -- boxes can be nested inside other 'container' boxes
        self._container = container
        # traces -- list of available traces for the box
        self._traces = dict()
        # connectors -- list of available connectors for the box
        self._connectors = dict()
        # factory_attributes -- factory attributes for box construction
        self._factory_attributes = dict()
        # graphical_info -- GUI position information
        self.graphical_info = GraphicalInfo(str(self._guid))

        for connector_type in factory.connector_types:
            connector = Connector(self, connector_type)
            self._connectors[connector_type.name] = connector
        for trace in factory.traces:
            tr = Trace(trace.trace_id, trace.help, trace.enabled)
            self._traces[trace.trace_id] = tr
        for attr in factory.box_attributes.attributes:
            self.add_attribute(attr.name, attr.help, attr.type, attr.value, 
                    attr.range, attr.allowed, attr.flags, 
                    attr.validation_function)
        for attr in factory.attributes:
            if attr.modified:
                self._factory_attributes[attr.name] = attr.value

    @property
    def guid(self):
        return self._guid

    @property
    def factory_id(self):
        return self._factory_id

    @property
    def testbed_guid(self):
        return self._testbed_guid

    @property
    def container(self):
        return self._container

    @property
    def connectors(self):
        return self._connectors.values()

    @property
    def traces(self):
        return self._traces.values()

    @property
    def traces_name(self):
        return self._traces.keys()

    @property
    def factory_attributes(self):
        return self._factory_attributes

    @property
    def addresses(self):
        return []

    @property
    def routes(self):
        return []

    def trace_help(self, trace_id):
        return self._traces[trace_id].help

    def enable_trace(self, trace_id):
        self._traces[trace_id].enabled = True

    def disable_trace(self, trace_id):
        self._traces[trace_id].enabled = False

    def connector(self, name):
        return self._connectors[name]

    def destroy(self):
        super(Box, self).destroy()
        for c in self.connectors:
            c.destroy()         
        for t in self.traces:
            t.destroy()
        self._connectors = self._traces = self._factory_attributes = None

class AddressableMixin(object):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(AddressableMixin, self).__init__(guid, factory, testbed_guid, 
                container)
        self._max_addresses = 1 # TODO: How to make this configurable!
        self._addresses = list()

    @property
    def addresses(self):
        return self._addresses

    @property
    def max_addresses(self):
        return self._max_addresses

class UserAddressableMixin(AddressableMixin):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(UserAddressableMixin, self).__init__(guid, factory, testbed_guid, 
                container)

    def add_address(self):
        if len(self._addresses) == self.max_addresses:
            raise RuntimeError("Maximun number of addresses for this box reached.")
        address = Address()
        self._addresses.append(address)
        return address

    def delete_address(self, address):
        self._addresses.remove(address)
        del address

    def destroy(self):
        super(UserAddressableMixin, self).destroy()
        for address in list(self.addresses):
            self.delete_address(address)
        self._addresses = None

class RoutableMixin(object):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(RoutableMixin, self).__init__(guid, factory, testbed_guid, 
            container)
        self._routes = list()

    @property
    def routes(self):
        return self._routes

class UserRoutableMixin(RoutableMixin):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(UserRoutableMixin, self).__init__(guid, factory, testbed_guid, 
            container)

    def add_route(self):
        route = Route()
        self._routes.append(route)
        return route

    def delete_route(self, route):
        self._route.remove(route)
        del route

    def destroy(self):
        super(UserRoutableMixin, self).destroy()
        for route in list(self.routes):
            self.delete_route(route)
        self._route = None

def MixIn(MyClass, MixIn):
    # Mixins are installed BEFORE "Box" because
    # Box inherits from non-cooperative classes,
    # so the MRO chain gets broken when it gets
    # to Box.

    # Install mixin
    MyClass.__bases__ = (MixIn,) + MyClass.__bases__
    
    # Add properties
    # Somehow it doesn't work automatically
    for name in dir(MixIn):
        prop = getattr(MixIn,name,None)
        if isinstance(prop, property):
            setattr(MyClass, name, prop)
    
    # Update name
    MyClass.__name__ = MyClass.__name__.replace(
        'Box',
        MixIn.__name__.replace('MixIn','')+'Box',
        1)

class Factory(AttributesMap):
    _box_class_cache = {}
        
    def __init__(self, factory_id, 
            allow_addresses = False, has_addresses = False,
            allow_routes = False, has_routes = False,
            Help = None, category = None):
        super(Factory, self).__init__()
        self._factory_id = factory_id
        self._allow_addresses = bool(allow_addresses)
        self._allow_routes = bool(allow_routes)
        self._has_addresses = bool(allow_addresses) or self._allow_addresses
        self._has_routes = bool(allow_routes) or self._allow_routes
        self._help = help
        self._category = category
        self._connector_types = list()
        self._traces = list()
        self._box_attributes = AttributesMap()
        
        if not self._has_addresses and not self._has_routes:
            self._factory = Box
        else:
            addresses = 'w' if self._allow_addresses else ('r' if self._has_addresses else '-')
            routes    = 'w' if self._allow_routes else ('r' if self._has_routes else '-')
            key = addresses+routes
            
            if key in self._box_class_cache:
                self._factory = self._box_class_cache[key]
            else:
                # Create base class
                class _factory(Box):
                    def __init__(self, guid, factory, testbed_guid, container = None):
                        super(_factory, self).__init__(guid, factory, testbed_guid, container)
                
                # Add mixins, one by one
                if allow_addresses:
                    MixIn(_factory, UserAddressableMixin)
                elif has_addresses:
                    MixIn(_factory, AddressableMixin)
                    
                if allow_routes:
                    MixIn(_factory, UserRoutableMixin)
                elif has_routes:
                    MixIn(_factory, RoutableMixin)
                
                # Put into cache
                self._box_class_cache[key] = self._factory = _factory

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
    def has_addresses(self):
        return self._has_addresses

    @property
    def has_routes(self):
        return self._has_routes

    @property
    def help(self):
        return self._help

    @property
    def category(self):
        return self._category

    @property
    def connector_types(self):
        return self._connector_types

    @property
    def traces(self):
        return self._traces

    @property
    def box_attributes(self):
        return self._box_attributes

    def add_connector_type(self, connector_type):
        self._connector_types.append(connector_type)

    def add_trace(self, trace_id, help, enabled = False):
        trace = Trace(trace_id, help, enabled)
        self._traces.append(trace)

    def add_box_attribute(self, name, help, type, value = None, range = None,
        allowed = None, flags = Attribute.NoFlags, validation_function = None):
        self._box_attributes.add_attribute(name, help, type, value, range,
                allowed, flags, validation_function)

    def create(self, guid, testbed_description):
        return self._factory(guid, self, testbed_description.guid)

    def destroy(self):
        super(Factory, self).destroy()
        self._connector_types = None

class FactoriesProvider(object):
    def __init__(self, testbed_id, testbed_version):
        super(FactoriesProvider, self).__init__()
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._factories = dict()

        metadata = Metadata(testbed_id, testbed_version) 
        for factory in metadata.build_design_factories():
            self.add_factory(factory)

    @property
    def testbed_id(self):
        return self._testbed_id

    @property
    def testbed_version(self):
        return self._testbed_version

    @property
    def factories(self):
        return self._factories.values()

    def factory(self, factory_id):
        return self._factories[factory_id]

    def add_factory(self, factory):
        self._factories[factory.factory_id] = factory

    def remove_factory(self, factory_id):
        del self._factories[factory_id]

class TestbedDescription(AttributesMap):
    def __init__(self, guid_generator, provider):
        super(TestbedDescription, self).__init__()
        self._guid_generator = guid_generator
        self._guid = guid_generator.next()
        self._provider = provider
        self._boxes = dict()
        self.graphical_info = GraphicalInfo(str(self._guid))

        metadata = Metadata(provider.testbed_id, provider.testbed_version)
        for attr in metadata.testbed_attributes().attributes:
            self.add_attribute(attr.name, attr.help, attr.type, attr.value, 
                    attr.range, attr.allowed, attr.flags, 
                    attr.validation_function)

    @property
    def guid(self):
        return self._guid

    @property
    def provider(self):
        return self._provider

    @property
    def boxes(self):
        return self._boxes.values()

    def box(self, guid):
        return self._boxes[guid] if guid in self._boxes else None

    def create(self, factory_id):
        guid = self._guid_generator.next()
        factory = self._provider.factory(factory_id)
        box = factory.create(guid, self)
        self._boxes[guid] = box
        return box

    def delete(self, guid):
        box = self._boxes[guid]
        del self._boxes[guid]
        box.destroy()

    def destroy(self):
        for guid, box in self._boxes.iteritems():
            box.destroy()
        self._boxes = None

class ExperimentDescription(object):
    def __init__(self, guid = 0):
        self._guid_generator = GuidGenerator(guid)
        self._testbed_descriptions = dict()

    @property
    def testbed_descriptions(self):
        return self._testbed_descriptions.values()

    def to_xml(self):
        parser = XmlExperimentParser()
        return parser.to_xml(self)

    def from_xml(self, xml):
        parser = XmlExperimentParser()
        parser.from_xml(self, xml)

    def testbed_description(self, guid):
        return self._testbed_descriptions[guid] \
                if guid in self._testbed_descriptions else None

    def box(self, guid):
        for testbed_description in self._testbed_descriptions.values():
            box = testbed_description.box(guid)
            if box: return box
        return None

    def add_testbed_description(self, provider):
        testbed_description = TestbedDescription(self._guid_generator, 
                provider)
        guid = testbed_description.guid
        self._testbed_descriptions[guid] = testbed_description
        return testbed_description

    def remove_testbed_description(self, testbed_description):
        guid = testbed_description.guid
        del self._testbed_descriptions[guid]

    def destroy(self):
        for testbed_description in self.testbed_descriptions:
            testbed_description.destroy()

# TODO: When the experiment xml is passed to the controller to execute it
# NetReferences in the xml need to be solved
#
#targets = re.findall(r"%target:(.*?)%", command)
#for target in targets:
#   try:
#      (family, address, port) = resolve_netref(target, AF_INET, 
#          self.server.experiment )
#      command = command.replace("%%target:%s%%" % target, address.address)
#   except:
#       continue

