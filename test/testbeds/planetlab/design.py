#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
import unittest

class PlanetlabDesignTestCase(unittest.TestCase):
    def make_test_design(self):
        exp_desc = ExperimentDescription()
        testbed_id = "planetlab"
        provider = FactoriesProvider(testbed_id)
        tstbd_desc = exp_desc.add_testbed_description(provider)
        tstbd_desc.set_attribute_value("slice", "inria_nepi")
        node1 = tstbd_desc.create("Node")
        node2 = tstbd_desc.create("Node")
        iface1 = tstbd_desc.create("NodeInterface")
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = tstbd_desc.create("NodeInterface")
        node2.connector("devs").connect(iface2.connector("node"))
        switch = tstbd_desc.create("Internet")
        iface1.connector("inet").connect(switch.connector("devs"))
        iface2.connector("inet").connect(switch.connector("devs"))
        app = tstbd_desc.create("Application")
        app.set_attribute_value("command", "ping -qc10 10.0.0.2")
        app.connector("node").connect(node1.connector("apps"))
        
        return exp_desc, tstbd_desc, node1, node2, iface1, iface2, app
        
    def test_design_simple(self):
        exp_desc, tstbd_desc, node1, node2, iface1, iface2, app = self.make_test_design()

        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)

    def test_design_constrained(self):
        exp_desc, tstbd_desc, node1, node2, iface1, iface2, app = self.make_test_design()
        
        node1.set_attribute_value("hostname", "onelab*.inria.fr")
        node2.set_attribute_value("hostname", "onelab*.inria.fr")

        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)

    def test_design_constrained2(self):
        exp_desc, tstbd_desc, node1, node2, iface1, iface2, app = self.make_test_design()
        
        node1.set_attribute_value("minReliability", 90.0)
        node1.set_attribute_value("operatingSystem", "f12")
        node2.set_attribute_value("minReliability", 50.0)
        node2.set_attribute_value("architecture", "x86_64")

        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)
        
    def test_design_emulation(self):
        exp_desc, tstbd_desc, node1, node2, iface1, iface2, app = self.make_test_design()
        
        node1.set_attribute_value("emulation",True)
        
        netpipe1 = tstbd_desc.create("NetPipe")
        netpipe1.set_attribute_value("mode","CLIENT")
        netpipe1.set_attribute_value("portList","80,443")
        netpipe1.set_attribute_value("bwIn",1.0)
        netpipe1.set_attribute_value("bwOut",128.0/1024.0)
        netpipe1.set_attribute_value("delayIn",12)
        netpipe1.set_attribute_value("delayOut",92)
        netpipe1.set_attribute_value("plrIn",0.05)
        netpipe1.set_attribute_value("plrOut",0.15)
        node1.connector("pipes").connect(netpipe1.connector("node"))

        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)

if __name__ == '__main__':
    unittest.main()
