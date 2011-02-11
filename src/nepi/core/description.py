#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import validation
import sys

AF_INET = 0
AF_INET6 = 1

class ConnectorType(object):
    """A ConnectorType defines a kind of connector that can be used in an Object.
    """
    def __init__(self, connector_type_id, help, name, max = -1, min = 0):
        super(ConnectorType, self).__init__()
        """
        ConnectorType(name, help, display_name, max, min):
        - connector_type_id: (unique) identifier for this type. 
            Typically: testbed_id + factory_id + name
        - name: descriptive name for the user
        - help: help text
        - max: amount of connections that this type support, -1 for no limit
        - min: minimum amount of connections to this type of connector
        """
        if max == -1:
            max = sys.maxint
        elif max <= 0:
                raise RuntimeError(
             'The maximum number of connections allowed need to be more than 0')
        if min < 0:
            raise RuntimeError(
             'The minimum number of connections allowed needs to be at least 0')
        self._connector_type_id = connector_type_id
        self._help = help
        self._name = name
        self._max = max
        self._min = min
        # list of connector_type_ids with which this connector_type is allowed
        # to connect
        self._allowed_connector_type_ids = list()

    @property
    def connector_type_id(self):
        return self._connector_type_id

    @property
    def help(self):
        return self._help

    @property
    def name(self):
        return self._name

    @property
    def max(self):
        return self._max

    @property
    def min(self):
        return self._min

    def add_allowed_connector_type_id(self, connector_type_id):
        self._allowed_connector_type_ids.append(connector_type_id)

    def can_connect(self, connector_type_id):
        return connector_type_id in self._allowed_connector_type_ids

class Connector(object):
    """A Connector sepcifies the connection points in an Object"""
    def __init__(self, box, connector_type):
        super(Connector, self).__init__()
        self._box = box
        self._connector_type = connector_type
        self._connections = dict()

    @property
    def box(self):
        return self._box

    @property
    def connector_type(self):
        return self._connector_type

    @property
    def connections(self):
        return self._connections.values()

    def is_full(self):
        """Return True if the connector has the maximum number of connections"""
        return len(self.connections) == self.connector_type.max

    def is_complete(self):
        """Return True if the connector has the minimum number of connections"""
        return len(self.connections) >= self.connector_type.min

    def is_connected(self, connector):
        return connector._key in self._connections

    def connect(self, connector):
        if self.is_full() or connector.is_full():
            raise RuntimeError("Connector is full")    
        if not self.can_connect(connector) or not connector.can_connect(self):
            raise RuntimeError("Could not connect.")
        self._connections[connector._key] = connector
        connector._connections[self._key] = self

    def disconnect(self, connector):
        if connector._key not in self._connections or\
                self._key not in connector._connections:
                raise RuntimeError("Could not disconnect.")
        del self._connections[connector._key]
        del connector._connections[self._key]

    def can_connect(self, connector):
        connector_type_id = connector.connector_type.connector_type_id
        return self.connector_type.can_connect(connector_type_id) 

    def destroy(self):
        for connector in self._connections:
            self.disconnect(connector)
        self._box = self._connectors = None

    @property
    def _key(self):
        return "%d_%s" % (self.box.guid, 
                self.connector_type.connector_type_id)

class Trace(AttributesMap):
    def __init__(self, name, help, enabled = False):
        super(Trace, self).__init__()
        self._name = name
        self._help = help       
        self.enabled = enabled
    
    @property
    def name(self):
        return self._name

    @property
    def help(self):
        return self._help

