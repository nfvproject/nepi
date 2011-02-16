#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute
from nepi.util.parser.base import ExperimentParser
from xml.dom import minidom

class XmlExperimentParser(ExperimentParser):
    def to_xml(self, experiment_description):
        data = self.to_data(experiment_description)
        doc = minidom.Document()        
        exp_tag = doc.createElement("experiment")
        testbeds_tag = doc.createElement("testbeds")
        exp_tag.appendChild(testbeds_tag)

        elements_tags = dict()
        for guid, elem_data in data.iteritems():
            if "testbed_id" in elem_data:
                elements_tag = self.testbed_data_to_xml(doc, testbeds_tag, guid,
                        elem_data)
                elements_tags[guid] = elements_tag
            else:
                testbed_guid = elem_data["testbed_guid"]
                elements_tag = elements_tags[testbed_guid]
                self.box_data_to_xml(doc, elements_tag, guid, elem_data)

        doc.appendChild(exp_tag)
        xml = doc.toprettyxml(indent="    ", encoding="UTF-8")
        return xml

    def testbed_data_to_xml(self, doc, parent_tag, guid, testbed_data):
        testbed_tag = doc.createElement("testbed") 
        testbed_tag.setAttribute("guid", str(guid))
        testbed_tag.setAttribute("testbed_id", str(testbed_data["testbed_id"]))
        testbed_tag.setAttribute("testbed_version", 
                str(testbed_data["testbed_version"]))
        parent_tag.appendChild(testbed_tag)
        elements_tag = doc.createElement("elements")
        testbed_tag.appendChild(elements_tag)
        return elements_tag

    def box_data_to_xml(self, doc, parent_tag, guid, box_data):
        element_tag = doc.createElement("element")
        parent_tag.appendChild(element_tag)
        element_tag.setAttribute("factory_id", str(box_data["factory_id"]))
        element_tag.setAttribute("guid", str(guid))
        if "factory_attributes" in box_data:
            self.factory_attributes_data_to_xml(doc, element_tag,
                    box_data["factory_attributes"])
        if "attributes" in box_data:
            self.attributes_data_to_xml(doc, element_tag, 
                    box_data["attributes"])
        if "traces" in box_data:
            self.traces_data_to_xml(doc, element_tag, box_data["traces"])
        if "addresses" in box_data:
            self.addresses_data_to_xml(doc, element_tag, 
                    box_data["addresses"])
        if "routes" in box_data:
            self.routes_data_to_xml(doc, element_tag, box_data["routes"])
        if "connections" in box_data:
            self.connections_data_to_xml(doc, element_tag, 
                    box_data["connections"])
        
    def factory_attributes_data_to_xml(self, doc, parent_tag, data):
        factory_attributes_tag = doc.createElement("factory_attributes") 
        parent_tag.appendChild(factory_attributes_tag)
        for name, value in data.iteritems():
            factory_attribute_tag = doc.createElement("factory_attribute") 
            factory_attributes_tag.appendChild(factory_attribute_tag)
            factory_attribute_tag.setAttribute("name", name)
            factory_attribute_tag.setAttribute("value", str(value))
            factory_attribute_tag.setAttribute("type", self.type_to_standard(value))

    def attributes_data_to_xml(self, doc, parent_tag, data):
        attributes_tag = doc.createElement("attributes") 
        parent_tag.appendChild(attributes_tag)
        for name, value in data.iteritems():
            attribute_tag = doc.createElement("attribute") 
            attributes_tag.appendChild(attribute_tag)
            attribute_tag.setAttribute("name", name)
            attribute_tag.setAttribute("value", str(value))
            attribute_tag.setAttribute("type", self.type_to_standard(value))

    def traces_data_to_xml(self, doc, parent_tag, data):
        traces_tag = doc.createElement("traces") 
        parent_tag.appendChild(traces_tag)
        for name in data:
            trace_tag = doc.createElement("trace") 
            traces_tag.appendChild(trace_tag)
            trace_tag.setAttribute("name", name)

    def addresses_data_to_xml(self, doc, parent_tag, data):
        addresses_tag = doc.createElement("addresses") 
        parent_tag.appendChild(addresses_tag)
        for address in data:
            address_tag = doc.createElement("address") 
            addresses_tag.appendChild(address_tag)
            for name, value in address.iteritems():
                address_tag.setAttribute(name, str(value))

    def routes_data_to_xml(self, doc, parent_tag, data):
        routes_tag = doc.createElement("routes") 
        parent_tag.appendChild(routes_tag)
        for route in data:
            route_tag = doc.createElement("route") 
            routes_tag.appendChild(route_tag)
            for name, value in route.iteritems():
                route_tag.setAttribute(name, str(value))

    def connections_data_to_xml(self, doc, parent_tag, data):
        connections_tag = doc.createElement("connections") 
        parent_tag.appendChild(connections_tag)
        for connector_type_id, connections in data.iteritems():
            for other_guid, other_connector_type_id in connections.iteritems():
                connection_tag = doc.createElement("connection") 
                connections_tag.appendChild(connection_tag)
                connection_tag.setAttribute("connector", connector_type_id)
                connection_tag.setAttribute("other_guid", str(other_guid))
                connection_tag.setAttribute("other_connector",
                        other_connector_type_id)

    def from_xml(self, experiment_description, xml):
        data = dict()
        doc = minidom.parseString(xml)
        testbeds_tag = doc.getElementsByTagName("testbeds")[0] 
        testbed_tag_list = testbeds_tag.getElementsByTagName("testbed")
        for testbed_tag in testbed_tag_list:
            if testbed_tag.nodeType == doc.ELEMENT_NODE:
                testbed_data = self.testbed_data_from_xml(testbed_tag)
                testbed_guid = testbed_tag.getAttribute("guid")
                data[int(testbed_guid)] = testbed_data
                elements_tag = testbed_tag.getElementsByTagName("elements")[0] 
                element_tag_list = elements_tag.getElementsByTagName("element")
                for element_tag in element_tag_list:
                    if element_tag.nodeType == doc.ELEMENT_NODE:
                        box_data = self.box_data_from_xml(testbed_guid, element_tag)
                        guid = element_tag.getAttribute("guid")
                        data[int(guid)] = box_data
        print data
        self.from_data(experiment_description, data)

    def testbed_data_from_xml(self, tag):
        testbed_id = tag.getAttribute("testbed_id")
        testbed_version = tag.getAttribute("testbed_version")
        return dict({
            "testbed_id": str(testbed_id), 
            "testbed_version": str(testbed_version),
            })

    def box_data_from_xml(self, testbed_guid, tag):
        factory_id = tag.getAttribute("factory_id")
        data = dict({
            "testbed_guid": int(testbed_guid),
            "factory_id": str(factory_id)
            })
        self.factory_attributes_data_from_xml(data, tag)
        self.attributes_data_from_xml(data, tag)
        self.traces_data_from_xml(data, tag)
        self.addresses_data_from_xml(data, tag)
        self.routes_data_from_xml(data, tag)
        self.connections_data_from_xml(data, tag)
        return data
        
    def factory_attributes_data_from_xml(self, data, tag):
        factory_attributes_tag_list = tag.getElementsByTagName(
                "factory_attributes")
        if len(factory_attributes_tag_list) == 0:
            return

        factory_attribute_tag_list = factory_attributes_tag_list[0].\
                getElementsByTagName("factory_attribute")
        factory_attributes_data = dict()
        for factory_attribute_tag in factory_attribute_tag_list:
             if factory_attribute_tag.nodeType == tag.ELEMENT_NODE:
                name = factory_attribute_tag.getAttribute("name")
                value = factory_attribute_tag.getAttribute("value")
                std_type = factory_attribute_tag.getAttribute("type")
                value = self.type_from_standard(std_type, value)
                factory_attributes_data[str(name)] = value
        data["factory_attributes"] = factory_attributes_data
    
    def attributes_data_from_xml(self, data, tag):
        attributes_tag_list= tag.getElementsByTagName("attributes")
        if len(attributes_tag_list) == 0:
            return

        attribute_tag_list = attributes_tag_list[0].\
                getElementsByTagName("attribute")
        attributes_data = dict()
        for attribute_tag in attribute_tag_list:
             if attribute_tag.nodeType == tag.ELEMENT_NODE:
                name = attribute_tag.getAttribute("name")
                value = attribute_tag.getAttribute("value")
                std_type = attribute_tag.getAttribute("type")
                value = self.type_from_standard(std_type, value)
                attributes_data[str(name)] = value
        data["attributes"] = attributes_data

    def traces_data_from_xml(self, data, tag):
        traces_tag_list = tag.getElementsByTagName("traces")
        if len(traces_tag_list) == 0:
            return

        trace_tag_list = traces_tag_list[0].getElementsByTagName(
                "trace")
        traces_data = list()
        for trace_tag in trace_tag_list:
             if trace_tag.nodeType == tag.ELEMENT_NODE:
                name = trace_tag.getAttribute("name")
                traces_data.append(name)
        data["traces"] = traces_data

    def addresses_data_from_xml(self, data, tag):
        addresses_tag_list = tag.getElementsByTagName("addresses")
        if len(addresses_tag_list) == 0:
            return

        address_tag_list = addresses_tag_list[0].\
                getElementsByTagName("address")
        addresses_data = list()
        address_attributes = dict({"AutoConfigure": Attribute.BOOL, 
            "Address": Attribute.STRING,
            "Family": Attribute.INTEGER,
            "NetPrefix": Attribute.INTEGER,
            "Broadcast": Attribute.STRING 
            })
        for address_tag in address_tag_list:
            if address_tag.nodeType == tag.ELEMENT_NODE:
                address_data = dict()
                for attr_name in address_attributes.keys():
                    if address_tag.hasAttribute(attr_name):
                        value = address_tag.getAttribute(attr_name)
                        type = address_attributes[attr_name]
                        address_data[attr_name] = self.type_from_standard(
                                type, value)
                addresses_data.append(address_data)
        data["addresses"] = addresses_data

    def routes_data_from_xml(self, data, tag):
        routes_tag_list = tag.getElementsByTagName("routes")
        if len(routes_tag_list) == 0:
            return

        route_tag_list = routes_tag_list[0].getElementsByTagName("route")
        routes_data = list()
        route_attributes = dict({"Family": Attribute.INTEGER,
            "Destination": Attribute.STRING,
            "NetPrefix": Attribute.INTEGER,
            "NextHop": Attribute.STRING,
            "Interface": Attribute.STRING,
            })
        for route_tag in route_tag_list:
            if address_tag.nodeType == tag.ELEMENT_NODE:
                route_data = dict()
                for attr_name in route_attributes.keys():
                    if route_tag.hasAttribute(attr_name):
                        value = route_tag.getAttribute(attr_name)
                        type = route_attributes[attr_name]
                        route_data[attr_name] = self.type_from_standard(
                                type, value)
                routes_data.append(route_data)
        data["routes"] = routes_data

    def connections_data_from_xml(self, data, tag):
        connections_tag_list = tag.getElementsByTagName("connections")
        if len(connections_tag_list) == 0:
            return

        connection_tag_list = connections_tag_list[0].getElementsByTagName(
                "connection")
        connections_data = dict()
        for connection_tag in connection_tag_list:
             if connection_tag.nodeType == tag.ELEMENT_NODE:
                 connector = connection_tag.getAttribute("connector")
                 other_connector = connection_tag.getAttribute(
                         "other_connector")
                 other_guid = connection_tag.getAttribute("other_guid")
                 if not connector in connections_data:
                     connections_data[str(connector)] = dict()
                 connection_data = connections_data[str(connector)]
                 connection_data[int(other_guid)] = str(other_connector)
        data["connections"] = connections_data

    def type_to_standard(self, value):
        if type(value) == str:
            return Attribute.STRING
        if type(value) == bool:
            return Attribute.BOOL
        if type(value) == int:
            return Attribute.INTEGER
        if type(value) == float:
            return Attribute.DOUBLE
    
    def type_from_standard(self, type, value):
        if type == Attribute.STRING:
            return str(value)
        if type == Attribute.BOOL:
            return bool(value)
        if type == Attribute.INTEGER:
            return int(value)
        if type == Attribute.DOUBLE:
            return float(value)

