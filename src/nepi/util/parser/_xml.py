#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute
from nepi.util.parser.base import ExperimentData, ExperimentParser
from xml.dom import minidom

class XmlExperimentParser(ExperimentParser):
    def to_xml(self, experiment_description):
        data = self.to_data(experiment_description)
        doc = minidom.Document()        
        exp_tag = doc.createElement("experiment")
        testbeds_tag = doc.createElement("testbeds")
        exp_tag.appendChild(testbeds_tag)

        elements_tags = dict()
        for guid in data.guids:
            if data.is_testbed_data(guid):
                elements_tag = self.testbed_data_to_xml(doc, testbeds_tag, guid, data)
                elements_tags[guid] = elements_tag
            else:
                self.box_data_to_xml(doc, elements_tags, guid, data)
        doc.appendChild(exp_tag)
        xml = doc.toprettyxml(indent="    ", encoding="UTF-8")
        return xml

    def testbed_data_to_xml(self, doc, parent_tag, guid, data):
        testbed_tag = doc.createElement("testbed") 
        testbed_tag.setAttribute("guid", str(guid))
        (testbed_id, testbed_version) = data.get_testbed_data(guid)
        testbed_tag.setAttribute("testbed_id", str(testbed_id))
        testbed_tag.setAttribute("testbed_version", str(testbed_version))
        parent_tag.appendChild(testbed_tag)
        self.graphical_info_data_to_xml(doc, testbed_tag, guid, data)
        self.attributes_data_to_xml(doc, testbed_tag, guid, data)
        elements_tag = doc.createElement("elements")
        testbed_tag.appendChild(elements_tag)
        return elements_tag

    def box_data_to_xml(self, doc, elements_tags, guid, data):
        (testbed_guid, factory_id) = data.get_box_data(guid)
        element_tag = doc.createElement("element")
        parent_tag = elements_tags[testbed_guid]
        parent_tag.appendChild(element_tag)
        element_tag.setAttribute("factory_id", factory_id)
        element_tag.setAttribute("guid", str(guid))
        self.graphical_info_data_to_xml(doc, element_tag, guid, data)
        self.factory_attributes_data_to_xml(doc, element_tag, guid, data)
        self.attributes_data_to_xml(doc, element_tag, guid, data)
        self.traces_data_to_xml(doc, element_tag, guid, data)
        self.addresses_data_to_xml(doc, element_tag, guid, data)
        self.routes_data_to_xml(doc, element_tag, guid, data)
        self.connections_data_to_xml(doc, element_tag, guid, data)

    def graphical_info_data_to_xml(self, doc, parent_tag, guid, data):
        graphical_info_tag = doc.createElement("graphical_info") 
        parent_tag.appendChild(graphical_info_tag)
        (x, y, width, height, label) = data.get_graphical_info_data(guid)
        graphical_info_tag.setAttribute("x", str(x))
        graphical_info_tag.setAttribute("y", str(y))
        graphical_info_tag.setAttribute("width", str(width))
        graphical_info_tag.setAttribute("height", str(height))
        graphical_info_tag.setAttribute("label", str(label))

    def factory_attributes_data_to_xml(self, doc, parent_tag, guid, data):
        factory_attributes_tag = doc.createElement("factory_attributes")
        for (name, value) in data.get_factory_attribute_data(guid):
            factory_attribute_tag = doc.createElement("factory_attribute") 
            factory_attributes_tag.appendChild(factory_attribute_tag)
            factory_attribute_tag.setAttribute("name", name)
            factory_attribute_tag.setAttribute("value", str(value))
            factory_attribute_tag.setAttribute("type", self.type_to_standard(value))
        if factory_attributes_tag.hasChildNodes():
            parent_tag.appendChild(factory_attributes_tag)

    def attributes_data_to_xml(self, doc, parent_tag, guid, data):
        attributes_tag = doc.createElement("attributes") 
        for name, value in data.get_attribute_data(guid):
            attribute_tag = doc.createElement("attribute") 
            attributes_tag.appendChild(attribute_tag)
            attribute_tag.setAttribute("name", name)
            attribute_tag.setAttribute("value", str(value))
            attribute_tag.setAttribute("type", self.type_to_standard(value))
        if attributes_tag.hasChildNodes():
            parent_tag.appendChild(attributes_tag)

    def traces_data_to_xml(self, doc, parent_tag, guid, data):
        traces_tag = doc.createElement("traces") 
        for name in data.get_trace_data(guid):
            trace_tag = doc.createElement("trace") 
            traces_tag.appendChild(trace_tag)
            trace_tag.setAttribute("name", name)
        if traces_tag.hasChildNodes():
            parent_tag.appendChild(traces_tag)

    def addresses_data_to_xml(self, doc, parent_tag, guid, data):
        addresses_tag = doc.createElement("addresses") 
        for (autoconfigure, address, family, netprefix, broadcast) \
                in data.get_address_data(guid):
            address_tag = doc.createElement("address") 
            addresses_tag.appendChild(address_tag)
            if autoconfigure:
                address_tag.setAttribute("AutoConfigure", str(autoconf))
            if address:
                address_tag.setAttribute("Address", str(address))
            address_tag.setAttribute("Family", str(family))
            address_tag.setAttribute("NetPrefix", str(netprefix))
            if broadcast:
                address_tag.setAttribute("Broadcast", str(broadcast))
        if addresses_tag.hasChildNodes():
            parent_tag.appendChild(addresses_tag)

    def routes_data_to_xml(self, doc, parent_tag, guid, data):
        routes_tag = doc.createElement("routes") 
        for (family, destination, netprefix, nexthop) \
                in data.get_route_data(guid):
            route_tag = doc.createElement("route") 
            routes_tag.appendChild(route_tag)
            route_tag.setAttribute("Family", str(family))
            route_tag.setAttribute("Destination", str(destination))
            route_tag.setAttribute("NetPrefix", str(netprefix))
            route_tag.setAttribute("NextHop", str(nexthop))
        if routes_tag.hasChildNodes():
            parent_tag.appendChild(routes_tag)

    def connections_data_to_xml(self, doc, parent_tag, guid, data):
        connections_tag = doc.createElement("connections") 
        for (connector_type_name, other_guid, other_connector_type_name) \
                in data.get_connection_data(guid):
                connection_tag = doc.createElement("connection") 
                connections_tag.appendChild(connection_tag)
                connection_tag.setAttribute("connector", connector_type_name)
                connection_tag.setAttribute("other_guid", str(other_guid))
                connection_tag.setAttribute("other_connector",
                        other_connector_type_name)
        if connections_tag.hasChildNodes():
            parent_tag.appendChild(connections_tag)

    def from_xml_to_data(self, xml):
        data = ExperimentData()
        doc = minidom.parseString(xml)
        testbeds_tag = doc.getElementsByTagName("testbeds")[0] 
        testbed_tag_list = testbeds_tag.getElementsByTagName("testbed")
        for testbed_tag in testbed_tag_list:
            if testbed_tag.nodeType == doc.ELEMENT_NODE:
                testbed_guid = int(testbed_tag.getAttribute("guid"))
                elements_tag = testbed_tag.getElementsByTagName("elements")[0] 
                elements_tag = testbed_tag.removeChild(elements_tag)
                self.testbed_data_from_xml(testbed_tag, data)
                element_tag_list = elements_tag.getElementsByTagName("element")
                for element_tag in element_tag_list:
                    if element_tag.nodeType == doc.ELEMENT_NODE:
                        self.box_data_from_xml(element_tag, testbed_guid, data)
        return data

    def from_xml(self, experiment_description, xml):
        data = self.from_xml_to_data(xml)
        self.from_data(experiment_description, data)

    def testbed_data_from_xml(self, tag, data):
        testbed_guid = int(tag.getAttribute("guid"))
        testbed_id = str(tag.getAttribute("testbed_id"))
        testbed_version = str(tag.getAttribute("testbed_version"))
        data.add_testbed_data(testbed_guid, testbed_id, testbed_version)
        self.graphical_info_data_from_xml(tag, testbed_guid, data)
        self.attributes_data_from_xml(tag, testbed_guid, data)

    def box_data_from_xml(self, tag, testbed_guid, data):
        guid = int(tag.getAttribute("guid"))
        factory_id = str(tag.getAttribute("factory_id"))
        data.add_box_data(guid, testbed_guid, factory_id)
        self.graphical_info_data_from_xml(tag, guid, data)
        self.factory_attributes_data_from_xml(tag, guid, data)
        self.attributes_data_from_xml(tag, guid, data)
        self.traces_data_from_xml(tag, guid, data)
        self.addresses_data_from_xml(tag, guid, data)
        self.routes_data_from_xml(tag, guid, data)
        self.connections_data_from_xml(tag, guid, data)

    def graphical_info_data_from_xml(self, tag, guid, data):
        graphical_info_tag_list = tag.getElementsByTagName(
                "graphical_info")
        if len(graphical_info_tag_list) == 0:
            return

        graphical_info_tag = graphical_info_tag_list[0]
        if graphical_info_tag.nodeType == tag.ELEMENT_NODE:
            x = float(graphical_info_tag.getAttribute("x"))
            y = float(graphical_info_tag.getAttribute("y"))
            width = float(graphical_info_tag.getAttribute("width"))
            height = float(graphical_info_tag.getAttribute("height"))
            label = str(graphical_info_tag.getAttribute("label"))
            data.add_graphical_info_data(guid, x, y, width, height, label)

    def factory_attributes_data_from_xml(self, tag, guid, data):
        factory_attributes_tag_list = tag.getElementsByTagName(
                "factory_attributes")
        if len(factory_attributes_tag_list) == 0:
            return

        factory_attribute_tag_list = factory_attributes_tag_list[0].\
                getElementsByTagName("factory_attribute")
        for factory_attribute_tag in factory_attribute_tag_list:
             if factory_attribute_tag.nodeType == tag.ELEMENT_NODE:
                name = str(factory_attribute_tag.getAttribute("name"))
                value = factory_attribute_tag.getAttribute("value")
                std_type = factory_attribute_tag.getAttribute("type")
                value = self.type_from_standard(std_type, value)
                data.add_factory_attribute_data(guid, name, value)

    def attributes_data_from_xml(self, tag, guid, data):
        attributes_tag_list= tag.getElementsByTagName("attributes")
        if len(attributes_tag_list) == 0:
            return

        attribute_tag_list = attributes_tag_list[0].\
                getElementsByTagName("attribute")
        for attribute_tag in attribute_tag_list:
             if attribute_tag.nodeType == tag.ELEMENT_NODE:
                name = str(attribute_tag.getAttribute("name"))
                value = attribute_tag.getAttribute("value")
                std_type = attribute_tag.getAttribute("type")
                value = self.type_from_standard(std_type, value)
                data.add_attribute_data(guid, name, value)

    def traces_data_from_xml(self, tag, guid, data):
        traces_tag_list = tag.getElementsByTagName("traces")
        if len(traces_tag_list) == 0:
            return

        trace_tag_list = traces_tag_list[0].getElementsByTagName(
                "trace")
        for trace_tag in trace_tag_list:
             if trace_tag.nodeType == tag.ELEMENT_NODE:
                name = str(trace_tag.getAttribute("name"))
                data.add_trace_data(guid, name)

    def addresses_data_from_xml(self, tag, guid, data):
        addresses_tag_list = tag.getElementsByTagName("addresses")
        if len(addresses_tag_list) == 0:
            return

        address_tag_list = addresses_tag_list[0].\
                getElementsByTagName("address")
        for address_tag in address_tag_list:
            if address_tag.nodeType == tag.ELEMENT_NODE:
                autoconf = address_tag.getAttribute("AutoConfigure") == "True" \
                       if address_tag.hasAttribute("AutoConfigure") else None
                address = str(address_tag.getAttribute("Address")) \
                       if address_tag.hasAttribute("Address") else None
                family = int(address_tag.getAttribute("Family")) \
                       if address_tag.hasAttribute("Family") else None
                netprefix = int(address_tag.getAttribute("NetPrefix")) \
                       if address_tag.hasAttribute("NetPrefix") else None
                broadcast = str(address_tag.getAttribute("Broadcast")) \
                       if address_tag.hasAttribute("Broadcast") else None
                data.add_address_data(guid, autoconf, address, family, 
                    netprefix, broadcast)

    def routes_data_from_xml(self, tag, guid, data):
        routes_tag_list = tag.getElementsByTagName("routes")
        if len(routes_tag_list) == 0:
            return

        route_tag_list = routes_tag_list[0].getElementsByTagName("route")
        for route_tag in route_tag_list:
            if route_tag.nodeType == tag.ELEMENT_NODE:
                family = int(route_tag.getAttribute("Family"))
                destination = str(route_tag.getAttribute("Destination"))
                netprefix = int(route_tag.getAttribute("NetPrefix"))
                nexthop = str(route_tag.getAttribute("NextHop"))
                data.add_route_data(guid, family, destination, netprefix, 
                        nexthop)

    def connections_data_from_xml(self, tag, guid, data):
        connections_tag_list = tag.getElementsByTagName("connections")
        if len(connections_tag_list) == 0:
            return

        connection_tag_list = connections_tag_list[0].getElementsByTagName(
                "connection")
        for connection_tag in connection_tag_list:
             if connection_tag.nodeType == tag.ELEMENT_NODE:
                 connector_type_name = str(connection_tag.getAttribute(
                     "connector"))
                 other_connector_type_name = str(connection_tag.getAttribute(
                         "other_connector"))
                 other_guid = int(connection_tag.getAttribute("other_guid"))
                 data.add_connection_data(guid, connector_type_name, 
                         other_guid, other_connector_type_name)

    def type_to_standard(self, value):
        if isinstance(value, str):
            return Attribute.STRING
        if isinstance(value, bool):
            return Attribute.BOOL
        if isinstance(value, int):
            return Attribute.INTEGER
        if isinstance(value, float):
            return Attribute.DOUBLE
    
    def type_from_standard(self, type, value):
        if type == Attribute.STRING:
            return str(value)
        if type == Attribute.BOOL:
            return value == "True"
        if type == Attribute.INTEGER:
            return int(value)
        if type == Attribute.DOUBLE:
            return float(value)

