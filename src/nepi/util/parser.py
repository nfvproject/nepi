"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from nepi.design.box import Box

from xml.dom import minidom
import sys

STRING = "string"
BOOL = "bool"
INTEGER = "integer"
DOUBLE = "float"

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

def from_type(value):
    if isinstance(value, str):
        return STRING
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, int):
        return INTEGER
    if isinstance(value, float):
        return DOUBLE

def to_type(type, value):
    if type == STRING:
        return str(value)
    if type == BOOL:
        return value == "True"
    if type == INTEGER:
        return int(value)
    if type == DOUBLE:
        return float(value)

class XMLParser(object):
    def to_xml(self, box):
        doc = minidom.Document()

        root = doc.createElement("boxes")
        doc.appendChild(root)

        traversed = dict()
        self._traverse_boxes(doc, traversed, box)

        # Keep the order
        for guid in sorted(traversed.keys()):
            bnode = traversed[guid]
            root.appendChild(bnode)
       
        try:
            xml = doc.toprettyxml(indent="    ", encoding="UTF-8")
        except:
            print >>sys.stderr, "Oops: generating XML from %s" % (data,)
            raise
        
        return xml

    def _traverse_boxes(self, doc, traversed, box):
        bnode = doc.createElement("box")
        bnode.setAttribute("guid", xmlencode(box.guid))
        bnode.setAttribute("label", xmlencode(box.label))
        bnode.setAttribute("x", xmlencode(box.x))
        bnode.setAttribute("y", xmlencode(box.y))
        bnode.setAttribute("width", xmlencode(box.width))
        bnode.setAttribute("height", xmlencode(box.height))

        traversed[box.guid] = bnode

        anode = doc.createElement("attributes")
        bnode.appendChild(anode)
        for name in sorted(box.attributes):
            value = getattr(box.a, name)
            aanode = doc.createElement("attribute")
            anode.appendChild(aanode)
            aanode.setAttribute("name", xmlencode(name))
            aanode.setAttribute("value", xmlencode(value))
            aanode.setAttribute("type", from_type(value))

        tnode = doc.createElement("tags")
        bnode.appendChild(tnode)
        for tag in sorted(box.tags):
            ttnode = doc.createElement("tag")
            tnode.appendChild(ttnode)
            ttnode.setAttribute("name", xmlencode(tag))

        cnode = doc.createElement("connections")
        bnode.appendChild(cnode)
        for b in sorted(box.connections):
            ccnode = doc.createElement("connection")
            cnode.appendChild(ccnode)
            ccnode.setAttribute("guid", xmlencode(b.guid))
            if b.guid not in traversed:
                self._traverse_boxes(doc, traversed, b)

    def from_xml(self, xml):
        doc = minidom.parseString(xml)
        bnode_list = doc.getElementsByTagName("box")

        boxes = dict()
        connections = dict()

        for bnode in bnode_list:
            if bnode.nodeType == doc.ELEMENT_NODE:
                guid = int(bnode.getAttribute("guid"))
                label = xmldecode(bnode.getAttribute("label"))
                x = float(bnode.getAttribute("x"))
                y = float(bnode.getAttribute("y"))
                height = float(bnode.getAttribute("height"))
                width = float(bnode.getAttribute("width"))
                box = Box(label=label, guid=guid)
                boxes[guid] = box

                anode_list = bnode.getElementsByTagName("attribute") 
                for anode in anode_list:
                    name = xmldecode(anode.getAttribute("name"))
                    value = xmldecode(anode.getAttribute("value"))
                    type = xmldecode(anode.getAttribute("type"))
                    value = to_type(type, value)
                    setattr(box.a, name, value)
                    
                tnode_list = bnode.getElementsByTagName("tag") 
                for tnode in tnode_list:
                    value = xmldecode(tnode.getAttribute("name"))
                    box.tadd(value)

                connections[box] = set()
                cnode_list = bnode.getElementsByTagName("connection")
                for cnode in cnode_list:
                    guid = int(cnode.getAttribute("guid"))
                    connections[box].add(guid)

        for box, conns in connections.iteritems():
            for guid in conns:
                b = boxes[guid]
                box.connect(b)

        return box


