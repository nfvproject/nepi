#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.util import tags
import mock.metadata
import sys
import unittest

class DesignTestCase(unittest.TestCase):
    def setUp(self):
        sys.modules["nepi.testbeds.mock.metadata"] = mock.metadata

    def test_design(self):
        exp_desc = ExperimentDescription()
        testbed_id = "mock"
        provider = FactoriesProvider(testbed_id)
        desc = exp_desc.add_testbed_description(provider)
        desc.set_attribute_value("fake", True)
        node1 = desc.create("Node")
        node2 = desc.create("Node")
        iface1 = desc.create("Interface")
        iface1.set_attribute_value("fake", True)
        addr1 = iface1.add_address()
        addr2 = iface1.add_address()
        addr3 = iface1.add_address()
        self.assertRaises(RuntimeError, iface1.add_address)
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = desc.create("Interface")
        iface2.set_attribute_value("fake", True)
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("iface").connect(iface2.connector("iface"))
        app = desc.create("Application")
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("fake")

        self.assertEquals(node1.tags, [tags.MOBILE, tags.NODE, tags.ALLOW_ROUTES])

        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)

if __name__ == '__main__':
    unittest.main()

