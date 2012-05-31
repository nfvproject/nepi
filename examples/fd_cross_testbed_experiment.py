#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Experiment Topology:
#
#  ns-3        |     NETNS 
#              |

#             fd   
#  n1 --- n2 ----- n3 --- n4
#              
#     0.0     1.0     2.0 


from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
import getpass
import tempfile
import time

user = getpass.getuser()
root_dir = tempfile.mkdtemp()

def create_ns3_node(ns3_desc):
    node = ns3_desc.create("ns3::Node")
    ipv4 = ns3_desc.create("ns3::Ipv4L3Protocol")
    arp  = ns3_desc.create("ns3::ArpL3Protocol")
    icmp = ns3_desc.create("ns3::Icmpv4L4Protocol")
    udp = ns3_desc.create("ns3::UdpL4Protocol")
    node.connector("protos").connect(ipv4.connector("node"))
    node.connector("protos").connect(arp.connector("node"))
    node.connector("protos").connect(icmp.connector("node"))
    node.connector("protos").connect(udp.connector("node"))
    return node

exp_desc = ExperimentDescription()

ns3_provider = FactoriesProvider("ns3")
ns3_desc = exp_desc.add_testbed_description(ns3_provider)
ns3_desc.set_attribute_value("homeDirectory", root_dir)
ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
ns3_desc.set_attribute_value("ChecksumEnabled", True)

node1 = create_ns3_node(ns3_desc)
iface12 = ns3_desc.create("ns3::PointToPointNetDevice")
queue12 = ns3_desc.create("ns3::DropTailQueue")
node1.connector("devs").connect(iface12.connector("node"))
iface12.connector("queue").connect(queue12.connector("dev"))
ip12 = iface12.add_address()
ip12.set_attribute_value("Address", "10.0.0.1")

node2 = create_ns3_node(ns3_desc)
iface21 = ns3_desc.create("ns3::PointToPointNetDevice")
queue21 = ns3_desc.create("ns3::DropTailQueue")
node2.connector("devs").connect(iface21.connector("node"))
iface21.connector("queue").connect(queue21.connector("dev"))
ip21 = iface21.add_address()
ip21.set_attribute_value("Address", "10.0.0.2")

chan = ns3_desc.create("ns3::PointToPointChannel")
iface12.connector("chan").connect(chan.connector("dev2"))
iface21.connector("chan").connect(chan.connector("dev2"))

iface23 = ns3_desc.create("ns3::FdNetDevice")
node2.connector("devs").connect(iface23.connector("node"))
ip23 = iface23.add_address()
ip23.set_attribute_value("Address", "10.0.1.1")

netns_provider = FactoriesProvider("netns")
netns_desc = exp_desc.add_testbed_description(netns_provider)
netns_desc.set_attribute_value("homeDirectory", root_dir)
#netns_desc.set_attribute_value("enableDebug", True)

node3 = netns_desc.create("Node")
iface32 = netns_desc.create("TapNodeInterface")
iface32.set_attribute_value("up", True)
node3.connector("devs").connect(iface32.connector("node"))
ip32 = iface32.add_address()
ip32.set_attribute_value("Address", "10.0.1.2")

iface23.connector("->fd").connect(iface32.connector("fd->"))

iface34 = netns_desc.create("P2PNodeInterface")
iface34.set_attribute_value("up", True)
node3.connector("devs").connect(iface34.connector("node"))
ip34 = iface34.add_address()
ip34.set_attribute_value("Address", "10.0.2.1")

node4 = netns_desc.create("Node")
node4.set_attribute_value("forward_X11", True)
iface43 = netns_desc.create("P2PNodeInterface")
iface43.set_attribute_value("up", True)
node4.connector("devs").connect(iface43.connector("node"))
ip43 = iface43.add_address()
ip43.set_attribute_value("Address", "10.0.2.2")

iface34.connector("p2p").connect(iface43.connector("p2p"))

route = node1.add_route()
route.set_attribute_value("Destination", "10.0.2.0")
route.set_attribute_value("NextHop", "10.0.0.2")

route = node2.add_route()
route.set_attribute_value("Destination", "10.0.2.0")
route.set_attribute_value("NextHop", "10.0.1.2")

route = node3.add_route()
route.set_attribute_value("Destination", "10.0.0.0")
route.set_attribute_value("NextHop", "10.0.1.1")

route = node4.add_route()
route.set_attribute_value("Destination", "10.0.0.0")
route.set_attribute_value("NextHop", "10.0.2.1")

app = netns_desc.create("Application")
app.set_attribute_value("command", "ping -qc 3 10.0.0.1")
app.set_attribute_value("user", user)
app.connector("node").connect(node4.connector("apps"))
app.enable_trace("stdout")
      
xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)

controller.start()
while not controller.is_finished(app.guid):
    time.sleep(0.5)

result = controller.trace(app.guid, "stdout")

controller.stop()
controller.shutdown()

print result