class Address(AttributesMap):
    def __init__(self, family):
        super(Address, self).__init__()
        self.add_attribute(name = "AutoConfigure", 
                help = "If set, this address will automatically be assigned", 
                type = Attribute.BOOL,
                value = False,
                validation_function = validation.is_bool)
        self.add_attribute(name = "Family",
                help = "Address family type: AF_INET, AFT_INET6", 
                type = Attribute.INTEGER, 
                value = family,
                readonly = True)
        address_validation = validation.is_ip4_address if family == AF_INET \
                        else validation.is_ip6_address
        self.add_attribute(name = "Address",
                help = "Address number", 
                type = Attribute.STRING,
                validation_function = address_validation)
        prefix_range = (0, 32) if family == AF_INET else (0, 128)
        self.add_attribute(name = "NetPrefix",
                help = "Network prefix for the address", 
                type = Attribute.INTEGER, 
                range = prefix_range,
                validation_function = validation.is_integer)
        if family == AF_INET:
            self.add_attribute(name = "Broadcast",
                    help = "Broadcast address", 
                    type = Attribute.STRING,
                    validation_function = validation.is_ip4_address)
                
class Route(AttributesMap):
    def __init__(self, family):
        super(Route, self).__init__()
        self.add_attribute(name = "Family",
                help = "Address family type: AF_INET, AFT_INET6", 
                type = Attribute.INTEGER, 
                value = family,
                readonly = True)
        address_validation = validation.is_ip4_address if family == AF_INET \
                        else validation.is_ip6_address
        self.add_attribute(name = "Destination", 
                help = "Network destintation",
                type = Attribute.STRING, 
                validation_function = address_validation)
        prefix_range = (0, 32) if family == AF_INET else (0, 128)
        self.add_attribute(name = "NetPrefix",
                help = "Network destination prefix", 
                type = Attribute.INTEGER, 
                prefix_range = prefix_range,
                validation_function = validation.is_integer)
        self.add_attribute(name = "NextHop",
                help = "Address for the next hop", 
                type = Attribute.STRING,
                validation_function = address_validation)
        self.add_attribute(name = "Interface",
                help = "Local interface address", 
                type = Attribute.STRING,
                validation_function = address_validation)

class Box(AttributesMap):
    def __init__(self, guid, factory, container = None):
        super(Box, self).__init__()
        # general unique id
        self._guid = guid
        # factory identifier or name
        self._factory_id = factory.factory_id
        # boxes can be nested inside other 'container' boxes
        self._container = container
        # traces for the box
        self._traces = dict()
        # connectors for the box
        self._connectors = dict()
        # factory attributes for box construction
        self._factory_attributes = list()

        for connector_type in factory.connector_types:
            connector = Connector(self, connector_type)
            self._connectors[connector_type.name] = connector
        for trace in factory.traces:
            tr = Trace(trace.name, trace.help, trace.enabled)
            self._traces[trace.name] = tr
        for attr in factory.box_attributes:
            self.add_attribute(attr.name, attr.help, attr.type, attr.value, 
                    attr.range, attr.allowed, attr.readonly, 
                    attr.validation_function)
        for attr in factory.attributes:
            self._factory_attributes.append(attr)

    @property
    def guid(self):
        return self._guid

    @property
    def factory_id(self):
        return self._factory_id

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
    def factory_attributes(self):
        return self._factory_attributes

    @property
    def addresses(self):
        return []

    @property
    def routes(self):
        return []

    def connector(self, name):
        return self._connectors[name]

    def trace(self, name):
        return self._traces[name]

    def destroy(self):
        super(Box, self).destroy()
        for c in self.connectors:
            c.destroy()         
        for t in self.traces:
            t.destroy()
        self._connectors = self._traces = self._factory_attributes = None

class AddressableBox(Box):
    def __init__(self, guid, factory, family, max_addresses = 1, container = None):
        super(AddressableBox, self).__init__(guid, factory, container)
        self._family = family
        # maximum number of addresses this box can have
        self._max_addresses = max_addresses
        self._addresses = list()

    @property
    def addresses(self):
        return self._addresses

    @property
    def max_addresses(self):
        return self._max_addresses

    def add_address(self):
        if len(self._addresses) == self.max_addresses:
            raise RuntimeError("Maximun number of addresses for this box reached.")
        address = Address(family = self._family)
        self._addresses.append(address)
        return address

    def delete_address(self, address):
        self._addresses.remove(address)
        del address

    def destroy(self):
        super(AddressableBox, self).destroy()
        for address in self.addresses:
            self.delete_address(address)
        self._addresses = None

