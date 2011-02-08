#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nepi.core.attributes import AttributesMap

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
        self._allowed_connections = list()

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

    def add_allowed_connection(self, connector_type_id):
        self._allowed_connections.append(connector_type_id)

    def can_connect(self, connector_type_id):
        return connector_type_id in self._allowed_connections

class Connector(object):
    """A Connector sepcifies the connection points in an Object"""
    def __init__(self, element, connector_type):
        super(Connector, self).__init__()
        self._element = element
        self._connector_type = connector_type
        self._connections = dict()

    @property
    def element(self):
        return self._element

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

    def connect(self, connector):
        if self.is_full() or connector.is_full():
            raise RuntimeError("Connector is full")    
        if not self.can_connect(connector) or not connector.can_connect(self):
            raise RuntimeError("Could not connect.")
        self._connections[connector._key] = connector
        connector._connections[self._key] = self

    def disconnect(self, connector):
        if connector._key not in self._connections or 
            self._key not in connector._connections:
                raise RuntimeError("Could not disconnect.")
        del self._connections[connector._key]
        del connector._connections[self._key]

    def can_connect(self, connector):
        connector_type_id = connector.connector_type.connector_type_id
        self.connector_type.can_connect(connector_type_id) 

    def destroy(self):
        for connector in self._connections:
            self.disconnect(connector)
        self._element = self._connectors = None

    @property
    def _key(self):
        return "%d_%s" % (self.element.guid, 
                self.connector_type.connector_type_id)

class Trace(AttributesMap):
    def __init__(self, name, help, enabled=False):
        super(Trace, self).__init__()
        self._name = name
        self._help = help       
        self._enabled = enabled
    
    @property
    def name(self):
        return self._name

    @property
    def help(self):
        return self._help

    @property
    def is_enabled(self):
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

class Element(AttributesMap):
    def __init__(self, guid, testbed_id, factory, container = None):
        super(Element, self).__init__()
        # general unique id
        self._guid = guid
        # factory identifier or name
        self._factory_id = factory.factory_id
        # elements can be nested inside other 'container' elements
        self._container = container
        # traces for the element
        self._traces = dict()
        # connectors for the element
        self._connectors = dict()
        for connector_type in factory.connector_types:
            connector = Connector(self, connector_type)
            self._connectors[connector_type.connector_id] = connector

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

    def connector(self, name):
        return self._connectors[name]

    def trace(self, name):
        return self._traces[name]

    def destroy(self):
        super(Element, self).destroy()
        for c in self.connectors:
            c.destroy()         
        for t in self.traces:
            t.destroy()
        self._connectors = self._traces = None

class Factory(AttributesMap):
    def __init__(self, factory_id, help = None, category = None):
        super(Factory, self).__init__()
        self._factory_id = factory_id
        self._help = help
        self._category = category
        self._connector_types = set()

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
    def connector_types(self):
        return self._connector_types

    def add_connector_type(self, connector_id, help, name, max = -1, min = 0):
        connector_type = ConnectorType(connector_id, help, name, max, min)            
        self._connector_types.add(connector_type)

    def create(self, guid, testbed_design, container = None):
        raise NotImplementedError

    def destroy(self):
        super(Factory, self).destroy()
        self._connector_types = None

#TODO: Provide some way to identify that the providers and the factories
# belong to a specific testbed version
class Provider(object):
    def __init__(self):
        super(Provider, self).__init__()
        self._factories = dict()

    def factory(self, factory_id):
        return self._factories[factory_id]

    def add_factory(self, factory):
        self._factories[factory.factory_id] = factory

    def remove_factory(self, factory_id):
        del self._factories[factory_id]

    def list_factories(self):
        return self._factories.keys()

class TestbedDescription(AttributeMap):
    def __init__(self, guid_generator, testbed_id, testbed_version, provider):
        super(TestbedDescription, self).__init__()
        self._guid_generator = guid_generator
        self._guid = guid_generator.next()
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._provider = provider
        self._elements = dict()

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
    def elements(self):
        return self._elements.values()

    def create(self, factory_id):
        guid = self.guid_generator.next()
        factory = self._provider.factories(factory_id)
        element = factory.create(guid, self)
        self._elements[guid] = element

    def delete(self, guid):
        element = self._elements[guid]
        del self._elements[guid]
        element.destroy()

    def destroy(self):
        for guid, element in self._elements.iteitems():
            del self._elements[guid]
            element.destroy()
        self._elements = None

