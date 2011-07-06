#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
import os
import shutil
import test_util
import unittest
import uuid

class NetnsDesignTestCase(unittest.TestCase):
    def test_design_if(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "netns"
        provider = FactoriesProvider(testbed_id, testbed_version)
        tstbd_desc = exp_desc.add_testbed_description(provider)
        tstbd_desc.set_attribute_value("enableDebug", True)
        node1 = tstbd_desc.create("Node")
        node2 = tstbd_desc.create("Node")
        iface1 = tstbd_desc.create("NodeInterface")
        iface1.set_attribute_value("up", True)
        node1.connector("devs").connect(iface1.connector("node"))
        ip1 = iface1.add_address()
        ip1.set_attribute_value("Address", "10.0.0.1")
        iface2 = tstbd_desc.create("NodeInterface")
        iface2.set_attribute_value("up", True)
        node2.connector("devs").connect(iface2.connector("node"))
        ip2 = iface2.add_address()
        ip2.set_attribute_value("Address", "10.0.0.2")
        switch = tstbd_desc.create("Switch")
        switch.set_attribute_value("up", True)
        iface1.connector("switch").connect(switch.connector("devs"))
        iface2.connector("switch").connect(switch.connector("devs"))
        app = tstbd_desc.create("Application")
        app.set_attribute_value("command", "ping -qc10 10.0.0.2")
        app.connector("node").connect(node1.connector("apps"))
        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)
        
if __name__ == '__main__':
    unittest.main()
