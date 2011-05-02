#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
import os
import shutil
import tempfile
import test_util
import time
import unittest

class VlcWirelessNetnsNs3TestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def add_netns_tap(self, node, netns_desc):
        tap = netns_desc.create("TapNodeInterface")
        tap.set_attribute_value("up", True)
        node.connector("devs").connect(tap.connector("node"))
        return tap

    def add_ns3_fdnd(self, node, ns3_desc):
        fdnd = ns3_desc.create("ns3::FileDescriptorNetDevice")
        node.connector("devs").connect(fdnd.connector("node"))
        fdnd.enable_trace("FileDescriptorPcapTrace")
        return fdnd

    def add_ns3_node(self, ns3_desc):
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

    def add_ns3_wifi(self, node, ns3_desc, access_point = False):
        wifi = ns3_desc.create("ns3::WifiNetDevice")
        node.connector("devs").connect(wifi.connector("node"))

        phy = ns3_desc.create("ns3::YansWifiPhy")
        error = ns3_desc.create("ns3::NistErrorRateModel")
        manager = ns3_desc.create("ns3::ArfWifiManager")
        if access_point:
            mac = ns3_desc.create("ns3::QapWifiMac")
        else:
            mac = ns3_desc.create("ns3::QstaWifiMac")

        phy.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
        mac.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
        phy.connector("err").connect(error.connector("phy"))
        wifi.connector("phy").connect(phy.connector("dev"))
        wifi.connector("mac").connect(mac.connector("dev"))
        wifi.connector("manager").connect(manager.connector("dev"))

        phy.enable_trace("YansWifiPhyPcapTrace")
        return wifi, phy

    def add_ns3_random_mobility(self, node, ns3_desc, x, y, z, speed, 
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

    def add_ns3_constant_mobility(self, node, ns3_desc, x, y, z):
        mobility = ns3_desc.create("ns3::ConstantPositionMobilityModel") 
        position = "%d:%d:%d" % (x, y, z)
        mobility.set_attribute_value("Position", position)
        node.connector("mobility").connect(mobility.connector("node"))
        return mobility

    def add_ns3_wifi_channel(self, ns3_desc):
        channel = ns3_desc.create("ns3::YansWifiChannel")
        delay = ns3_desc.create("ns3::ConstantSpeedPropagationDelayModel")
        loss  = ns3_desc.create("ns3::LogDistancePropagationLossModel")
        channel.connector("delay").connect(delay.connector("chan"))
        channel.connector("loss").connect(loss.connector("prev"))
        return channel

    def add_ip_address(self, iface, address):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)

    def add_route(self, node, destination, netprefix, nexthop):
        route = node.add_route()
        route.set_attribute_value("Destination", destination)
        route.set_attribute_value("NetPrefix", netprefix)
        route.set_attribute_value("NextHop", nexthop)

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_local(self):
        bounds_width = bounds_height = 200
        x = y = 100
        speed = 1
        user = "alina"
        movie = "/tmp/test.ts"

        exp_desc = ExperimentDescription()

        ## NS3 Testbed instance description ##
        testbed_version = "3_9_RC3"
        testbed_id = "ns3"
        ns3_provider = FactoriesProvider(testbed_id, testbed_version)
        ns3_desc = exp_desc.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("homeDirectory", self.root_dir)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)
        # create node 1
        node1 = self.add_ns3_node(ns3_desc)
        mobility1 = self.add_ns3_constant_mobility(node1, ns3_desc, x, y, 0)
        wifi1, phy1 = self.add_ns3_wifi(node1, ns3_desc, access_point = False)
        self.add_ip_address(wifi1, "10.0.1.1")
        fdnd1 = self.add_ns3_fdnd(node1, ns3_desc)
        self.add_ip_address(fdnd1, "10.0.0.1")
        # create node 2
        node2 = self.add_ns3_node(ns3_desc)
        mobility2 = self.add_ns3_random_mobility(node2, ns3_desc, 0, 0, 0, 
                speed, bounds_width, bounds_height)
        wifi2, phy2 = self.add_ns3_wifi(node2, ns3_desc, access_point = True)
        self.add_ip_address(wifi2, "10.0.1.2")
        fdnd2 = self.add_ns3_fdnd(node2, ns3_desc)
        self.add_ip_address(fdnd2, "10.0.2.1")
        # interconnect nodes with a wifi channel
        wifichan = self.add_ns3_wifi_channel(ns3_desc)
        phy1.connector("chan").connect(wifichan.connector("phys"))
        phy2.connector("chan").connect(wifichan.connector("phys"))

        ## NETNS testbed description 1 ##
        testbed_version = "01"
        testbed_id = "netns"
        netns_provider = FactoriesProvider(testbed_id, testbed_version)
        netns_desc1 = exp_desc.add_testbed_description(netns_provider)
        netns_desc1.set_attribute_value("homeDirectory", self.root_dir)
        #netns_desc1.set_attribute_value("enableDebug", True
        # create node 3
        node3 = netns_desc1.create("Node")
        node3.set_attribute_value("forward_X11", True)
        tap1 = self.add_netns_tap(node3, netns_desc1)
        self.add_ip_address(tap1, "10.0.0.2")
        # create vlc server
        # DEBUG!! target = "{#[vlc_client].addr[0].[Address]#}"
        target = "10.0.2.2" 
        command = "vlc -I dummy -vvv %s --sout '#rtp{dst=%s,port=5004,mux=ts}' vlc:quit" \
                % (movie, target)
        vlc_server = netns_desc1.create("Application")
        vlc_server.set_attribute_value("command", command)
        vlc_server.set_attribute_value("user", user)
        vlc_server.connector("node").connect(node3.connector("apps"))

        #command = "xterm"
        #xterm1 = netns_desc1.create("Application")
        #xterm1.set_attribute_value("command", command)
        #xterm1.set_attribute_value("user", user)
        #xterm1.connector("node").connect(node3.connector("apps"))

        ## NETNS testbed description 2 ##
        netns_desc2 = exp_desc.add_testbed_description(netns_provider)
        netns_desc2.set_attribute_value("homeDirectory", self.root_dir)
        #netns_desc2.set_attribute_value("enableDebug", True)
        # create node 4
        node4 = netns_desc2.create("Node")
        node4.set_attribute_value("forward_X11", True)
        node4.set_attribute_value("label", "vlc_client")
        tap2 = self.add_netns_tap(node4, netns_desc2)
        self.add_ip_address(tap2, "10.0.2.2")
        # create vlc client
        vlc_client = netns_desc2.create("Application")
        command = "vlc rtp://%s:5004/test.ts" % target
        vlc_client.set_attribute_value("command", command)
        vlc_client.set_attribute_value("user", user)
        vlc_client.connector("node").connect(node4.connector("apps"))
        #vlc_trace = vlc_server.get_trace("StderrTrace")
        #vlc_trace.get_attribute("Filename").value = "vlc_server.err"
        #vlc_trace.enable()        

        #command = "xterm"
        #xterm2 = netns_desc2.create("Application")
        #xterm2.set_attribute_value("command", command)
        #xterm2.set_attribute_value("user", user)
        #xterm2.connector("node").connect(node4.connector("apps"))

        ## testbed_interconnection
        fdnd1.connector("fd").connect(tap1.connector("fd"))
        fdnd2.connector("fd").connect(tap2.connector("fd"))
      
        self.add_route(node4, "10.0.0.0", 24, "10.0.2.1")
        self.add_route(node4, "10.0.1.0", 24, "10.0.2.1")
        self.add_route(node3, "10.0.2.0", 24, "10.0.0.1")
        self.add_route(node3, "10.0.1.0", 24, "10.0.0.1")

        self.add_route(node2, "10.0.0.0", 24, "10.0.1.1")
        self.add_route(node1, "10.0.2.0", 24, "10.0.1.2")


        xml = exp_desc.to_xml()
        controller = ExperimentController(xml, self.root_dir)
        controller.start()
        while not controller.is_finished(vlc_server.guid):
            time.sleep(0.5)
        controller.stop()
        controller.shutdown()

    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()
