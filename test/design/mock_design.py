# -*- coding: utf-8 -*-

"""Experiment design test"""

from nepi.design import create_experiment, create_provider
# mock testbed
import mock

provider = create_provider()
provider.add_factories(mock)
exp = create_experiment()

mock_inst = provider.create(exp, "mock::MockInstance")

node1 = provider.create(exp, "mock::Node")
mock_inst.add_box(node1)
node1.set_attribute("boolAttr", True)

iface1 = provider.create(exp, "mock::Interface")
mock_inst.add_box(iface1)
node1.connect("devs", iface1, "node")

addr1 = provider.create(exp, "mock::IPv4Address")
mock_inst.add_box(addr1)
addr1.set_attribute("Address", "192.168.0.1")
iface1.connect("addrs", addr1, "iface")

node2 = provider.create(exp, "mock::Node")
mock_inst.add_box(node2)

iface2 = provider.create(exp, "mock::Interface")
mock_inst.add_box(iface2)
node2.connect("devs", iface2, "node")

addr2 = provider.create(exp, "mock::IPv4Address")
mock_inst.add_box(addr2)
addr2.set_attribute("Address", "192.168.0.2")
iface2.connect("addrs", addr2, "iface")

trace = provider.create(exp, "mock::Trace")
mock_inst.add_box(trace)
trace.set_attribute("stringAttr", "string")
node1.connect("traces", trace, "node")

iface1.connect("peer", iface2, "peer")

app = provider.create(exp, "mock::Application")
mock_inst.add_box(app)
app.set_attribute("start", "10s")
app.connect("node", node1, "apps")

#self.assertRaises(RuntimeError, iface1.add_address)
# self.assertEquals(node1.tags, [tags.MOBILE, tags.NODE, tags.ALLOW_ROUTES])

xml = exp.to_xml()

#exp_desc2 = ExperimentDescription()
#exp_desc2.from_xml(xml)
#xml2 = exp_desc2.to_xml()
#self.assertTrue(xml == xml2)

