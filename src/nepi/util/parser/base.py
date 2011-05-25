#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

class ExperimentData(object):
    def __init__(self):
        self.data = dict()
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.data)
    
    def __str__(self):
        from pprint import pformat
        return "%s:%s" % (self.__class__, pformat(self.data))

    @property
    def guids(self):
        return self.data.keys()

    def add_testbed_data(self, guid, testbed_id, testbed_version):
        testbed_data = dict()
        testbed_data["testbed_id"] = testbed_id
        testbed_data["testbed_version"] = testbed_version
        self.data[guid] = testbed_data

    def add_box_data(self, guid, testbed_guid, factory_id):
        box_data = dict()
        box_data["testbed_guid"] = testbed_guid
        box_data["factory_id"] = factory_id
        self.data[guid] = box_data

    def add_graphical_info_data(self, guid, x, y, width, height):
        data = self.data[guid]
        if not "graphical_info" in data:
            data["graphical_info"] = dict()
        graphical_info_data = data["graphical_info"]
        graphical_info_data["x"] = x
        graphical_info_data["y"] = y
        graphical_info_data["width"] = width
        graphical_info_data["height"] = height

    def add_factory_attribute_data(self, guid, name, value):
        data = self.data[guid]
        if not "factory_attributes" in data:
            data["factory_attributes"] = dict()
        factory_attributes_data = data["factory_attributes"]
        factory_attributes_data[name] = value

    def add_attribute_data(self, guid, name, value):
        data = self.data[guid]
        if not "attributes" in data:
            data["attributes"] = dict()
        attributes_data = data["attributes"]
        attributes_data[name] = value

    def add_trace_data(self, guid, trace_name):
        data = self.data[guid]
        if not "traces" in data:
            data["traces"] = list()
        traces_data = data["traces"]
        traces_data.append(trace_name)

    def add_connection_data(self, guid, connector_type_name, other_guid,
            other_connector_type_name):
        data = self.data[guid]
        if not "connections" in data:
            data["connections"] = dict()
        connections_data = data["connections"]
        if not connector_type_name in connections_data:
            connections_data[connector_type_name] = dict()
        connection_data = connections_data[connector_type_name]
        connection_data[other_guid] = other_connector_type_name

    def add_address_data(self, guid, autoconf, address, netprefix, 
            broadcast):
        data = self.data[guid]
        if not "addresses" in data:
            data["addresses"] = list()
        addresses_data = data["addresses"]
        address_data = dict()
        if autoconf:
            address_data["AutoConfigure"] = autoconf
        if address:
            address_data["Address"] = address
        address_data["NetPrefix"] = netprefix
        if broadcast:
            address_data["Broadcast"] = broadcast
        addresses_data.append(address_data)

    def add_route_data(self, guid, destination, netprefix, nexthop): 
        data = self.data[guid]
        if not "routes" in data:
            data["routes"] = list()
        routes_data = data["routes"]
        route_data = dict({
            "Destination": destination,
            "NetPrefix": netprefix, 
            "NextHop": nexthop 
            })
        routes_data.append(route_data)

    def is_testbed_data(self, guid):
        return True if "testbed_id" in self.data[guid] else None

    def get_testbed_data(self, guid):
        testbed_data = self.data[guid]
        return (testbed_data["testbed_id"], testbed_data["testbed_version"])

    def get_box_data(self, guid):
        box_data = self.data[guid]
        return (box_data["testbed_guid"], box_data["factory_id"])

    def get_graphical_info_data(self, guid):
        data = self.data[guid]
        if not "graphical_info" in data:
            return (0, 0, 0, 0, "") 
        graphical_info_data = data["graphical_info"]
        return (graphical_info_data["x"],
                graphical_info_data["y"],
                graphical_info_data["width"],
                graphical_info_data["height"])

    def get_factory_attribute_data(self, guid):
        data = self.data[guid]
        if not "factory_attributes" in data:
            return []
        factory_attributes_data = data["factory_attributes"]
        return [(name, value) for name, value \
                in factory_attributes_data.iteritems()]

    def get_attribute_data(self, guid, attribute=None, default=None):
        data = self.data[guid]
        if not "attributes" in data:
            if attribute is None:
                return []
            else:
                return None
        attributes_data = data["attributes"]
        if attribute is None:
            return [(name, value) for name, value \
                    in attributes_data.iteritems()]
        else:
            return attributes_data.get(attribute, default)

    def set_attribute_data(self, guid, attribute, value):
        data = self.data[guid]
        if not "attributes" in data:
            raise KeyError, "No attributes in reference OBJECT %r" % (guid,)
        attributes_data = data["attributes"]
        attributes_data[attribute] = value

    def get_trace_data(self, guid):
        data = self.data[guid]
        if not "traces" in data:
            return []
        return [trace_id for trace_id in data["traces"]]

    def get_connection_data(self, guid):
        data = self.data[guid]
        if not "connections" in data:
            return []
        connections_data = data["connections"]
        return [(connector_type_name, other_guid, other_connector_type_name) \
                    for connector_type_name, connection_data \
                        in connections_data.iteritems() \
                            for other_guid, other_connector_type_name \
                                in connection_data.iteritems()]

    def get_address_data(self, guid):
        data = self.data[guid]
        if not "addresses" in data:
            return []
        addresses_data = data["addresses"]
        return [(data["AutoConfigure"] if "AutoConfigure" in data else None,
                 data["Address"] if "Address" in data else None,
                 data["NetPrefix"] if "NetPrefix" in data else None,
                 data["Broadcast"] if "Broadcast" in data else None) \
                 for data in addresses_data]

    def get_route_data(self, guid):
        data = self.data[guid]
        if not "routes" in data:
            return []
        routes_data = data["routes"]
        return [(data["Destination"],
                 data["NetPrefix"],
                 data["NextHop"]) \
                         for data in routes_data]

