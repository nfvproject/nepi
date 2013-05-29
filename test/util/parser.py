#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>


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

