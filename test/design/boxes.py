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


if __name__ == '__main__':
    unittest.main()

