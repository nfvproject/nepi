#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from optparse import OptionParser, SUPPRESS_HELP
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC
import os
import shutil
import tempfile
import itertools
import time
import math

"""
  -----------------------------------------------------------------------
  |    NETNS                                                            |                                    
  |                                                                     |
  |    +-----+     +-----+    +-----+    +-----+          +------+      |
  |    |node1|     |node2|    |node3|    |node4 |         |server|      |
  |    +-----+     +-----+    +-----+    +-----+          +------+      |
  |     65/30       69/30      73/30      77/30            226/30       |
  |    -------     -------    -------    -------          --------      |
  |       |           |          |          |                |          |
  |---------------------------------------------------------------------|
  |       |           |          |          |                |          | 
  |    -------     -------    -------    -------             |          |
  |     66/30       30/30     74/30       78/30              |          |
  |    +-----+     +-----+    +-----+    +-----+             |          |
  |    |sta0 |     |sta1 |    |sta2 |    |sta3 |             |          |
  |    +-----+     +-----+    +-----+    +-----+             |          |
  |     34/27       35/27      36/27      37/27              |          |
  |    -------     --------    -------   -------             |          |
  |     ((*))       ((*))       ((*))     ((*))              |          |
  |                                                          |          |
  |                                                          |          |
  |                       ((*))                              |          |
  |                     --------                             |          |
  |                       33/27                              |          |
  |                     +------+                             |          |
  |                     |  AP  |  225/30 |--------------------          |
  |                     +------+                                        |
  |                                                                     |
  |     NS-3                                                            |
  -----------------------------------------------------------------------

"""

