#!/usr/bin/env python

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
import getpass
import tempfile
import time

def add_ns3_random_mobility(node, ns3_desc, x, y, z, speed, 
        bounds_width, bounds_height):
    position = "%d:%d:%d" % (x, y, z)
    bounds = "0|%d|0|%d" % (bounds_width, bounds_height) 
    speed = "Constant:%d" % speed
    mobility = ns3_desc.create("ns3::RandomDirection2dMobilityModel")
    mobility.set_attribute_value("Position", position)
    mobility.set_attribute_value("Bounds", bounds)
    mobility.set_attribute_value("Speed", speed)
    mobility.set_attribute_value("Pause",  "Constant:1")
    node.connector("mobility").connect(mobility.connector("node"))
    return mobility

def add_ns3_constant_mobility(node, ns3_desc, x, y, z):
    mobility = ns3_desc.create("ns3::ConstantPositionMobilityModel") 
    position = "%d:%d:%d" % (x, y, z)
    mobility.set_attribute_value("Position", position)
    node.connector("mobility").connect(mobility.connector("node"))
    return mobility

def add_ns3_wifi_channel(ns3_desc):
    channel = ns3_desc.create("ns3::YansWifiChannel")
    delay = ns3_desc.create("ns3::ConstantSpeedPropagationDelayModel")
    loss  = ns3_desc.create("ns3::LogDistancePropagationLossModel")
    channel.connector("delay").connect(delay.connector("chan"))
    channel.connector("loss").connect(loss.connector("prev"))
    return channel

def add_ip_address(iface, address):
    ip = iface.add_address()
    ip.set_attribute_value("Address", address)

def add_route(node, destination, netprefix, nexthop):
    route = node.add_route()
    route.set_attribute_value("Destination", destination)
    route.set_attribute_value("NetPrefix", netprefix)
    route.set_attribute_value("NextHop", nexthop)

def add_ns3_wifi(node, ns3_desc, access_point = False):
    wifi = ns3_desc.create("ns3::WifiNetDevice")
    node.connector("devs").connect(wifi.connector("node"))

    phy = ns3_desc.create("ns3::YansWifiPhy")
    error = ns3_desc.create("ns3::NistErrorRateModel")
    manager = ns3_desc.create("ns3::ArfWifiManager")
    if access_point:
        mac = ns3_desc.create("ns3::ApWifiMac")
    else:
        mac = ns3_desc.create("ns3::StaWifiMac")

    phy.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
    mac.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
    phy.connector("err").connect(error.connector("phy"))
    wifi.connector("phy").connect(phy.connector("dev"))
    wifi.connector("mac").connect(mac.connector("dev"))
    wifi.connector("manager").connect(manager.connector("dev"))
    #phy.enable_trace("YansWifiPhyPcapTrace")
    return wifi, phy

def add_netns_tap(node, netns_desc):
    tap = netns_desc.create("TapNodeInterface")
    tap.set_attribute_value("up", True)
    node.connector("devs").connect(tap.connector("node"))
    return tap

def add_ns3_fdnd(node, ns3_desc):
    fdnd = ns3_desc.create("ns3::FdNetDevice")
    node.connector("devs").connect(fdnd.connector("node"))
    #fdnd.enable_trace("FileDescriptorPcapTrace")
    return fdnd

def add_ns3_node(ns3_desc):
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

user = getpass.getuser()
root_dir = tempfile.mkdtemp()
movie = "/home/alina/repos/nepi/big_buck_bunny_240p_mpeg4_lq.ts" 
bounds_width = bounds_height = 200
x = y = 100
speed = 1

exp_desc = ExperimentDescription()

ns3_provider = FactoriesProvider("ns3")
ns3_desc = exp_desc.add_testbed_description(ns3_provider)
ns3_dir = tempfile.mkdtemp()
ns3_desc.set_attribute_value("rootDirectory", ns3_dir)
ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
ns3_desc.set_attribute_value("ChecksumEnabled", True)

netns_provider = FactoriesProvider("netns")
netns_desc1 = exp_desc.add_testbed_description(netns_provider)
netns_dir1 = tempfile.mkdtemp()
netns_desc1.set_attribute_value("rootDirectory", netns_dir1)
netns_desc1.set_attribute_value("enableDebug", True)
netns_desc1.set_attribute_value("useSudo", True)
netns_desc1.set_attribute_value("deployment_communication", "LOCAL")
netns_desc1.set_attribute_value("deployment_mode", "DAEMON")

