#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Experiment Topology:
#
#  n1 --- n2 --- n3
# 
#
# This example is based on the ns-3 wifi-hidden-terminal.cc example.
#

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
import tempfile
import time

def create_node(ns3_desc):
    node = ns3_desc.create("ns3::Node")
    ipv4 = ns3_desc.create("ns3::Ipv4L3Protocol")
    arp  = ns3_desc.create("ns3::ArpL3Protocol")
    icmp = ns3_desc.create("ns3::Icmpv4L4Protocol")
    udp = ns3_desc.create("ns3::UdpL4Protocol")
    tcp = ns3_desc.create("ns3::TcpL4Protocol")
    node.connector("protos").connect(ipv4.connector("node"))
    node.connector("protos").connect(arp.connector("node"))
    node.connector("protos").connect(icmp.connector("node"))
    node.connector("protos").connect(udp.connector("node"))
    node.connector("protos").connect(tcp.connector("node"))
    mobility = ns3_desc.create("ns3::ConstantPositionMobilityModel")
    node.connector("mobility").connect(mobility.connector("node"))
    
    return (node, mobility)

def create_wifi_device(ns3_desc, node, channel):
    dev = ns3_desc.create("ns3::WifiNetDevice")
    node.connector("devs").connect(dev.connector("node"))
    manager = ns3_desc.create("ns3::ConstantRateWifiManager")
    manager.set_attribute_value("DataMode", "DsssRate2Mbps")
    manager.set_attribute_value("ControlMode", "DsssRate1Mbps")
    dev.connector("manager").connect(manager.connector("dev"))

    mac = ns3_desc.create("ns3::AdhocWifiMac")
    mac.set_attribute_value("Standard",  "WIFI_PHY_STANDARD_80211b")
    mac.set_attribute_value("QosSupported", False)
    dev.connector("mac").connect(mac.connector("dev"))

    phy = ns3_desc.create("ns3::YansWifiPhy")
    phy.set_attribute_value("Standard",  "WIFI_PHY_STANDARD_80211b")
    dev.connector("phy").connect(phy.connector("dev"))
    channel.connector("phys").connect(phy.connector("chan"))
    # Without the error model it doesn'y work!!
    error = ns3_desc.create("ns3::NistErrorRateModel")
    phy.connector("err").connect(error.connector("phy"))
 
    return dev

root_dir = tempfile.mkdtemp()

exp_desc = ExperimentDescription()

testbed_id = "ns3"
ns3_provider = FactoriesProvider(testbed_id)
ns3_desc = exp_desc.add_testbed_description(ns3_provider)
ns3_desc.set_attribute_value("homeDirectory", root_dir)
#ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
#ns3_desc.set_attribute_value("ChecksumEnabled", True)

# 0. Enable or disable CTS/RTS
# ??

# 1 & 2 & 6. Create 3 nodes with their mobility models, and Install TCP/IP stack & assign IP addresses
(node1, mob1) = create_node(ns3_desc)
(node2, mob2) = create_node(ns3_desc)
(node3, mob3) = create_node(ns3_desc)

#  3. Create propagation loss matrix
matrix = ns3_desc.create("ns3::MatrixPropagationLossModel")
matrix.set_attribute_value("DefaultLoss", 200.0)

mp1 = ns3_desc.create("ns3::Nepi::MobilityPair")
mp1.connector("matrix").connect(matrix.connector("mobpair"))
mp1.set_attribute_value("Loss", 50.0)
mp1.connector("ma").connect(mob1.connector("mp"))
mp1.connector("mb").connect(mob2.connector("mp"))

mp2 = ns3_desc.create("ns3::Nepi::MobilityPair")
mp2.connector("matrix").connect(matrix.connector("mobpair"))
mp2.set_attribute_value("Loss", 50.0)
mp2.connector("ma").connect(mob3.connector("mp"))
mp2.connector("mb").connect(mob2.connector("mp"))

# 4. Create & setup wifi channel
channel = ns3_desc.create("ns3::YansWifiChannel")
channel.connector("loss").connect(matrix.connector("chan"))
# DEBUG: Works with ns3::LogDistancePropagationLossModel but now with ns3::MatrixPropagationLossModel
# loss = ns3_desc.create("ns3::LogDistancePropagationLossModel")
# channel.connector("loss").connect(loss.connector("prev"))
delay = ns3_desc.create("ns3::ConstantSpeedPropagationDelayModel")
channel.connector("delay").connect(delay.connector("chan"))

# 5. Install wireless devices

dev1 = create_wifi_device(ns3_desc, node1, channel)
ip1 = dev1.add_address()
ip1.set_attribute_value("Address", "10.0.0.1")
ip1.set_attribute_value("NetPrefix", 8)

dev2 = create_wifi_device(ns3_desc, node2, channel)
ip2 = dev2.add_address()
ip2.set_attribute_value("Address", "10.0.0.2")
ip2.set_attribute_value("NetPrefix", 8)

dev3 = create_wifi_device(ns3_desc, node3, channel)
ip3 = dev3.add_address()
ip3.set_attribute_value("Address", "10.0.0.3")
ip3.set_attribute_value("NetPrefix", 8)

app = ns3_desc.create("ns3::V4Ping")
app.set_attribute_value("Remote", "10.0.0.3")
app.set_attribute_value("Verbose", True)
app.set_attribute_value("StartTime", "0s")
app.set_attribute_value("StopTime", "20s")

app.connector("node").connect(node1.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()

while not controller.is_finished(app.guid):
    time.sleep(0.5)

controller.stop()
controller.shutdown()
