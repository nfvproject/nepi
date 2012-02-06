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

        mocki = provider.create("mock::MockInstance")
        exp1.add(mocki)
        node1 = provider.create("mock::Node")
        mocki.add(node1)
        iface1 = provider.create("mock::Interface")
        mocki.add(iface1)
        node1.c.devs.connect(iface1.c.node)
        node2 = node1.clone()
        mocki.add(node2)

        self.assertTrue(id(node1) != id(node2))
        self.assertTrue(id(node1._boxes) != id(node2._boxes))
        self.assertTrue(id(node1._attributes) != id(node2._attributes))
        self.assertTrue(id(node1.a.label) != id(node2.a.label))
        self.assertTrue(id(node1._connectors) != id(node2._connectors))
        self.assertTrue(id(node1._connections) != id(node2._connections))
        self.assertTrue(len(node1.connections) == 1)
        self.assertTrue(len(node2.connections) == 0)
        node1.a.boolAttr.value = True
        self.assertTrue(node1.a.boolAttr.value != node2.a.boolAttr.value)
        for cname in node1.connectors:
            conn1 = getattr(node1.c, cname)
            conn2 = getattr(node2.c, cname)
            self.assertTrue(id(conn1) !=  id(conn2))
            self.assertTrue(conn1.owner != conn2.owner)
    
    
    def test_clone_container(self):
        provider = create_provider(mods=[mock])
        
        mocki = provider.create("mock::MockInstance")
        cont1 = provider.create("mock::Container")
        mocki.add(cont1)
        node1 = provider.create("mock::Node", boolAttr = False)
        node1.a.label.value = "node"
        cont1.add(node1)
        iface1 = provider.create("mock::Interface")
        iface1.a.label.value = "iface"
        cont1.add(iface1)
        node1.c.devs.connect(iface1.c.node)

        app1 = provider.create("mock::Application")
        app1.a.label.value = "app"
        mocki.add(app1)

        # Exposing attributes
        cont1.expose_attribute("myattr", node1.a.boolAttr)

        self.assertTrue(id(node1.a.boolAttr) == id(cont1.a.myattr))
        self.assertTrue(node1.a.boolAttr.value == False)
        cont1.a.myattr.value = True
        self.assertTrue(node1.a.boolAttr.value == True)

        # Exposing connectors
        cont1.expose_connector("myconn", node1.c.apps)
        
        self.assertTrue(id(node1.c.apps) == id(cont1.c.myconn))
        cont1.c.myconn.connect(app1.c.node)
        self.assertTrue(cont1.c.myconn.is_connected(app1.c.node))
        self.assertTrue(node1.c.apps.is_connected(app1.c.node))
        cont1.c.myconn.disconnect(app1.c.node)
        self.assertFalse(cont1.c.myconn.is_connected(app1.c.node))
        self.assertFalse(node1.c.apps.is_connected(app1.c.node))

        node1.c.apps.connect(app1.c.node)
        self.assertTrue(cont1.c.myconn.is_connected(app1.c.node))
        self.assertTrue(node1.c.apps.is_connected(app1.c.node))
        node1.c.apps.disconnect(app1.c.node)
        self.assertFalse(cont1.c.myconn.is_connected(app1.c.node))
        self.assertFalse(node1.c.apps.is_connected(app1.c.node))

        # clone container
        cont2 = cont1.clone()
        mocki.add(cont2)

        node2 = cont2.box("node")
        iface2 = cont2.box("iface")
        self.assertTrue(id(node1) != id(node2))
        self.assertTrue(id(iface1) != id(iface2))

        self.assertTrue(id(cont1.a.myattr) != id(cont2.a.myattr))
        self.assertTrue(id(node2.a.boolAttr) == id(cont2.a.myattr))
        self.assertTrue(node2.a.boolAttr.value == True)
        cont2.a.myattr.value = False
        self.assertTrue(node2.a.boolAttr.value == False)
        self.assertTrue(node1.a.boolAttr.value == True)

        self.assertTrue(node2.c.devs.is_connected(iface2.c.node))
        self.assertFalse(node2.c.devs.is_connected(iface1.c.node))

        self.assertTrue(id(node2.c.apps) == id(cont2.c.myconn))
        cont2.c.myconn.connect(app1.c.node)
        self.assertTrue(cont2.c.myconn.is_connected(app1.c.node))
        self.assertTrue(node2.c.apps.is_connected(app1.c.node))
        cont2.c.myconn.disconnect(app1.c.node)
        self.assertFalse(cont2.c.myconn.is_connected(app1.c.node))
        self.assertFalse(node2.c.apps.is_connected(app1.c.node))


    def test_experiment_serialization(self):
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
        addr1.a.address.value = "192.168.0.1"
        iface1.c.addrs.connect(addr1.c.iface)

        node2 = provider.create("mock::Node")
        mocki.add(node2)

        iface2 = provider.create("mock::Interface")
        mocki.add(iface2)
        node2.c.devs.connect(iface2.c.node)

        addr2 = provider.create("mock::IPv4Address")
        mocki.add(addr2)
        addr2.a.address.value = "192.168.0.2"
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
        node21 = exp2.box(node1.guid)
        self.assertTrue(node21.a.boolAttr.value == True)
        
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)


    def test_container_serialization(self):
        provider = create_provider(mods=[mock])

        mocki = provider.create("mock::MockInstance")
        cont1 = provider.create("mock::Container", container = mocki)

        node1 = provider.create("mock::Node", container = cont1)
        iface1 = provider.create("mock::Interface", container = cont1)
        iface2 = provider.create("mock::Interface", container = cont1)
        iface3 = provider.create("mock::Interface", container = cont1)
        iface4 = provider.create("mock::Interface", container = cont1)
        node1.c.devs.connect(iface1.c.node)
        node1.c.devs.connect(iface2.c.node)
        node1.c.devs.connect(iface3.c.node)
        node1.c.devs.connect(iface4.c.node)

        addr1 = provider.create("mock::IPv4Address", container = cont1)
        addr1.a.address.value = "192.168.0.1"
        iface1.c.addrs.connect(addr1.c.iface)
        addr2 = provider.create("mock::IPv4Address", container = cont1)
        addr2.a.address.value = "192.168.0.2"
        iface2.c.addrs.connect(addr2.c.iface)
        addr3 = provider.create("mock::IPv4Address", container = cont1)
        addr3.a.address.value = "192.168.0.3"
        iface3.c.addrs.connect(addr3.c.iface)
        addr4 = provider.create("mock::IPv4Address", container = cont1)
        addr4.a.address.value = "192.168.1.1"
        iface4.c.addrs.connect(addr4.c.iface)

        cont1.expose_connector("eth0", iface1.c.node)
        cont1.expose_connector("eth1", iface2.c.node)
        cont1.expose_connector("eth2", iface3.c.node)
        cont1.expose_connector("eth3", iface4.c.node)

        cont1.expose_attribute("out_address", addr4.a.address)

        search_path = "/tmp"
        ret = provider.store_user_container(cont1, search_path = search_path)
        self.assertFalse(ret)

        cont1.a.boxId.value = "mock::Switch"
        ret = provider.store_user_container(cont1, search_path = search_path)
        self.assertTrue(ret)

        provider2 = create_provider(mods=[mock], search_path = search_path)
        mocki = provider2.create("mock::MockInstance")
        switch1 = provider2.create("mock::Switch", container = mocki)


if __name__ == '__main__':
    unittest.main()

