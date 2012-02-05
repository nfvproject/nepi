#!/usr/bin/env python

from nepi.design import create_provider
# mock testbed
import mock
import unittest

class DesignBoxesTestCase(unittest.TestCase):

    def test_clone_box(self):
        provider = create_provider(mods=[mock])

        exp1 = provider.create("Experiment")
        exp2 = provider.create("Experiment")

        self.assertTrue(id(exp1) != id(exp2))
        self.assertTrue(id(exp1._boxes) != id(exp2._boxes))
        self.assertTrue(id(exp1._attributes) != id(exp2._attributes))
        self.assertTrue(id(exp1.a.label) != id(exp2.a.label))
        self.assertTrue(id(exp1._connectors) != id(exp2._connectors))
        self.assertTrue(id(exp1._connections) != id(exp2._connections))
        exp1.a.label.value = 'label'
        self.assertTrue(exp1.a.label.value != exp2.a.label.value)

        node1 = provider.create("mock::Node")
        node2 = node1.clone()
        self.assertTrue(id(node1) != id(node2))
        self.assertTrue(id(node1._boxes) != id(node2._boxes))
        self.assertTrue(id(node1._attributes) != id(node2._attributes))
        self.assertTrue(id(node1.a.label) != id(node2.a.label))
        self.assertTrue(id(node1._connectors) != id(node2._connectors))
        self.assertTrue(id(node1._connections) != id(node2._connections))
        node1.a.boolAttr.value = True
        self.assertTrue(node1.a.boolAttr.value != node2.a.boolAttr.value)
        for cname in node1.connectors:
            conn1 = getattr(node1.c, cname)
            conn2 = getattr(node2.c, cname)
            self.assertTrue(id(conn1) !=  id(conn2))
            self.assertTrue(conn1.owner != conn2.owner)


if __name__ == '__main__':
    unittest.main()

