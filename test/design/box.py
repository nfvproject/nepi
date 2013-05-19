#!/usr/bin/env python

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

