#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.description import ExperimentDescription
from nepi.testbeds import netns

exp_desc = ExperimentDescription()
testbed_version = "01"
netns_provider = netns.TestbedFactoriesProvider(testbed_version)
netns_desc = exp_desc.add_testbed_description(netns_provider)

node1 = netns_desc.create("Node")
node2 = netns_desc.create("Node")
iface1 = netns_desc.create("NodeInterface")
iface1.set_attribute_value("up", True)
node1.connector("devs").connect(iface1.connector("node"))
ip1 = iface1.add_address()
ip1.set_attribute_value("Address", "10.0.0.1")
iface2 = netns_desc.create("NodeInterface")
iface2.set_attribute_value("up", True)
node2.connector("devs").connect(iface2.connector("node"))
ip2 = iface2.add_address()
ip2.set_attribute_value("Address", "10.0.0.2")
switch = netns_desc.create("Switch")
switch.set_attribute_value("up", True)
iface1.connector("switch").connect(switch.connector("devs"))
iface2.connector("switch").connect(switch.connector("devs"))
app = netns_desc.create("Application")
app.set_attribute_value("command", "ping -qc10 10.0.0.2")
app.connector("node").connect(node1.connector("apps"))

xml = exp_desc.to_xml()
exp_desc2 = ExperimentDescription()
exp_desc2.from_xml(xml)
xml2 = exp_desc2.to_xml()
assert xml == xml2


