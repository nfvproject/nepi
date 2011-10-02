#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from optparse import OptionParser, SUPPRESS_HELP
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP
import test_util
import os
import shutil
import tempfile
import itertools
import time
import math

"""

   ___________________________________________________________
  |   NETNS                                                   |
  |                                                           |
  |                    __________                             | 
  |                   |netns_node|  VLC_SERVER                |
  |                   |__________|                            |
  |                                                           |
  |                       1/30                                |
  |                    -----------                            |
  |_________________________|_________________________________|
                            |  
                            |  0/30
   _________________________|_________________________________
  |    PL1                  |                                 |  
  |                   ------------                            |
  |                       2/30                                |
  |                                                           |
  |                       5/30                                |
  |                  -------------                            |
  |_________________________|_________________________________|
                            | 
                            |   4/30
   _________________________|_________________________________
  |    NS-3                 |                                 |
  |                     --------                              |  
  |                       6/30                                |
  |                      ______                               |
  |                     |  AP  |                              |
  |                     |______|                              |
  |                       33/27                               |
  |                     --------                              |
  |                       ((*))                               |
  |                                                           |
  |                                                           |
  |     ((*))       ((*))       ((*))     ((*))               |         
  |    -------     --------    -------   -------              |          
  |     34/27       35/27      36/27      37/27               |          
  |    +-----+     +-----+    +-----+    +-----+              |
  |    |sta0 |     |sta1 |    |sta2 |    |sta3 |              |
  |    +-----+     +-----+    +-----+    +-----+              |
  |     66/30       70/30      74/30      78/30               |
  |    -------     -------    -------    -------              |
  |_______|___________|__________|__________|_________________|
          |           |          |          |
    ______|____   ____|____   ___|____   ___|____
   | PL2  |    | |PL3 |    | |PL4|    | |PL5|    | 
   |      |    | |    |    | |   |    | |   |    |
   | -------   | | ------- | | ------ | |------- |  
   |  65/30    | |  69/30  | | 73/30  | | 77/30  |                                 
   |___________| |_________| |________| |________|

"""

