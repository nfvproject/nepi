# -*- coding: utf-8 -*-

from nepi.design import attributes, tags
from xml.dom import minidom

import sys

def xmlencode(s):
    if isinstance(s, str):
        rv = s.decode("latin1")
    elif not isinstance(s, unicode):
        rv = unicode(s)
    else:
        rv = s
    return rv.replace(u'\x00',u'&#0000;')

def xmldecode(s):
    return s.replace(u'&#0000',u'\x00').encode("utf8")

def to_attribute_type(value):
    if isinstance(value, str):
        return attributes.AttributeTypes.STRING
    if isinstance(value, bool):
        return attributes.AttributeTypes.BOOL
    if isinstance(value, int):
        return attributes.AttributeTypes.INTEGER
    if isinstance(value, float):
        return attributes.AttributeTypes.DOUBLE

def from_attribute_type(type, value):
    if type == attributes.AttributeTypes.STRING:
        return str(value)
    if type == attributes.AttributeTypes.BOOL:
        return value == "True"
    if type == attributes.AttributeTypes.INTEGER:
        return int(value)
    if type == attributes.AttributeTypes.DOUBLE:
        return float(value)

class XMLBoxParser(object):
    def to_xml(self, box):
        doc = minidom.Document()        
        root_tag = doc.createElement("scenario")

        # boxes in the serialization domain
        def guids(box, l = []):
            for b in box.boxes:
                l = guids(b, l)
            l.append(box.guid)
            return l

        self.box_to_xml(box, root_tag, doc, guids(box))
        doc.appendChild(root_tag)
        
        try:
            xml = doc.toprettyxml(indent="    ", encoding="UTF-8")
        except:
            print >>sys.stderr, "Oops: generating XML from %s" % (data,)
            raise
        
        return xml

    def box_to_xml(self, box, p_tag, doc, guids):
        b_tag = doc.createElement("box")
        b_tag.setAttribute("guid", xmlencode(box.guid))
        b_tag.setAttribute("testbed_id", xmlencode(box.testbed_id))
        b_tag.setAttribute("box_id", xmlencode(box.box_id))
        self.graphical_info_to_xml(box, b_tag, doc)
        self.attributes_to_xml(box, b_tag, doc)
        self.connections_to_xml(box, b_tag, doc, guids)

        if tags.CONTAINER in box.tags:
            self.exposed_attributes_to_xml(box, b_tag, doc)
            self.exposed_connectors_to_xml(box, b_tag, doc)

        for b in box.boxes:
            self.box_to_xml(b, b_tag, doc, guids)
        
        p_tag.appendChild(b_tag)

    def attributes_to_xml(self, box, tag, doc):
        attrs_tag = doc.createElement("attributes")
        for name, attr in box._attributes.iteritems():
            # Ignore exposed attributes
            if name != attr.name:
                continue
            if not attr.value:
                continue
            attr_type = to_attribute_type(attr.value)
            attr_tag = doc.createElement("attribute") 
            attr_tag.setAttribute("name", attr.name)
            attr_tag.setAttribute("value", xmlencode(attr.value))
            attr_tag.setAttribute("type", xmlencode(attr_type))
            attrs_tag.appendChild(attr_tag)
        if attrs_tag.hasChildNodes():
            tag.appendChild(attrs_tag)

    def graphical_info_to_xml(self, box, tag, doc):
        gi = box.graphical_info
        gi_tag = doc.createElement("graphical_info") 
        gi_tag.setAttribute("x", xmlencode(gi.x))
        gi_tag.setAttribute("y", xmlencode(gi.y))
        gi_tag.setAttribute("width", xmlencode(gi.width))
        gi_tag.setAttribute("height", xmlencode(gi.height))
        tag.appendChild(gi_tag)

    def connections_to_xml(self, box, tag, doc, guids):
        conns_tag = doc.createElement("connections")
        for conn in box.connections:
            (b, connector_name, other_b, other_connector_name) = conn
            # Ignore exposed connections and boxes that are not in
            # the serialization domain
            if b != box or other_b.guid not in guids:
                continue
            conn_tag = doc.createElement("connection") 
            conn_tag.setAttribute("connector", connector_name)
            conn_tag.setAttribute("other_guid", xmlencode(other_b.guid))
            conn_tag.setAttribute("other_connector", other_connector_name)
            conns_tag.appendChild(conn_tag)
        if conns_tag.hasChildNodes():
            tag.appendChild(conns_tag)

    def exposed_attributes_to_xml(self, box, tag, doc):
        exp_attrs_tag = doc.createElement("exposed_attributes")
        for name, attr in box._attributes.iteritems():
            # It is not an exposed attribute
            if name == attr.name:
                continue
            exp_attr_tag = doc.createElement("exposed_attribute") 
            exp_attr_tag.setAttribute("exposed_name", name)
            exp_attr_tag.setAttribute("attr_name", attr.name)
            exp_attr_tag.setAttribute("owner_guid", xmlencode(attr.owner.guid))
            exp_attrs_tag.appendChild(exp_attr_tag)
        if exp_attrs_tag.hasChildNodes():
            tag.appendChild(exp_attrs_tag)

    def exposed_connectors_to_xml(self, box, tag, doc):
        exp_conns_tag = doc.createElement("exposed_connectors")
        for name, conn in box._connectors.iteritems():
            # It is not an exposed connector
            if name == conn.name:
                continue
            exp_conn_tag = doc.createElement("exposed_connector") 
            exp_conn_tag.setAttribute("exposed_name", name)
            exp_conn_tag.setAttribute("conn_name", conn.name)
            exp_conn_tag.setAttribute("owner_guid", xmlencode(conn.owner.guid))
            exp_conns_tag.appendChild(exp_conn_tag)
        if exp_conns_tag.hasChildNodes():
            tag.appendChild(exp_conns_tag)

    def from_xml(self, provider, xml):
        doc = minidom.parseString(xml)
        scenario_tag = doc.getElementsByTagName("scenario")
        if scenario_tag:
            box_tags = scenario_tag[0].childNodes
        else:
            box_tags = doc.childNodes

        box = None
        connections = []
        for b_tag in box_tags:
            if b_tag.nodeType == doc.ELEMENT_NODE and \
                    xmldecode(b_tag.nodeName) == 'box':
                box = self.box_from_xml(provider, b_tag, connections)
                break
        self.connect_boxes(box, connections)
        return box

    def box_from_xml(self, provider, b_tag, connections):
        guid = xmldecode(b_tag.getAttribute("guid"))
        if guid: guid = int(guid)
        box_id = xmldecode(b_tag.getAttribute("box_id"))
        box = provider.create(box_id, guid = guid)
        self.graphical_info_from_xml(box, b_tag)
        self.attributes_from_xml(box, b_tag)
        self.connections_from_xml(box, b_tag, connections)

        for tag in b_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'box':
                child_box = self.box_from_xml(provider, tag, connections)
                box.add(child_box)

        if tags.CONTAINER in box.tags:
            self.exposed_attributes_from_xml(box, b_tag)
            self.exposed_connectors_from_xml(box, b_tag)
        return box

    def attributes_from_xml(self, box, b_tag):
        attributes_tag = self._find_subtag(b_tag, 'attributes')
        if not attributes_tag: 
            return 

        for tag in attributes_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'attribute':
                name = xmldecode(tag.getAttribute("name"))
                value = xmldecode(tag.getAttribute("value"))
                type = xmldecode(tag.getAttribute("type"))
                value = from_attribute_type(type, value)
                attr = getattr(box.a, name)
                attr.value = value

    def graphical_info_from_xml(self, box, b_tag):
        for tag in b_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'graphical_info':
                x = float(tag.getAttribute("x"))
                y = float(tag.getAttribute("y"))
                width = float(tag.getAttribute("width"))
                height = float(tag.getAttribute("height"))
                box.graphical_info.x = x
                box.graphical_info.y = y
                box.graphical_info.width = width
                box.graphical_info.width = width
                break

    def connections_from_xml(self, box, b_tag, connections):
        connections_tag = self._find_subtag(b_tag, 'connections')
        if not connections_tag: 
            return 
        
        for tag in connections_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'connection':
                 connector = xmldecode(tag.getAttribute("connector"))
                 other_connector = xmldecode(tag.getAttribute("other_connector"))
                 other_guid = int(tag.getAttribute("other_guid"))
                 connections.append((box.guid, connector, other_guid, other_connector))

    def exposed_attributes_from_xml(self, box, b_tag):
        exposed_attributes_tag = self._find_subtag(b_tag, 'exposed_attributes')
        if not exposed_attributes_tag: 
            return 
        
        for tag in exposed_attributes_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'exposed_attribute':
                 exposed_name = xmldecode(tag.getAttribute('exposed_name'))
                 attr_name = xmldecode(tag.getAttribute('attr_name'))
                 owner_guid = int(tag.getAttribute('owner_guid'))
                 b = box.box(owner_guid)
                 attribute = getattr(b.a, attr_name)
                 box.expose_attribute(exposed_name, attribute)

    def exposed_connectors_from_xml(self, box, b_tag):
        exposed_connections_tag = self._find_subtag(b_tag, 'exposed_connectors')
        if not exposed_connections_tag: 
            return 
        
        for tag in exposed_connections_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'exposed_connector':
                 exposed_name = xmldecode(tag.getAttribute('exposed_name'))
                 conn_name = xmldecode(tag.getAttribute('conn_name'))
                 owner_guid = int(tag.getAttribute('owner_guid'))
                 b = box.box(owner_guid)
                 connector = getattr(b.c, conn_name)
                 box.expose_connector(exposed_name, connector)

    def _find_subtag(self, b_tag, tag_name):
        the_tag = None
        for tag in b_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == tag_name:
                the_tag = tag
                break
        return the_tag

    def connect_boxes(self, box, connections):
        dejafait = set()
        for conn in connections:
            (guid, connector, other_guid, other_connector) = conn
            if not (guid, connector) in dejafait:
                b = box.box(guid)
                other_b = box.box(other_guid)
                conn = getattr(b.c, connector)
                other_conn = getattr(other_b.c, other_connector)
                conn.connect(other_conn)
                dejafait.add((other_guid, other_connector))
    
