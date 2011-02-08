#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.experiment import ExperimentDescription

testbed_id = "netns"
testbed_version = "0.1"
experiment = ExperimentDescription()
netns = experiment.add_testbed_description(testbed_id, testbed_version)
node1 = netns.create("Node")
node2 = netns.create("Node")
iface1 = netns.create("NodeInterface")
iface1.set_attribute_value("up", True)
node1.connector("devs").connect(iface1.connector("node"))
ip1 = iface1.add_address()
p1.set_attribute_value("Address", "10.0.0.1")
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

print experiment.xml_description

description = """
<experiment>
  <testbeds>
    <testbed testbed_id="netns" testbed_version="1.0" guid="1">
      <elements>
        <element factory_id="Node" guid="2">
          <construct-parameters>
          </construct-parameters>
          <attributes>
          </attributes>
          <traces>
          </traces>
          <addresses>
          </addresses>
          <routes>
          </routes>
        </element>
      </elements>
      <connections>
      </connections>
    </testbed>
  </testbeds>
</experiment>
"""

