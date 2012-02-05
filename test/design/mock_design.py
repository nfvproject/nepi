# -*- coding: utf-8 -*-

"""Experiment design test"""

from nepi.design import create_provider
# mock testbed
import mock

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

#self.assertRaises(RuntimeError, iface1.add_address)
# self.assertEquals(node1.tags, [tags.MOBILE, tags.NODE, tags.ALLOW_ROUTES])

xml = exp.xml
print xml

#exp_desc2 = ExperimentDescription()
#exp_desc2.from_xml(xml)
#xml2 = exp_desc2.to_xml()
#self.assertTrue(xml == xml2)

