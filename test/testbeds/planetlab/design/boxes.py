#!/usr/bin/env python

from nepi.design import create_provider
import unittest

class PlanetLabDesignBoxesTestCase(unittest.TestCase):
    def test_design(self):
        provider = create_provider()
        exp = provider.create("Experiment")
        sl = provider.create("pl::Slice", container = exp)
        sl.a.slice.value = "inria_nepi"
       
        node1 = provider.create("pl::Node", container = sl)
        node2 = provider.create("pl::Node", container = sl)
        
        iface1 = provider.create("pl::NodeInterface", container = sl)
        node1.c.ifaces.connect(iface1.c.node)
        iface2 = provider.create("pl::NodeInterface", container = sl)
        node1.c.ifaces.connect(iface2.c.node)
        inet = provider.create("pl::Internet", container = sl)
        iface1.c.inet.connect(inet.c.ifaces)
        iface2.c.inet.connect(inet.c.ifaces)

        app = provider.create("pl::Application", container = sl)
        app.a.command.value = "ping -qc10 10.0.0.2"
        app.c.node.connect(node1.c.apps)
        
        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)
 
    def test_design_constrained(self):
        provider = create_provider()
        exp = provider.create("Experiment")
        sl = provider.create("pl::Slice", container = exp)
        sl.a.slice.value = "inria_nepi"
        
        node1 = provider.create("pl::Node", container = sl)
        node2 = provider.create("pl::Node", container = sl)
 
        node1.a.hostname.value = "onelab*.inria.fr"
        node2.a.hostname.value = "onelab*.inria.fr"

        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)
 
    def test_design_constrained2(self):
        provider = create_provider()
        
        exp = provider.create("Experiment")
        sl = provider.create("pl::Slice", container = exp)
        sl.a.slice.value = "inria_nepi"
        
        node1 = provider.create("pl::Node", container = sl)
        node2 = provider.create("pl::Node", container = sl)
        node1.a.minReliability.value = 90.0
        node1.a.operatingSystem.value = "f12"
        node2.a.minReliability.value = 50.0
        node2.a.architecture.value = "x86_64"

        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)

        
    def test_design_emulation(self):
        provider = create_provider()
        exp = provider.create("Experiment")
        sl = provider.create("pl::Slice", container = exp)
        sl.a.slice.value = "inria_nepi"
        
        node1 = provider.create("pl::Node", container = sl)
        netpipe1 = provider.create("pl::NetPipe", container = sl)
       
        netpipe1.a.mode.value = "CLIENT"
        netpipe1.a.portList.value = "80,443"
        netpipe1.a.bwIn.value = 1.0
        netpipe1.a.bwOut.value = 128.0/1024.0
        netpipe1.a.delayIn.value = 12
        netpipe1.a.delayOut.value = 92
        netpipe1.a.plrIn.value = 0.05 
        netpipe1.a.plrOut.value = 0.15
        node1.c.pipes.connect(netpipe1.c.node)

        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)

    def test_address_and_routes(self):
        provider = create_provider()
        exp = provider.create("Experiment")
        sl = provider.create("pl::Slice", container = exp)
        sl.a.slice.value = "inria_nepi"
       
        node1 = provider.create("pl::Node", container = sl)
        node2 = provider.create("pl::Node", container = sl)
        
        iface1 = provider.create("pl::TapInterface", container = sl)
        node1.c.ifaces.connect(iface1.c.node)
        iface2 = provider.create("pl::TapInterface", container = sl)
        node1.c.ifaces.connect(iface2.c.node)

        route1 = node1.add_route(destination = "0.0.0.0", nexthop = "192.168.0.1")
        route2 = node2.add_route(destination = "0.0.0.0", nexthop = "192.168.0.2")

        addr1 = iface1.add_address(address = "192.168.0.1")
        addr2 = iface2.add_address(address = "192.168.0.2")

        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)


if __name__ == '__main__':
    unittest.main()
