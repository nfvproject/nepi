#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et:ai:sts=4
from nepi.core.attributes import AttributesMap

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

    def read_trace(self):
        raise NotImplementedError

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

class Element(AttributesMap):
    def __init__(self, guid, factory, container = None):
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
        from nepi.core.connection import Connector
        for connector_type in factory.connector_types:
            connector = Connector(self, connector_type)
            self._connectors[connector_type.name] = connector

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
    def connections(self):
        r = set()
        for c in self.connectors:
            r.update(c.connections)
        return r

    @property
    def connectors(self):
        return self._connectors.values()

    @property
    def traces(self):
        return self._traces.values()

    @property
    def instructions(self):
        raise NotImplementedError

    def connector(self, name):
        return self._connectors[name]

    def trace(self, name):
        return self._traces[name]

    def destroy(self):
        super(Element, self).destroy()
        for c in self.connections:
            c.disconnect()
        if len(self.connections) != 0:
            raise AttributeError('Some connections could not be disconnected')
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

    def add_connector_type(self, name, help, display_name, max = -1, min = 0):
        from nepi.core.connection import ConnectorType
        connector_type = ConnectorType(name, help, display_name, max, min)            
        self._connector_types.add(connector_type)

    def create(self, guid, backend, container = None):
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

class Backend(AttributeMap):
    def __init__(self, guid_generator, testbed_id, provider):
        super(Backend, self).__init__()
        self._guid_generator = guid_generator
        self._guid = guid_generator.next()
        self._testbed_id = testbed_id
        self._provider = provider
        self._elements = dict()

    @property
    def guid(self):
        return self._guid

    @property
    def testbed_id(self):
        return self._testbed_id

    @property
    def elements(self):
        return self._elements.values()

    def create(self, factory_id):
        guid = self.guid_generator.next()
        factory = self._provider.factories(factory_id)
        element = factory.create(guid, self)
        self._elements[guid] = element

    def remove(self, guid):
        element = self._elements[guid]
        del self._elements[guid]
        element.destroy()

    def instructions(self):
        raise NotImplementedError

    def destroy(self):
        for guid, element in self._elements.iteitems():
            del self._elements[guid]
            element.destroy()
        self._elements = None

