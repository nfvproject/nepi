#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Experiment design API
"""

from nepi.core.attributes import AttributesMap, Attribute
from nepi.core.metadata import Metadata
from nepi.util import validation
from nepi.util.guid import GuidGenerator
from nepi.util.graphical_info import GraphicalInfo
from nepi.util.parser._xml import XmlExperimentParser
from nepi.util.tags import Taggable
import sys

class Connector(object):
    """A Connector sepcifies the connection points in an Object"""
    def __init__(self, box, connector_type):
        super(Connector, self).__init__()
        self._box = box
        self._connector_type = connector_type
        self._connections = list()

    def __str__(self):
        return "Connector(%s, %s)" % (self.box, self.connector_type)

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
            raise RuntimeError("Could not connect. %s to %s" % (self, connector))
        self._connections.append(connector)
        connector._connections.append(self)

    def disconnect(self, connector):
        if connector not in self._connections or\
                self not in connector._connections:
                raise RuntimeError("Could not disconnect.")
        self._connections.remove(connector)
        connector._connections.remove(self)

    def can_connect(self, connector):
        # can't connect with self
        if self.box.guid == connector.box.guid:
            return False
        if self.is_full() or connector.is_full():
            return False
        if self.is_connected(connector):
            return False
        (testbed_id, factory_id, name) = connector.connector_type.connector_type_id
        testbed_guid1 = self.box.testbed_guid
        testbed_guid2 = connector.box.testbed_guid
        must_cross = (testbed_guid1 != testbed_guid2)
        return self.connector_type.can_connect(testbed_id, factory_id, name,
                must_cross)

    def destroy(self):
        for connector in self.connections:
            self.disconnect(connector)
        self._box = self._connectors = None

class Trace(AttributesMap):
    def __init__(self, name, help, enabled = False):
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
    def enabled(self):
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

class Address(AttributesMap):
    def __init__(self):
        super(Address, self).__init__()
        self.add_attribute(name = "Address",
                help = "Address number", 
                type = Attribute.STRING,
                flags = Attribute.NoDefaultValue,
                validation_function = validation.is_ip_address)
        self.add_attribute(name = "NetPrefix",
                help = "Network prefix for the address", 
                type = Attribute.INTEGER, 
                range = (0, 128),
                value = 24,
                flags = Attribute.NoDefaultValue,
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
                validation_function = validation.is_ref_address)
        self.add_attribute(name = "NetPrefix",
                help = "Network destination prefix", 
                type = Attribute.INTEGER, 
                range = (0, 128),
                value = 24,
                flags = Attribute.NoDefaultValue,
                validation_function = validation.is_integer)
        self.add_attribute(name = "NextHop",
                help = "Address for the next hop", 
                type = Attribute.STRING,
                flags = Attribute.NoDefaultValue,
                validation_function = validation.is_ref_address)
        self.add_attribute(name = "Metric",
                help = "Routing metric", 
                type = Attribute.INTEGER,
                value = 0,
                flags = Attribute.NoDefaultValue,
                validation_function = validation.is_integer)

class Box(AttributesMap, Taggable):
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
        self.graphical_info = GraphicalInfo()

        for connector_type in factory.connector_types:
            connector = Connector(self, connector_type)
            self._connectors[connector_type.name] = connector
        for (name, help, enabled) in factory.traces:
            trace = Trace(name, help, enabled)
            self._traces[name] = trace
        for tag_id in factory.tags:
            self.add_tag(tag_id)
        for attr in factory.box_attributes.attributes:
            self.add_attribute(attr.name, attr.help, attr.type, attr.value, 
                    attr.range, attr.allowed, attr.flags, 
                    attr.validation_function, attr.category)
        for attr in factory.attributes:
            if attr.modified or attr.is_metadata:
                self._factory_attributes[attr.name] = attr.value

    def __str__(self):
        return "Box(%s, %s, %s)" % (self.guid, self.factory_id, self.testbed_guid)

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
    def traces_list(self):
        return self._traces.keys()

    @property
    def factory_attributes(self):
        return self._factory_attributes

    def trace_help(self, trace_id):
        return self._traces[trace_id].help

    def enable_trace(self, trace_id):
        self._traces[trace_id].enable()

    def disable_trace(self, trace_id):
        self._traces[trace_id].disable()

    def is_trace_enabled(self, trace_id):
        return self._traces[trace_id].enabled

    def connector(self, name):
        return self._connectors[name]

    def destroy(self):
        super(Box, self).destroy()
        for c in self.connectors:
            c.destroy()         
        for t in self.traces:
            t.destroy()
        self._connectors = self._traces = self._factory_attributes = None

class FactoriesProvider(object):
    def __init__(self, testbed_id):
        super(FactoriesProvider, self).__init__()
        self._testbed_id = testbed_id
        self._factories = dict()

        metadata = Metadata(testbed_id) 
        for factory in metadata.build_factories():
            self.add_factory(factory)

        self._testbed_version = metadata.testbed_version

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
    def __init__(self, guid_generator, provider, guid = None):
        super(TestbedDescription, self).__init__()
        self._guid_generator = guid_generator
        self._guid = guid_generator.next(guid)
        self._provider = provider
        self._boxes = dict()
        self.graphical_info = GraphicalInfo()

        metadata = Metadata(provider.testbed_id)
        for attr in metadata.testbed_attributes().attributes:
            self.add_attribute(attr.name, attr.help, attr.type, attr.value, 
                    attr.range, attr.allowed, attr.flags, 
                    attr.validation_function, attr.category)

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

    def create(self, factory_id, guid = None):
        guid = self._guid_generator.next(guid)
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
    def __init__(self):
        self._guid_generator = GuidGenerator()
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

    def get_element(self, guid):
        if guid in self._testbed_descriptions:
            return self._testbed_descriptions[guid]
        for testbed_description in self._testbed_descriptions.values():
            box = testbed_description.box(guid)
            if box: return box
        return None

    def add_testbed_description(self, provider, guid = None):
        testbed_description = TestbedDescription(self._guid_generator, 
                provider, guid)
        guid = testbed_description.guid
        self._testbed_descriptions[guid] = testbed_description
        return testbed_description

    def remove_testbed_description(self, guid):
        testbed_description = self._testbed_descriptions[guid]
        del self._testbed_descriptions[guid]
        testbed_description.destroy()

    def destroy(self):
        for testbed_description in self.testbed_descriptions:
            testbed_description.destroy()


