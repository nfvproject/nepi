#!/usr/bin/env python

from nepi.design import create_provider
from nepi.execute import create_ec
# mock testbed
import mock
import time
import unittest

class ExecuteControllersTestCase(unittest.TestCase):
    def test_experiment_controller_create(self):
        provider = create_provider(mods=[mock])
        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance", container = exp)
        
        node1 = provider.create("mock::Node", container = mocki, boolAttr = True)
        iface1 = provider.create("mock::Interface", container = mocki)
        addr1 = iface1.add_address(address = "192.168.0.1")
        node1.c.devs.connect(iface1.c.node)

        node2 = provider.create("mock::Node", container = mocki, boolAttr = True)
        iface2 = provider.create("mock::Interface", container = mocki)
        addr2 = iface2.add_address(address = "192.168.0.2")
        node2.c.devs.connect(iface2.c.node)

        iface1.c.peer.connect(iface2.c.peer)

        trace = provider.create("mock::Trace", container = mocki, stringAttr = "lala")
        node1.c.traces.connect(trace.c.node)

        app = provider.create("mock::Application", container = mocki, start = "10s")
        app.c.node.connect(node1.c.apps)

        xml = exp.xml

        ec = create_ec(xml)
        ec.run(mods=[mock])
        time.sleep(2)
        ec.shutdown()
        

if __name__ == '__main__':
    unittest.main()

