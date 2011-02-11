#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.experiment import ExperimentDescription

testbed_id = "netns"
testbed_version = "01"
experiment = ExperimentDescription()
netns = experiment.add_testbed_description(testbed_id, testbed_version)
node1 = netns.create("Node")
node2 = netns.create("Node")
iface1 = netns.create("NodeInterface")
iface1.set_attribute_value("up", True)
node1.connector("devs").connect(iface1.connector("node"))
ip1 = iface1.add_address()
ip1.set_attribute_value("Address", "10.0.0.1")
iface2 = netns.create("NodeInterface")
iface2.set_attribute_value("up", True)
node2.connector("devs").connect(iface2.connector("node"))
ip2 = iface2.add_address()
ip2.set_attribute_value("Address", "10.0.0.2")
switch = netns.create("Switch")
switch.set_attribute_value("up", True)
iface1.connector("switch").connect(switch.connector("devs"))
iface2.connector("switch").connect(switch.connector("devs"))
app = netns.create("Application")
app.set_attribute_value("command", "ping -qc10 10.0.0.2")
app.connector("node").connect(node1.connector("apps"))

#from nepi.util.parser.base import Parser
#p = Parser()
#data = p.to_data(experiment)
#print data
#e2 = p.from_data(data)
#data2 = p.to_data(e2)
#print data2

#print data == data2
#print experiment.xml_description


