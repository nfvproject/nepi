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

import unittest

class BoxDesignTestCase(unittest.TestCase):
    def test_simple_design(self):
        node1 = Box()
        node2 = Box()

        node1.label = "uno"
        node2.label = "dos"

        node1.tadd('nodo')
        node2.tadd('mynodo')

        self.assertEquals(node1.tags, set(['nodo']))
        self.assertEquals(node2.tags, set(['mynodo']))
       
        node1.a.hola = "chau"
        node2.a.hello = "bye"

        self.assertEquals(node1.a.hola, "chau")
        self.assertEquals(node2.a.hello, "bye")

        node1.connect(node2)
        
        self.assertEquals(node1.connections, set([node2]))
        self.assertEquals(node2.connections, set([node1]))
        self.assertTrue(node1.is_connected(node2))
        self.assertTrue(node2.is_connected(node1))

        self.assertEquals(node1.c.dos.a.hello, "bye")
        self.assertEquals(node2.c.uno.a.hola, "chau")
       
        node2.disconnect(node1)

        self.assertEquals(node1.connections, set([]))
        self.assertEquals(node2.connections, set([]))
        self.assertFalse(node1.is_connected(node2))
        self.assertFalse(node2.is_connected(node1))

        self.assertRaises(AttributeError, node1.c.dos)
        self.assertRaises(AttributeError, node2.c.uno)


if __name__ == '__main__':
    unittest.main()