class RoutingTableBox(Box):
    def __init__(self, guid, factory, container = None):
        super(RoutingTableBox, self).__init__(guid, factory, container)
        self._routes = list()

    @property
    def routes(self):
        return self._routes

    def add_route(self, family):
        route = Route(family = family)
        self._routes.append(route)
        return route

    def delete_route(self, route):
        self._route.remove(route)
        del route

    def destroy(self):
        super(RoutingCapableBox, self).destroy()
        for route in self.routes:
            self.delete_route(route)
        self._route = None

class BoxFactory(AttributesMap):
    def __init__(self, factory_id, display_name, help = None, category = None):
        super(BoxFactory, self).__init__()
        self._factory_id = factory_id
        self._help = help
        self._category = category
        self._display_name = display_name
        self._connector_types = set()
        self._traces = list()
        self._box_attributes = list()

    @property
    def factory_id(self):
        return self._factory_id

    @property
    def help(self):
        return self._help

    @property
    def category(self):
        return self._category

    @property
    def display_name(self):
        return self._display_name

    @property
    def connector_types(self):
        return self._connector_types

    @property
    def traces(self):
        return self._traces

    @property
    def box_attributes(self):
        return self._box_attributes

    def add_connector_type(self, connector_type_id, help, name, max = -1, 
            min = 0, allowed_connector_type_ids = []):
        connector_type = ConnectorType(connector_type_id, help, name, max, min)
        for connector_type_id in allowed_connector_type_ids:
            connector_type.add_allowed_connector_type_id(connector_type_id)
        self._connector_types.add(connector_type)

    def add_trace(self, name, help, enabled = False):
        trace = Trace(name, help, enabled)
        self._traces.append(trace)

    def add_box_attribute(self, name, help, type, value = None, range = None,
        allowed = None, readonly = False, validation_function = None):
        attribute = Attribute(name, help, type, value, range, allowed, readonly,
                validation_function)
        self._box_attributes.append(attribute)

    def create(self, guid, testbed_description):
        return Box(guid, self)

    def destroy(self):
        super(BoxFactory, self).destroy()
        self._connector_types = None

class AddressableBoxFactory(BoxFactory):
    def __init__(self, factory_id, display_name, family, max_addresses = 1,
            help = None, category = None):
        super(AddressableBoxFactory, self).__init__(factory_id,
                display_name, help, category)
        self._family = family
        self._max_addresses = 1

    def create(self, guid, testbed_description):
        return AddressableBox(guid, self, self._family, 
                self._max_addresses)

class RoutingTableBoxFactory(BoxFactory):
    def create(self, guid, testbed_description):
        return RoutingTableBox(guid, self)

class FactoriesProvider(object):
    def __init__(self):
        super(FactoriesProvider, self).__init__()
        self._factories = dict()

    def factory(self, factory_id):
        return self._factories[factory_id]

    def add_factory(self, factory):
        self._factories[factory.factory_id] = factory

    def remove_factory(self, factory_id):
        del self._factories[factory_id]

    def list_factories(self):
        return self._factories.keys()

class TestbedDescription(AttributesMap):
    def __init__(self, guid_generator, testbed_id, testbed_version, provider):
        super(TestbedDescription, self).__init__()
        self._guid_generator = guid_generator
        self._guid = guid_generator.next()
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._provider = provider
        self._boxes = dict()

    @property
    def guid(self):
        return self._guid

    @property
    def testbed_id(self):
        return self._testbed_id

    @property
    def testbed_version(self):
        return self._testbed_version

    @property
    def provider(self):
        return provider

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
        for guid, box in self._boxes.iteitems():
            del self._boxes[guid]
            box.destroy()
        self._boxes = None

