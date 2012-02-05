#!/usr/bin/env python

from nepi.design import create_provider
# mock testbed
import mock
import unittest

class DesignIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_serialization(self):
        provider = create_provider(mods=[mock])

        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance")
        exp.add(mocki)

        node1 = provider.create("mock::Node", boolAttr = False)
        mocki.add(node1)
        node1.a.boolAttr.value = True

        iface1 = provider.create("mock::Interface")
        mocki.add(iface1)
        node1.c.devs.connect(iface1.c.node)

        addr1 = provider.create("mock::IPv4Address")
        mocki.add(addr1)
        addr1.a.Address.value = "192.168.0.1"
        iface1.c.addrs.connect(addr1.c.iface)

        node2 = provider.create("mock::Node")
        mocki.add(node2)

        iface2 = provider.create("mock::Interface")
        mocki.add(iface2)
        node2.c.devs.connect(iface2.c.node)

        addr2 = provider.create("mock::IPv4Address")
        mocki.add(addr2)
        addr2.a.Address.value = "192.168.0.2"
        iface2.c.addrs.connect(addr2.c.iface)

        trace = provider.create("mock::Trace")
        mocki.add(trace)
        trace.a.stringAttr.value = "string"
        node1.c.traces.connect(trace.c.node)

        iface1.c.peer.connect(iface2.c.peer)

        app = provider.create("mock::Application")
        mocki.add(app)
        app.a.start.value = "10s"
        app.c.node.connect(node1.c.apps)

        xml = exp.xml
        provider2 = create_provider(mods=[mock])
        exp2 = provider2.from_xml(xml)
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)

        #TODO: Serialize connections!!


if __name__ == '__main__':
    unittest.main()