class WirelessOverlay(object):
    def __init__(self):
        usage = "usage: %prog -n number_sta -m movie -u user"
        parser = OptionParser(usage=usage)
        parser.add_option("-u", "--user", dest="user", help="Valid linux system user (not root).", type="str")
        parser.add_option("-m", "--movie", dest="movie", help="Path to movie file to play", type="str")
        parser.add_option("-n", "--nsta", dest="nsta", help="Number of wifi stations", type="int")
        parser.add_option("-a", "--base_addr", dest="base_addr", help="Base address segment for the experiment", type="str")
        parser.add_option("-s", "--slicename", dest="slicename", help="PlanetLab slice", type="str")
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
        self.nsta = options.nsta if options.nsta else 3
        self.slicename = options.slicename if options.slicename else "inria_nepi3"
        base = options.base_addr if options.base_addr else "192.168.4"
        self.base_addr = base + ".%d"
        self.root_dir = tempfile.mkdtemp()

    def add_ip_address(self, iface, address, netprefix):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)
        ip.set_attribute_value("NetPrefix", netprefix)

    def add_route(self, node, destination, netprefix, nexthop):
        route = node.add_route()
        route.set_attribute_value("Destination", destination)
        route.set_attribute_value("NetPrefix", netprefix)
        route.set_attribute_value("NextHop", nexthop)

    def add_ns3_fdnd(self, ns3_desc, node):
        fdnd = ns3_desc.create("ns3::FdNetDevice")
        node.connector("devs").connect(fdnd.connector("node"))
        #fdnd.enable_trace("FdPcapTrace")
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

        #phy.enable_trace("YansWifiPhyPcapTrace")
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

    def add_pl_testbed(self, exp_desc):
        plchost = "nepiplc.pl.sophia.inria.fr"
        port_base = 2000 + (os.getpid() % 1000) * 13
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = test_util.pl_auth()

        pl_provider = FactoriesProvider("planetlab")
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", self.slicename)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        pl_desc.set_attribute_value("plcHost", plchost)
        pl_desc.set_attribute_value("tapPortBase", port_base)
        pl_desc.set_attribute_value("p2pDeployment", False) # it's interactive, we don't want it in tests
        pl_desc.set_attribute_value("dedicatedSlice", True)
        pl_desc.set_attribute_value("plLogLevel", "DEBUG")
        return pl_desc

    def add_pl_node(self, pl_desc, inet, label_prefix):
        node = pl_desc.create("Node")
        node.set_attribute_value("label", label_prefix)
        iface = pl_desc.create("NodeInterface")
        iface.set_attribute_value("label", label_prefix+"iface")
        iface.connector("inet").connect(inet.connector("devs"))
        node.connector("devs").connect(iface.connector("node"))
        forwarder = pl_desc.create("MulticastForwarder")
        forwarder.enable_trace("stderr")
        node.connector("apps").connect(forwarder.connector("node"))
        return node, iface

    def add_ns3_in_pl(self, exp_desc, pl_desc, pl_node, pl_iface, root):
        # Add NS3 support in node
        plnepi = pl_desc.create("NepiDependency")
        plns3 = pl_desc.create("NS3Dependency")
        plnepi.connector("node").connect(pl_node.connector("deps"))
        plns3.connector("node").connect(pl_node.connector("deps"))

        # Create NS3 testbed running in pl_node
        ns3_provider = FactoriesProvider("ns3")
        ns3_desc = exp_desc.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("rootDirectory", root)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[%s].addr[0].[Address]#}" % (
            pl_iface.get_attribute_value("label"),))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl_desc.get_attribute_value("slice"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl_desc.get_attribute_value("sliceSSHKey"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "{#[%s].[%s]#}" % (
                pl_node.get_attribute_value("label"),
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))
        ns3_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        return ns3_desc

    def add_netns_testbed(self, exp_desc):
        netns_provider = FactoriesProvider("netns")
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self.root_dir)
        netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        netns_root_dir = os.path.join(self.root_dir, "netns")
        os.mkdir(netns_root_dir)
        netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
        netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        netns_desc.set_attribute_value(DC.USE_SUDO, True)
        return netns_desc

    def add_netns_node(self, netns_desc):
        node = netns_desc.create("Node")
        node.set_attribute_value("forward_X11", True)
        return node

    def add_pl_ns3_connection(self, pl_desc, pl_node, pl_addr,
            ns3_desc, ns3_node, ns3_addr):
        pl_tap = pl_desc.create("TapInterface")
        pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        self.add_ip_address(pl_tap, pl_addr, 30)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        ns3_fdnd = ns3_desc.create("ns3::FdNetDevice")
        ns3_node.connector("devs").connect(ns3_fdnd.connector("node"))
        self.add_ip_address(ns3_fdnd, ns3_addr, 30)
        pl_tap.connector("fd->").connect(ns3_fdnd.connector("->fd"))

    def add_pl_ns3_tunchan_connection(self, pl_desc, pl_node, pl_addr,
            ns3_desc, ns3_node, ns3_addr):
        pl_tap = pl_desc.create("TunInterface")
        self.add_ip_address(pl_tap, pl_addr, 30)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        ns3_fdnd = ns3_desc.create("ns3::FdNetDevice")
        ns3_fdnd.enable_trace("FdPcapTrace")
        self.add_ip_address(ns3_fdnd, ns3_addr, 30)
        ns3_node.connector("devs").connect(ns3_fdnd.connector("node"))
        ns3_tc = ns3_desc.create("ns3::Nepi::TunChannel")
        ns3_tc.connector("fd->").connect(ns3_fdnd.connector("->fd"))
        pl_tap.connector("tcp").connect(ns3_tc.connector("tcp"))

    def add_pl_netns_connection(self, pl_desc, pl_node, pl_addr,
            netns_desc, netns_node, netns_addr):
        pl_tap = pl_desc.create("TunInterface")
        pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        pl_tap.set_attribute_value("multicast", True) 
        #pl_tap.enable_trace("pcap")
        #pl_tap.enable_trace("packets")
        self.add_ip_address(pl_tap, pl_addr, 30)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        netns_tap = netns_desc.create("TunNodeInterface")
        netns_tap.set_attribute_value("up", True)
        netns_tap.set_attribute_value("mtu", 1448)
        self.add_ip_address(netns_tap, netns_addr, 30)
        netns_node.connector("devs").connect(netns_tap.connector("node"))
        netns_tunchannel = netns_desc.create("TunChannel")
        netns_tunchannel.set_attribute_value("tun_cipher", "PLAIN") 
        netns_tunchannel.connector("->fd").connect(netns_tap.connector("fd->"))
        pl_tap.connector("tcp").connect(netns_tunchannel.connector("tcp"))

    def run(self):
        exp_desc = ExperimentDescription()

        ## PL ##
        pl_desc = self.add_pl_testbed(exp_desc)
        pl_inet = pl_desc.create("Internet")
        pl_node1, pl_iface1 = self.add_pl_node(pl_desc, pl_inet, 
                "node1_pl")

        ## NETNS ##
        netns_desc = self.add_netns_testbed(exp_desc)
        netns_node = self.add_netns_node(netns_desc)

        ## NS3 ##
        ns3_desc = self.add_ns3_in_pl(exp_desc, pl_desc, pl_node1, pl_iface1, "ns3")
        wifi_chan = self.add_ns3_wifi_channel(ns3_desc)
        
        # AP node
        ap_node = self.add_ns3_node(ns3_desc)
        self.add_ns3_constant_mobility(ns3_desc, ap_node, 0, 0, 0)
        ap_wifi, ap_phy = self.add_ns3_wifi(ns3_desc, ap_node, access_point = True)
        self.add_ip_address(ap_wifi, (self.base_addr%33), 27)
        ap_phy.connector("chan").connect(wifi_chan.connector("phys"))

        # wifi network 32/27
        r = 50
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

            self.add_route(stai, (self.base_addr%0), 30, (self.base_addr%33))
            self.add_route(stai, (self.base_addr%4), 30, (self.base_addr%33))

            net = 64 + i*4
            pl_nodei, pl_ifacei = self.add_pl_node(pl_desc, pl_inet, 
                    "node2%d_pl"%i)

            pl_addr = (self.base_addr%(net+1))
            ns3_addr = (self.base_addr%(net+2))
            self.add_pl_ns3_tunchan_connection(pl_desc, pl_nodei, pl_addr,
                ns3_desc, stai, ns3_addr)
            self.add_route(pl_nodei, (self.base_addr%32), 27, ns3_addr)
            self.add_route(pl_nodei, (self.base_addr%0), 30, ns3_addr)
            self.add_route(pl_nodei, (self.base_addr%4), 30, ns3_addr)

            network = (self.base_addr%net)
            self.add_route(netns_node, network, 30, (self.base_addr%2))
            self.add_route(pl_node1, network, 30, (self.base_addr%6))
            self.add_route(ap_node, network, 30, wifi_addr)
        
        # connection PL1/NETNS
        pl_addr = (self.base_addr%2)
        netns_addr = (self.base_addr%1)
        self.add_pl_netns_connection(pl_desc, pl_node1, pl_addr,
            netns_desc, netns_node, netns_addr)
        
        # connection PL1/NS3
        pl_addr = (self.base_addr%5)
        ns3_addr = (self.base_addr%6)
        self.add_pl_ns3_connection(pl_desc, pl_node1, pl_addr,
            ns3_desc, ap_node, ns3_addr)
        
        # APPLICATIONS
        command = "xterm" 
        app = netns_desc.create("Application")
        app.set_attribute_value("command", command)
        app.set_attribute_value("user", self.user)
        app.connector("node").connect(netns_node.connector("apps"))

        # applications
        #target = "{#[%s].addr[0].[Address]#}" % label
        servers = []
        clients = []
        net = 0
        target = self.base_addr%2
        local = self.base_addr%1
        port = 5065
        command = "sleep 2; vlc -I dummy %s --miface-addr=%s --sout '#udp{dst=%s:%d}' vlc://quit" \
            % (local,self.movie, target, port)
        vlc_server = netns_desc.create("Application")
        vlc_server.set_attribute_value("command", command)
        vlc_server.set_attribute_value("user", self.user)
        vlc_server.connector("node").connect(netns_node.connector("apps"))
        servers.append(vlc_server.guid)

        command = "sudo dbus-uuidgen --ensure; vlc -vvv -I dummy udp://@%s:%d --sout '#std{access=file,mux=ts,dst=big_buck_bunny_stream.ts}' "  % (target, port)
        vlc_client = pl_desc.create("Application")
        vlc_client.set_attribute_value("buildDepends", "vlc")
        vlc_client.set_attribute_value("rpmFusion", True)
        vlc_client.set_attribute_value("command", command)
        vlc_client.enable_trace("stdout")
        vlc_client.enable_trace("stderr")
        vlc_client.connector("node").connect(pl_node1.connector("apps"))
        clients.append(vlc_client.guid)

        # ROUTES
        self.add_route(netns_node, (self.base_addr%32), 27, (self.base_addr%2))
        self.add_route(netns_node, (self.base_addr%4), 30, (self.base_addr%2))
        
        self.add_route(pl_node1, (self.base_addr%32), 27, (self.base_addr%6))

        self.add_route(ap_node, (self.base_addr%0), 30, (self.base_addr%5))
        
        xml = exp_desc.to_xml()
        controller = ExperimentController(xml, self.root_dir)
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        time.sleep(0.1)
        controller.stop()
        controller.shutdown()

        """
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
        """

    def clean(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    example = WirelessOverlay()
    example.run()
    example.clean()