class WirelessOverlay(object):
    def __init__(self):
        usage = "usage: %prog -n number_sta -m movie -u user"
        parser = OptionParser(usage=usage)
        parser.add_option("-u", "--user", dest="user", help="Valid linux system user (not root).", type="str")
        parser.add_option("-m", "--movie", dest="movie", help="Path to movie file to play", type="str")
        parser.add_option("-n", "--nsta", dest="nsta", help="Number of wifi stations", type="int")
        parser.add_option("-a", "--base_addr", dest="base_addr", help="Base address segment for the experiment", type="str")
        (options, args) = parser.parse_args()
        if not options.movie:
            parser.error("Missing 'movie' option.")
        if options.user == 'root':
            parser.error("Missing or invalid 'user' option.")
        if options.user == 'root':
            parser.error("Missing or invalid 'user' option.")
        if options.nsta and options.nsta > 8:
            parser.error("Try a number of stations under 9.")

        self.user = options.user if options.user else os.getlogin()
        self.movie = options.movie
        self.nsta = options.nsta if options.nsta else 4
        base = options.base_addr if options.base_addr else "192.168.4"
        self.base_addr = base + ".%d"
        self.root_dir = tempfile.mkdtemp()

    def add_netns_tap(self, netns_desc, node):
        tap = netns_desc.create("TapNodeInterface")
        tap.set_attribute_value("up", True)
        node.connector("devs").connect(tap.connector("node"))
        return tap

    def add_ns3_fdnd(self, ns3_desc, node):
        fdnd = ns3_desc.create("ns3::FdNetDevice")
        node.connector("devs").connect(fdnd.connector("node"))
        fdnd.enable_trace("FdPcapTrace")
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

    def add_ns3_wifi(self, ns3_desc, node, access_point = False):
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

        phy.enable_trace("YansWifiPhyPcapTrace")
        return wifi, phy

    def add_ns3_constant_mobility(self, ns3_desc, node, x, y, z):
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

    def add_ip_address(self, iface, address, netprefix):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)
        ip.set_attribute_value("NetPrefix", netprefix)

    def add_route(self, node, destination, netprefix, nexthop):
        route = node.add_route()
        route.set_attribute_value("Destination", destination)
        route.set_attribute_value("NetPrefix", netprefix)
        route.set_attribute_value("NextHop", nexthop)

    def run(self):
        exp_desc = ExperimentDescription()

        ## NS3 ##

        ns3_provider = FactoriesProvider("ns3")
        ns3_desc = exp_desc.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("homeDirectory", self.root_dir)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)
        
        ## NS3 wifi network 32/27
        r = 50
        wifi_chan = self.add_ns3_wifi_channel(ns3_desc)
        
        # AP node
        ap = self.add_ns3_node(ns3_desc)
        self.add_ns3_constant_mobility(ns3_desc, ap, 0, 0, 0)

        wifi_ap, phy_ap = self.add_ns3_wifi(ns3_desc, ap, access_point = True)
        self.add_ip_address(wifi_ap, (self.base_addr%33), 27)
        phy_ap.connector("chan").connect(wifi_chan.connector("phys"))
        
        sta_nodes = []
        
        # STA nodes
        for i in xrange(0, self.nsta):
            stai = self.add_ns3_node(ns3_desc)
            angi = (360/self.nsta)*i
            xi = r*math.cos(angi)
            yi = r*math.sin(angi)
            self.add_ns3_constant_mobility(ns3_desc, stai, xi, yi, 0)
            wifi, phy= self.add_ns3_wifi(ns3_desc, stai, access_point = False)
            wifi_addr = self.base_addr%(34 + i)
            self.add_ip_address(wifi, wifi_addr, 27)
            phy.connector("chan").connect(wifi_chan.connector("phys"))
            sta_nodes.append((stai, wifi_addr))

        ## NETNS ##

        netns_provider = FactoriesProvider("netns")
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self.root_dir)
        netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        netns_root_dir = os.path.join(self.root_dir, "netns_instance")
        os.mkdir(netns_root_dir)
        netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
        netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        netns_desc.set_attribute_value(DC.USE_SUDO, True)

        server = netns_desc.create("Node")
        server.set_attribute_value("forward_X11", True)

        #command = "xterm" 
        #app = netns_desc.create("Application")
        #app.set_attribute_value("command", command)
        #app.set_attribute_value("user", self.user)
        #app.connector("node").connect(server.connector("apps"))

        # INTERCONNECTION NETNS/NS3

        tap = self.add_netns_tap(netns_desc, server)
        fdnd_ap = self.add_ns3_fdnd(ns3_desc, ap)
        fdnd_ap.connector("->fd").connect(tap.connector("fd->"))
        ## net NS3::fdnd/NETNS::tap 224/30
        self.add_ip_address(fdnd_ap, (self.base_addr%225), 30)
        self.add_ip_address(tap, (self.base_addr%226), 30)

        # ROUTES
        self.add_route(server, (self.base_addr%32), 27, (self.base_addr%225))

        servers = []
        clients = []
        i = 0
        for (stai, wifi_addr) in sta_nodes:
            # fdnd - netns tap
            nodei = netns_desc.create("Node")
            nodei.set_attribute_value("forward_X11", True)
            label = "client%d" % i
            nodei.set_attribute_value("label", label)
            tapi = self.add_netns_tap(netns_desc, nodei)
            fdndi = self.add_ns3_fdnd(ns3_desc, stai)
            fdndi.connector("->fd").connect(tapi.connector("fd->"))
            
            ## net NS3::fdnd/NETNS::tap subnets of 64/27
            net = 64 + i
            self.add_ip_address(tapi, (self.base_addr%(net + 1)), 30)
            self.add_ip_address(fdndi, (self.base_addr%(net + 2)), 30)
            
            # routes
            self.add_route(nodei, (self.base_addr%32), 27, (self.base_addr%(net+2)))
            self.add_route(nodei, (self.base_addr%224), 30, (self.base_addr%(net+2)))
            self.add_route(stai, (self.base_addr%224), 30, (self.base_addr%33))
            
            self.add_route(ap, (self.base_addr%net), 30, wifi_addr)
            self.add_route(server, (self.base_addr%net), 30, (self.base_addr%225))

            # applications
            #target = "{#[%s].addr[0].[Address]#}" % label
            target = self.base_addr%(net+1)
            port = 5000 + net + 1
            command = "vlc -I dummy %s --sout '#rtp{dst=%s,port=%d,mux=ts}' vlc://quit" \
                % (self.movie, target, port)
            vlc_server = netns_desc.create("Application")
            vlc_server.set_attribute_value("command", command)
            vlc_server.set_attribute_value("user", self.user)
            vlc_server.connector("node").connect(server.connector("apps"))
            servers.append(vlc_server.guid)

            command = "vlc rtp://%s:%d/test.ts" % (target, port)
            vlc_client = netns_desc.create("Application")
            vlc_client.set_attribute_value("command", command)
            vlc_client.set_attribute_value("user", self.user)
            vlc_client.connector("node").connect(nodei.connector("apps"))
            clients.append(vlc_client.guid)

            i += 4

        xml = exp_desc.to_xml()
        controller = ExperimentController(xml, self.root_dir)
        controller.start()
        stop = False
        while not stop:
            time.sleep(0.5)
            stop = True
            for guid in clients:
                if not controller.is_finished(guid):
                    stop = False
        time.sleep(0.1)
        controller.stop()
        controller.shutdown()

    def clean(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    example = WirelessOverlay()
    example.run()
    example.clean()

