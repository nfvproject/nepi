#!/usr/bin/env python

from nepi.design.box import Box 
from nepi.util.parser import XMLParser

import unittest

class BoxDesignTestCase(unittest.TestCase):
    def test_to_xml(self):
        node1 = Box()
        node2 = Box()

        node1.label = "node1"
        node2.label = "node2"

        node1.connect(node2)

        node1.a.dog = "cat"
        node1.a.one = "two"
        node1.a.t = "q"

        node1.c.node2.a.sky = "sea"
        node2.a.bee = "honey"

        node1.tadd("unooo")
        node2.tadd("dosss")

        parser = XMLParser()
        xml = parser.to_xml(node1)
        
        node = parser.from_xml(xml)
        xml2 = parser.to_xml(node)
        
        self.assertEquals(xml, xml2)

if __name__ == '__main__':
    unittest.main()

