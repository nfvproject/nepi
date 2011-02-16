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

from nepi.util.parser.base import ExperimentParser
p = ExperimentParser()
data = p.to_data(exp_desc)
print data.data
exp_desc2 = ExperimentDescription()
p.from_data(exp_desc2, data)
data2 = p.to_data(exp_desc2)
print data2.data
print data.data == data2.data

from nepi.util.parser._xml import XmlExperimentParser
p = XmlExperimentParser()
xml = p.to_xml(exp_desc)
print xml
exp_desc2 = ExperimentDescription()
p.from_xml(exp_desc2, xml)
xml2 = p.to_xml(exp_desc2)
print xml2
print xml == xml2

#print experiment.xml_description


