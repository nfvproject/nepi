# -*- coding: utf-8 -*-

from nepi.design import attributes
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
        self.box_to_xml(box, root_tag, doc)
        doc.appendChild(root_tag)
        
        try:
            xml = doc.toprettyxml(indent="    ", encoding="UTF-8")
        except:
            print >>sys.stderr, "Oops: generating XML from %s" % (data,)
            raise
        
        return xml

    def box_to_xml(self, box, p_tag, doc):
        b_tag = doc.createElement("box")
        b_tag.setAttribute("guid", xmlencode(box.guid))
        b_tag.setAttribute("testbed_id", xmlencode(box.testbed_id))
        b_tag.setAttribute("box_id", xmlencode(box.box_id))
        self.graphical_info_to_xml(box, b_tag, doc)
        self.attributes_to_xml(box, b_tag, doc)

        for b in box.boxes:
            self.box_to_xml(b, b_tag, doc)
        
        p_tag.appendChild(b_tag)

    def attributes_to_xml(self, box, tag, doc):
        attrs_tag = doc.createElement("attributes")
        for name in box.attributes:
            attr = getattr(box.a, name)
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

    def from_xml(self, provider, xml):
        doc = minidom.parseString(xml)
        scenario_tag = doc.getElementsByTagName("scenario")
        if scenario_tag:
            box_tags = scenario_tag[0].childNodes
        else:
            box_tags = doc.childNodes

        box = None
        for b_tag in box_tags:
            if b_tag.nodeType == doc.ELEMENT_NODE and \
                    xmldecode(b_tag.nodeName) == 'box':
                box = self.box_from_xml(provider, b_tag)
                break
        return box

    def box_from_xml(self, provider, b_tag):
        guid = xmldecode(b_tag.getAttribute("guid"))
        if guid: guid = int(guid)
        box_id = xmldecode(b_tag.getAttribute("box_id"))
        box = provider.create(box_id, guid = guid)
        self.graphical_info_from_xml(box, b_tag)
        self.attributes_from_xml(box, b_tag)
      
        for tag in b_tag.childNodes:
            if tag.nodeType == tag.ELEMENT_NODE and \
                    xmldecode(tag.nodeName) == 'box':
                child_box = self.box_from_xml(provider, tag)
                box.add(child_box)
        return box

    def attributes_from_xml(self, box, b_tag):
        attributes_tags = b_tag.getElementsByTagName("attributes")
        if len(attributes_tags) == 0:
            return

        attribute_tags = attributes_tags[0].getElementsByTagName("attribute")
        for attribute_tag in attribute_tags:
             if attribute_tag.nodeType == b_tag.ELEMENT_NODE:
                name = xmldecode(attribute_tag.getAttribute("name"))
                value = xmldecode(attribute_tag.getAttribute("value"))
                type = xmldecode(attribute_tag.getAttribute("type"))
                value = from_attribute_type(type, value)
                attr = getattr(box.a, name)
                attr.value = value

    def graphical_info_from_xml(self, box, b_tag):
        graphical_info_tag = b_tag.getElementsByTagName("graphical_info")
        if len(graphical_info_tag) == 0:
            return

        graphical_info_tag = graphical_info_tag[0]
        if graphical_info_tag.nodeType == b_tag.ELEMENT_NODE:
            x = float(graphical_info_tag.getAttribute("x"))
            y = float(graphical_info_tag.getAttribute("y"))
            width = float(graphical_info_tag.getAttribute("width"))
            height = float(graphical_info_tag.getAttribute("height"))
            box.graphical_info.x = x
            box.graphical_info.y = y
            box.graphical_info.width = width
            box.graphical_info.width = width