class ExperimentParser(object):
    def to_data(self, experiment_description):
        data = ExperimentData()
        for testbed_description in experiment_description.testbed_descriptions:
            guid = testbed_description.guid
            testbed_id = testbed_description.provider.testbed_id
            testbed_version = testbed_description.provider.testbed_version
            data.add_testbed_data(guid, testbed_id, testbed_version)
            self.graphical_info_to_data(data, guid, 
                    testbed_description.graphical_info)
            self.attributes_to_data(data, guid, testbed_description.attributes)
            for box in testbed_description.boxes:
                data.add_box_data(box.guid, guid, box.factory_id)
                self.graphical_info_to_data(data, box.guid, box.graphical_info)
                self.factory_attributes_to_data(data, box.guid, 
                        box.factory_attributes)
                self.attributes_to_data(data, box.guid, box.attributes)
                self.traces_to_data(data, box.guid, box.traces)
                self.connections_to_data(data, box.guid, box.connectors)
                self.addresses_to_data(data, box.guid, box.addresses)
                self.routes_to_data(data, box.guid, box.routes)
        return data

    def graphical_info_to_data(self, data, guid, g_info):
        data.add_graphical_info_data(guid, g_info.x, g_info.y, g_info.width, 
                g_info.height)

    def factory_attributes_to_data(self, data, guid, factory_attributes):
        factory_attributes = factory_attributes or dict()
        for name, value in factory_attributes.iteritems():
            data.add_factory_attribute_data(guid, name, value)

    def attributes_to_data(self, data, guid, attributes):
        for attribute in attributes:
            if attribute.modified or attribute.has_no_default_value:
                data.add_attribute_data(guid, attribute.name, attribute.value)

    def traces_to_data(self, data, guid, traces):
        for trace in traces:
            if trace.enabled:
                data.add_trace_data(guid, trace.trace_id)

    def connections_to_data(self, data, guid, connectors):
        for connector in connectors:
            connector_type_name = connector.connector_type.name
            for other_connector in connector.connections:
                other_guid = other_connector.box.guid
                other_connector_type_name = other_connector.connector_type.name
                data.add_connection_data(guid, connector_type_name, other_guid,
                        other_connector_type_name)

    def addresses_to_data(self, data, guid, addresses):
        for addr in addresses:
             autoconf = addr.get_attribute_value("AutoConfigure")
             address = addr.get_attribute_value("Address")
             netprefix = addr.get_attribute_value("NetPrefix")
             broadcast = addr.get_attribute_value("Broadcast") \
                    if addr.has_attribute("Broadcast") and \
                    addr.is_attribute_modified("Broadcast") else None
             data.add_address_data(guid, autoconf, address, netprefix, 
                    broadcast)

    def routes_to_data(self, data, guid, routes):
        for route in routes:
             destination = route.get_attribute_value("Destination")
             netprefix = route.get_attribute_value("NetPrefix")
             nexthop = route.get_attribute_value("NextHop")
             data.add_route_data(guid, destination, netprefix, nexthop)

    def from_data(self, experiment_description, data):
        box_guids = list()
        for guid in data.guids:
            if data.is_testbed_data(guid):
                self.testbed_from_data(experiment_description, guid, data)
            else:
                self.box_from_data(experiment_description, guid, data)
                box_guids.append(guid)
        self.connections_from_data(experiment_description, box_guids, data)

    def testbed_from_data(self, experiment_description, guid, data):
        from nepi.core.design import FactoriesProvider
        (testbed_id, testbed_version) = data.get_testbed_data(guid)
        provider = FactoriesProvider(testbed_id, testbed_version)
        experiment_description.add_testbed_description(provider, guid)
        testbed_description = experiment_description.testbed_description(guid)
        self.graphical_info_from_data(testbed_description, data)
        self.attributes_from_data(testbed_description, data)

    def box_from_data(self, experiment_description, guid, data):
        (testbed_guid, factory_id) = data.get_box_data(guid)
        testbed_description = experiment_description.testbed_description(
                testbed_guid)
        self.factory_attributes_from_data(testbed_description, factory_id,
                guid, data)
        box = testbed_description.create(factory_id, guid)

        self.graphical_info_from_data(box, data)
        self.attributes_from_data(box, data)
        self.traces_from_data(box, data)
        self.addresses_from_data(box, data)
        self.routes_from_data(box, data)

    def graphical_info_from_data(self, element, data):
        (x, y, width, height) =  data.get_graphical_info_data(
                element.guid)
        element.graphical_info.x = x
        element.graphical_info.y = y
        element.graphical_info.width = width
        element.graphical_info.height = height

    def factory_attributes_from_data(self, testbed_description, factory_id, 
            guid, data):
        factory = testbed_description.provider.factory(factory_id)
        for (name, value) in data.get_factory_attribute_data(guid):
            factory.set_attribute_value(name, value)

    def attributes_from_data(self, element, data):
        for name, value in data.get_attribute_data(element.guid):
            element.set_attribute_value(name, value)

    def traces_from_data(self, box, data):
        for name in data.get_trace_data(box.guid):
            box.enable_trace(name)

    def addresses_from_data(self, box, data):
        for (autoconf, address, netprefix, broadcast) \
                in data.get_address_data(box.guid):
            addr = box.add_address()
            if autoconf:
                addr.set_attribute_value("AutoConfigure", autoconf)
            if address:
                addr.set_attribute_value("Address", address)
            if netprefix != None:
                addr.set_attribute_value("NetPrefix", netprefix)
            if broadcast:
                addr.set_attribute_value("Broadcast", broadcast)

    def routes_from_data(self, box, data):
         for (destination, netprefix, nexthop) \
                 in data.get_route_data(box.guid):
            addr = box.add_route()
            addr.set_attribute_value("Destination", destination)
            addr.set_attribute_value("NetPrefix", netprefix)
            addr.set_attribute_value("NextHop", nexthop)

    def connections_from_data(self, experiment_description, guids, data):
        for guid in guids:
            box = experiment_description.box(guid)
            for (connector_type_name, other_guid, other_connector_type_name) \
                    in data.get_connection_data(guid):
                    other_box = experiment_description.box(other_guid)
                    connector = box.connector(connector_type_name)
                    other_connector = other_box.connector(
                            other_connector_type_name)
                    if not connector.is_connected(other_connector):
                        connector.connect(other_connector)

