#!/usr/bin/env python

from nepi.design import create_provider
import unittest

class NETNSDesignBoxesTestCase(unittest.TestCase):
    def test_design(self):
        provider = create_provider()
        exp = provider.create("Experiment")
        emu = provider.create("netns::Emulation", container = exp)
        emu.a.enableDebug.value = True
        
        node1 = provider.create("netns::Node", container = emu)
        node2 = provider.create("netns::Node", container = emu)

        iface1 = provider.create("netns::NodeInterface", container = emu)
        iface1.a.up.value = True
        iface2 = provider.create("netns::NodeInterface", container = emu)
        iface2.a.up.value = True

        node1.c.ifaces.connect(iface1.c.node)
        node2.c.ifaces.connect(iface2.c.node)

        ip1 = provider.create("netns::IPAddress", container = emu)
        ip1.a.address.value = "10.0.0.1"
        ip1.c.iface.connect(iface1.c.addrs)

        ip2 = provider.create("netns::IPAddress", container = emu)
        ip2.a.address.value = "10.0.0.2"
        ip2.c.iface.connect(iface2.c.addrs)

        switch = provider.create("netns::Switch", container = emu)
        switch.a.up.value = True
        iface1.c.switch.connect(switch.c.ifaces)
        iface2.c.switch.connect(switch.c.ifaces)
       
        app = provider.create("netns::Application", container = emu)
        app.a.command.value = "ping -qc10 10.0.0.2"
        app.c.node.connect(node1.c.apps)
        
        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        f = open('/tmp/xml1', 'w')
        f.write(xml)
        f.close()
        f = open('/tmp/xml2', 'w')
        f.write(xml2)
        f.close()
        self.assertTrue(xml == xml2)
        
if __name__ == '__main__':
    unittest.main()
