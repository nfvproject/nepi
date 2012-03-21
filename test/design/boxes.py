#!/usr/bin/env python

from nepi.design import create_provider
import shutil
import tempfile
import unittest

class DesignBoxesTestCase(unittest.TestCase):
    def test_clone_box(self):
        provider = create_provider(modnames = ["mock"])

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
        node2 = provider.clone(node1)
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
        provider = create_provider(modnames = ["mock"])
        
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
        cont2 = provider.clone(cont1)
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
        provider = create_provider(modnames = ["mock"])

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
        
        provider2 = create_provider(modnames = ["mock"])
        exp2 = provider2.from_xml(xml)
        node21 = exp2.box(node1.guid)
        self.assertTrue(node21.a.boolAttr.value == True)
        
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)

    def test_container_serialization(self):
        provider = create_provider(modnames = ["mock"])

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
        addr1.a.address.value = "192.168.1.1"
        iface1.c.addrs.connect(addr1.c.iface)
        addr2 = provider.create("mock::IPv4Address", container = cont1)
        addr2.a.address.value = "192.168.2.1"
        iface2.c.addrs.connect(addr2.c.iface)
        addr3 = provider.create("mock::IPv4Address", container = cont1)
        addr3.a.address.value = "192.168.3.1"
        iface3.c.addrs.connect(addr3.c.iface)
        addr4 = provider.create("mock::IPv4Address", container = cont1)
        addr4.a.address.value = "192.168.4.1"
        iface4.c.addrs.connect(addr4.c.iface)

        cont1.expose_connector("eth0", iface1.c.peer)
        cont1.expose_connector("eth1", iface2.c.peer)
        cont1.expose_connector("eth2", iface3.c.peer)
        cont1.expose_connector("eth3", iface4.c.peer)

        cont1.expose_attribute("eth0_address", addr1.a.address)
        cont1.expose_attribute("eth1_address", addr2.a.address)
        cont1.expose_attribute("eth2_address", addr3.a.address)
        cont1.expose_attribute("eth3_address", addr4.a.address)

        iface5 = provider.create("mock::Interface", container = mocki)
        cont1.c.eth0.connect(iface5.c.peer)
        self.assertTrue(cont1.c.eth0.is_connected(iface5.c.peer))
        self.assertTrue(iface1.c.peer.is_connected(iface5.c.peer))

        search_path = tempfile.mkdtemp()
        ret = provider.store_user_container(cont1, search_path = search_path)
        self.assertFalse(ret)

        cont1.a.boxId.value = "mock::Switch"
        ret = provider.store_user_container(cont1, search_path = search_path)
        self.assertTrue(ret)

        provider2 = create_provider(modnames=["mock"], search_path = search_path)
        mocki = provider2.create("mock::MockInstance")
        switch1 = provider2.create("mock::Switch", container = mocki)

        switch1.a.eth0_address.value = "192.168.5.1"
        self.assertTrue(switch1.a.eth0_address.value != cont1.a.eth0_address.value)
        self.assertFalse(switch1.c.eth0.is_connected(iface5.c.peer))

        shutil.rmtree(search_path)

    def test_routes_and_addresses(self):
        provider = create_provider(modnames = ["mock"])

        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance")
        exp.add(mocki)

        node1 = provider.create("mock::Node", boolAttr = False)
        mocki.add(node1)
        node1.a.boolAttr.value = True

        route1 = node1.add_route(destination = "0.0.0.0", nexthop = "192.168.0.1")

        iface1 = provider.create("mock::Interface")
        mocki.add(iface1)
        node1.c.devs.connect(iface1.c.node)

        addr1 = iface1.add_address(address = "192.168.0.1")

        node2 = provider.create("mock::Node")
        mocki.add(node2)

        iface2 = provider.create("mock::Interface")
        mocki.add(iface2)
        node2.c.devs.connect(iface2.c.node)

        addr2 = iface2.add_address(address = "192.168.0.2")

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

        provider2 = create_provider(modnames=["mock"])
        exp2 = provider2.from_xml(xml)
        node21 = exp2.box(node1.guid)
        self.assertTrue(node21.a.boolAttr.value == True)
        
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)

    def test_events(self):
        provider = create_provider(modnames = ["mock"])

        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance", container = exp)
        node1 = provider.create("mock::Node", container = mocki)
        iface1 = provider.create("mock::Interface", container = mocki)
        node1.c.devs.connect(iface1.c.node)
        app1 = provider.create("mock::Application", container = mocki)
        app1.c.node.connect(node1.c.apps)

        node2 = provider.create("mock::Node", container = mocki)
        iface2 = provider.create("mock::Interface", container = mocki)
        node2.c.devs.connect(iface2.c.node)
        app2 = provider.create("mock::Application", container = mocki)
        app2.c.node.connect(node2.c.apps)

        app1.e.start.at("2s")
        app2.e.start.after(app1.guid)

        xml = exp.xml

        # verify that the events where correctly reconstructed
        provider2 = create_provider(modnames=["mock"])
        exp2 = provider2.from_xml(xml)
        
        xml2 = exp2.xml
        self.assertTrue(xml == xml2)

if __name__ == '__main__':
    unittest.main()

