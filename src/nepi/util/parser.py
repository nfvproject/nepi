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

        for b in box.boxes:
            self.box_to_xml(b, b_tag, doc)
        
        p_tag.appendChild(b_tag)