netns_provider = FactoriesProvider("netns")
netns_desc2 = exp_desc.add_testbed_description(netns_provider)
netns_dir2 = tempfile.mkdtemp()
netns_desc2.set_attribute_value("rootDirectory", netns_dir2)
netns_desc2.set_attribute_value("enableDebug", True)
netns_desc2.set_attribute_value("useSudo", True)
netns_desc2.set_attribute_value("deployment_communication", "LOCAL")
netns_desc2.set_attribute_value("deployment_mode", "DAEMON")

node1 = netns_desc1.create("Node")
node1.set_attribute_value("forward_X11", True)
tap1 = netns_desc1.create("TapNodeInterface")
tap1.set_attribute_value("up", True)
node1.connector("devs").connect(tap1.connector("node"))
ip = tap1.add_address()
ip.set_attribute_value("Address", "10.0.0.1")

node2 = add_ns3_node(ns3_desc)
fdnd1 = add_ns3_fdnd(node2, ns3_desc)
add_ip_address(fdnd1, "10.0.0.2")

fdnd1.connector("->fd").connect(tap1.connector("fd->"))

mobility1 = add_ns3_constant_mobility(node2, ns3_desc, x, y, 0)
wifi1, phy1 = add_ns3_wifi(node2, ns3_desc, access_point = False)
add_ip_address(wifi1, "10.0.1.1")

node3 = add_ns3_node(ns3_desc)
mobility2 = add_ns3_random_mobility(node3, ns3_desc, x, y, 0, 
        speed, bounds_width, bounds_height)
wifi2, phy2 = add_ns3_wifi(node3, ns3_desc, access_point = True)
add_ip_address(wifi2, "10.0.1.2")

wifichan = add_ns3_wifi_channel(ns3_desc)
phy1.connector("chan").connect(wifichan.connector("phys"))
phy2.connector("chan").connect(wifichan.connector("phys"))

fdnd2 = add_ns3_fdnd(node3, ns3_desc)
add_ip_address(fdnd2, "10.0.2.1")

node4 = netns_desc2.create("Node")
node4.set_attribute_value("forward_X11", True)
tap2 = netns_desc2.create("TapNodeInterface")
tap2.set_attribute_value("up", True)
node4.connector("devs").connect(tap2.connector("node"))
ip = tap2.add_address()
ip.set_attribute_value("Address", "10.0.2.2")

fdnd2.connector("->fd").connect(tap2.connector("fd->"))

route = node1.add_route()
route.set_attribute_value("Destination", "10.0.2.0")
route.set_attribute_value("NextHop", "10.0.0.2")

route = node1.add_route()
route.set_attribute_value("Destination", "10.0.1.0")
route.set_attribute_value("NextHop", "10.0.0.2")

route = node2.add_route()
route.set_attribute_value("Destination", "10.0.2.0")
route.set_attribute_value("NextHop", "10.0.1.2")

route = node3.add_route()
route.set_attribute_value("Destination", "10.0.0.0")
route.set_attribute_value("NextHop", "10.0.1.1")

route = node4.add_route()
route.set_attribute_value("Destination", "10.0.1.0")
route.set_attribute_value("NextHop", "10.0.2.1")

route = node4.add_route()
route.set_attribute_value("Destination", "10.0.0.0")
route.set_attribute_value("NextHop", "10.0.2.1")

app1 = netns_desc1.create("Application")
server = "10.0.2.2" 
command = "xauth -b quit; vlc -I dummy -vvv %s --sout '#rtp{dst=%s,port=5004,mux=ts}' vlc://quit" \
        % (movie, server)
#command = "xterm"
app1.set_attribute_value("command", command)
app1.set_attribute_value("user", user)
app1.connector("node").connect(node1.connector("apps"))

app4 = netns_desc2.create("Application")
command = "xauth -b quit; vlc --ffmpeg-threads=1 rtp://%s:5004/test.ts" % server
#command = "xterm"
app4.set_attribute_value("command", command)
app4.set_attribute_value("user", user)
app4.connector("node").connect(node4.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)

controller.start()
while not controller.is_finished(app4.guid):
    time.sleep(0.5)

controller.stop()
controller.shutdown()


