#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Experiment Topology:
#
#  n1 --- n2
#  0.1   0.2 
#    

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
import tempfile
import time

root_dir = tempfile.mkdtemp()

exp_desc = ExperimentDescription()

testbed_id = "ns3"
ns3_provider = FactoriesProvider(testbed_id)
ns3_desc = exp_desc.add_testbed_description(ns3_provider)
ns3_desc.set_attribute_value("homeDirectory", root_dir)
ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
ns3_desc.set_attribute_value("ChecksumEnabled", True)

node1 = ns3_desc.create("ns3::Node")
ipv41 = ns3_desc.create("ns3::Ipv4L3Protocol")
arp1  = ns3_desc.create("ns3::ArpL3Protocol")
icmp1 = ns3_desc.create("ns3::Icmpv4L4Protocol")
node1.connector("protos").connect(ipv41.connector("node"))
node1.connector("protos").connect(arp1.connector("node"))
node1.connector("protos").connect(icmp1.connector("node"))
iface1 = ns3_desc.create("ns3::PointToPointNetDevice")
queue1 = ns3_desc.create("ns3::DropTailQueue")
node1.connector("devs").connect(iface1.connector("node"))
iface1.connector("queue").connect(queue1.connector("dev"))
trace1 = iface1.enable_trace("P2PAsciiTrace")
ip1 = iface1.add_address()
ip1.set_attribute_value("Address", "10.0.0.1")

node2 = ns3_desc.create("ns3::Node")
ipv42 = ns3_desc.create("ns3::Ipv4L3Protocol")
arp2  = ns3_desc.create("ns3::ArpL3Protocol")
icmp2 = ns3_desc.create("ns3::Icmpv4L4Protocol")
node2.connector("protos").connect(ipv42.connector("node"))
node2.connector("protos").connect(arp2.connector("node"))
node2.connector("protos").connect(icmp2.connector("node"))
iface2 = ns3_desc.create("ns3::PointToPointNetDevice")
queue2 = ns3_desc.create("ns3::DropTailQueue")
node2.connector("devs").connect(iface2.connector("node"))
iface2.connector("queue").connect(queue2.connector("dev"))
trace2 = iface2.enable_trace("P2PAsciiTrace")
ip2 = iface2.add_address()
ip2.set_attribute_value("Address", "10.0.0.2")

chan = ns3_desc.create("ns3::PointToPointChannel")
chan.set_attribute_value("Delay", "0ns")
iface1.connector("chan").connect(chan.connector("dev2"))
iface2.connector("chan").connect(chan.connector("dev2"))

app = ns3_desc.create("ns3::V4Ping")
app.set_attribute_value("Remote", "10.0.0.2")
app.set_attribute_value("Verbose", True)
app.set_attribute_value("StartTime", "0s")
app.set_attribute_value("StopTime", "20s")

app.connector("node").connect(node1.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()

time.sleep(5)

controller.set(chan.guid, "Delay", "10s")

time.sleep(5)

controller.set(chan.guid, "Delay", "0s")

while not controller.is_finished(app.guid):
    time.sleep(0.5)

controller.stop()
controller.shutdown()
