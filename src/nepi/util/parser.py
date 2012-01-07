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
        self.graphical_info_to_xml(box, p_tag, doc)
        self.attributes_to_xml(box, p_tag, doc)

        for b in box.boxes:
            self.box_to_xml(b, b_tag, doc)
        
        p_tag.appendChild(b_tag)

    def attributes_to_xml(self, box, tag, doc):
        attrs_tag = doc.createElement("attributes")
        for name in box.attributes:
            attr = getattr(box.a, name)
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



