#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from optparse import OptionParser, SUPPRESS_HELP
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP
import os
import shutil
import tempfile
import time
import sys
import random

def pl_auth():
    user = os.environ.get('PL_USER')
    pwd = os.environ.get('PL_PASS')
     
    if user and pwd:
        return (user,pwd)
    else:
        return None

class Roads09Ns3PLExample(object):
    testbed_id = "planetlab"
    testbed_version = "01"
    slicename = "inria_nepi"
    plchost = "nepiplc.pl.sophia.inria.fr"
    
    host1 = "nepi1.pl.sophia.inria.fr"
    host2 = "nepi2.pl.sophia.inria.fr"
    host3 = "nepi3.pl.sophia.inria.fr"
    host4 = "nepi5.pl.sophia.inria.fr"
    
    def __init__(self):
        #usage = "usage: %prog -m movie -u user"
        #parser = OptionParser(usage=usage)
        #parser.add_option("-u", "--user", dest="user", help="Valid linux system user (not root).", type="str")
        #parser.add_option("-m", "--movie", dest="movie", help="Path to movie file to play", type="str")
        #(options, args) = parser.parse_args()
        #if not options.movie:
        #    parser.error("Missing 'movie' option.")
        #if options.user == 'root':
        #    parser.error("Missing or invalid 'user' option.")

        #self.user = options.user if options.user else os.getlogin()
        #self.movie =  options.movie
        
        if not pl_auth():
            print "Example requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)"
            sys.exit(1)
        
        self.root_dir = tempfile.mkdtemp()


    def make_experiment_desc(self):
        testbed_id = self.testbed_id
        testbed_version = self.testbed_version
        slicename = self.slicename
        plchost = self.plchost
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = pl_auth()

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id, testbed_version)
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", slicename)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        pl_desc.set_attribute_value("plcHost", plchost)
        
        return pl_desc, exp_desc

    def make_ns_in_pl(self, pl, exp, node1, iface1, root):
        ns3_testbed_id = "ns3"
        ns3_testbed_version = "3_9_RC3"
        
        # Add NS3 support in node1
        plnepi = pl.create("NepiDependency")
        plns3 = pl.create("NS3Dependency")
        plnepi.connector("node").connect(node1.connector("deps"))
        plns3.connector("node").connect(node1.connector("deps"))

        # Create NS3 testbed running in node1
        ns3_provider = FactoriesProvider(ns3_testbed_id, ns3_testbed_version)
        ns3_desc = exp.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("rootDirectory", root)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[%s].addr[0].[Address]#}" % (
            iface1.get_attribute_value("label"),))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "{#[%s].[%s]#}" % (
                node1.get_attribute_value("label"),
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))
        ns3_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        
        return ns3_desc
    
    

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

    def add_ns3_wifi(self, node, ns3_desc, access_point = False, ip = None, prefix = 24):
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
        
        if ip:
            self.add_ip_address(wifi, ip, prefix)

        phy.enable_trace("YansWifiPhyPcapTrace")
        return wifi, phy

    def add_ns3_random_mobility(self, node, ns3_desc, x, y, z, speed, 
            bounds_width, bounds_height):
        position = "%f:%f:%f" % (x, y, z)
        bounds = "0|%f|0|%f" % (bounds_width, bounds_height) 
        speed = "Constant:%f" % speed
        mobility = ns3_desc.create("ns3::RandomDirection2dMobilityModel")
        mobility.set_attribute_value("Position", position)
        mobility.set_attribute_value("Bounds", bounds)
        mobility.set_attribute_value("Speed", speed)
        mobility.set_attribute_value("Pause",  "Constant:1")
        node.connector("mobility").connect(mobility.connector("node"))
        return mobility

    def add_ns3_constant_mobility(self, node, ns3_desc, x, y, z):
        mobility = ns3_desc.create("ns3::ConstantPositionMobilityModel") 
        position = "%f:%f:%f" % (x, y, z)
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

    def add_ip_address(self, iface, address, prefix = 24):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)
        ip.set_attribute_value("Broadcast", True)
        ip.set_attribute_value("NetPrefix", prefix)
        return ip

    def add_route(self, nodes, destination, netprefix, nexthop):
        for node in nodes:
            route = node.add_route()
            route.set_attribute_value("Destination", destination)
            route.set_attribute_value("NetPrefix", netprefix)
            route.set_attribute_value("NextHop", nexthop)

    def make_pl_router(self, pl, hostname, label, ip, inet = None):
        pl1 = pl.create("Node")
        pl1.set_attribute_value("hostname", hostname)
        pl1.set_attribute_value("label", label)
        pl1.set_attribute_value("emulation", True)
        pl1if = pl.create("NodeInterface")
        pl1if.set_attribute_value("label", label+"if")
        pl1tap = pl.create("TapInterface")
        pl1tap.enable_trace("packets") # for error output
        pl1tap.set_attribute_value("label", label+"tap")
        pl1tap.set_attribute_value("snat", False)
        inet = inet or pl.create("Internet")
        pl1.connector("devs").connect(pl1if.connector("node"))
        pl1.connector("devs").connect(pl1tap.connector("node"))
        pl1if.connector("inet").connect(inet.connector("devs"))
        
        pl1tapip = pl1tap.add_address()
        pl1tapip.set_attribute_value("Address", ip)
        pl1tapip.set_attribute_value("NetPrefix", 24)
        pl1tapip.set_attribute_value("Broadcast", False)
        
        return pl1, pl1if, pl1tap, pl1tapip, inet
    
    def make_mesh(self, pl, exp, inet):
        scale = 1.0
        walkdistance = 1.0
        walkspeed = 0.1
    
        # Router 1 & NS3 host in PL
        pl1, pl1if, pl1tap, pl1tapip, inet = self.make_pl_router(pl, 
            self.host1, "mesh_pl1", "192.168.2.2", inet)

        # Add NS3 support in pl1
        ns3 = self.make_ns_in_pl(pl, exp, pl1, pl1if, "tb-ns3-roads09-1")
        
        # Add WiFi channel
        chan = self.add_ns3_wifi_channel(ns3)
        
        # Add APs
        ap1 = self.add_ns3_node(ns3)
        ap2 = self.add_ns3_node(ns3)
        ap3 = self.add_ns3_node(ns3)
        ap4 = self.add_ns3_node(ns3)
        ap1wifi, ap1phy = self.add_ns3_wifi(ap1, ns3, False, "192.168.2.3", 26)
        ap2wifi, ap2phy = self.add_ns3_wifi(ap2, ns3, True, "192.168.2.4", 26)
        ap3wifi, ap3phy = self.add_ns3_wifi(ap3, ns3, False, "192.168.2.5", 26)
        ap4wifi, ap4phy = self.add_ns3_wifi(ap4, ns3, False, "192.168.2.6", 26)
        self.add_ns3_constant_mobility(ap1, ns3, -scale, -scale, 0.0)
        self.add_ns3_constant_mobility(ap2, ns3, +scale, -scale, 0.0)
        self.add_ns3_constant_mobility(ap3, ns3, -scale, +scale, 0.0)
        self.add_ns3_constant_mobility(ap4, ns3, +scale, +scale, 0.0)
        
        # Add WiFi nodes
        wnode1 = self.add_ns3_node(ns3)        
        wnode2 = self.add_ns3_node(ns3)        
        wnode3 = self.add_ns3_node(ns3)        
        wnode4 = self.add_ns3_node(ns3)        
        wnode5 = self.add_ns3_node(ns3)        
        wnode1wifi, wnode1phy = self.add_ns3_wifi(wnode1, ns3, False, "192.168.2.7", 26)
        wnode2wifi, wnode2phy = self.add_ns3_wifi(wnode2, ns3, False, "192.168.2.8", 26)
        wnode3wifi, wnode3phy = self.add_ns3_wifi(wnode3, ns3, False, "192.168.2.9", 26)
        wnode4wifi, wnode4phy = self.add_ns3_wifi(wnode4, ns3, False, "192.168.2.10", 26)
        wnode5wifi, wnode5phy = self.add_ns3_wifi(wnode5, ns3, False, "192.168.2.11", 26)
        self.add_ns3_random_mobility(wnode1, ns3, -2*scale, -2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode2, ns3, -2*scale, +scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode3, ns3, -scale, +2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode4, ns3, +scale, +2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode5, ns3, +2*scale, +2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        
        # Connect all WiFi phys to the channel
        ap1phy.connector("chan").connect(chan.connector("phys"))
        ap2phy.connector("chan").connect(chan.connector("phys"))
        ap3phy.connector("chan").connect(chan.connector("phys"))
        ap4phy.connector("chan").connect(chan.connector("phys"))
        wnode1phy.connector("chan").connect(chan.connector("phys"))
        wnode2phy.connector("chan").connect(chan.connector("phys"))
        wnode3phy.connector("chan").connect(chan.connector("phys"))
        wnode4phy.connector("chan").connect(chan.connector("phys"))
        wnode5phy.connector("chan").connect(chan.connector("phys"))
        
        # Add inet connection to AP
        ap2fdnd = self.add_ns3_fdnd(ap2, ns3)
        ap2fdndip = self.add_ip_address(ap2fdnd, "192.168.2.20")
        ap2fdndip.set_attribute_value("NetPrefix", 32) # p2p
        pl1tap.connector("fd->").connect(ap2fdnd.connector("->fd"))
        pl1tap.set_attribute_value("pointopoint", "192.168.2.20")
        r = ap2.add_route()
        r.set_attribute_value("Destination", "192.168.2.2")
        r.set_attribute_value("NetPrefix", 32)
        r.set_attribute_value("NextHop", "192.168.2.20")
        
        # return mesh router
        return (
            pl1, pl1if, pl1tap, pl1tapip, 
            (wnode1, wnode2, wnode3, wnode4, wnode5),
            (wnode1wifi, wnode2wifi, wnode3wifi, wnode4wifi, wnode5wifi),
            (ap1, ap2, ap3, ap4),
            (ap1wifi, ap2wifi, ap3wifi, ap4wifi),
            ns3,
            inet,
        )
    
    def make_wifi_hotspot(self, pl, exp, inet):
        scale = 1.0
        walkdistance = 1.0
        walkspeed = 0.1
    
        # Router 1 & NS3 host in PL
        pl1, pl1if, pl1tap, pl1tapip, inet = self.make_pl_router(pl, 
            self.host2, "hs_pl1", "192.168.2.65", inet)

        # Add NS3 support in pl1
        ns3 = self.make_ns_in_pl(pl, exp, pl1, pl1if, "tb-ns3-roads09-2")
        
        # Add WiFi channel
        chan = self.add_ns3_wifi_channel(ns3)
        
        # Add APs
        ap1 = self.add_ns3_node(ns3)
        ap1wifi, ap1phy = self.add_ns3_wifi(ap1, ns3, True, "192.168.2.66", 26)
        self.add_ns3_constant_mobility(ap1, ns3, 0.0, 0.0, 0.0)
        
        # Add WiFi nodes
        wnode1 = self.add_ns3_node(ns3)
        wnode2 = self.add_ns3_node(ns3)
        wnode3 = self.add_ns3_node(ns3)
        wnode4 = self.add_ns3_node(ns3)
        wnode1wifi, wnode1phy = self.add_ns3_wifi(wnode1, ns3, False, "192.168.2.67", 26)
        wnode2wifi, wnode2phy = self.add_ns3_wifi(wnode2, ns3, False, "192.168.2.68", 26)
        wnode3wifi, wnode3phy = self.add_ns3_wifi(wnode3, ns3, False, "192.168.2.69", 26)
        wnode4wifi, wnode4phy = self.add_ns3_wifi(wnode4, ns3, False, "192.168.2.70", 26)
        self.add_ns3_random_mobility(wnode1, ns3, +scale, -2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode2, ns3, -scale, -2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode3, ns3, -2*scale, +scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        self.add_ns3_random_mobility(wnode4, ns3, -2*scale, +2*scale, 0.0, 
            walkspeed, walkdistance, walkdistance)
        
        # Connect all WiFi phys to the channel
        ap1phy.connector("chan").connect(chan.connector("phys"))
        wnode1phy.connector("chan").connect(chan.connector("phys"))
        wnode2phy.connector("chan").connect(chan.connector("phys"))
        wnode3phy.connector("chan").connect(chan.connector("phys"))
        wnode4phy.connector("chan").connect(chan.connector("phys"))
        
        # Add inet connection to AP2
        ap1fdnd = self.add_ns3_fdnd(ap1, ns3)
        ap1fdndip = self.add_ip_address(ap1fdnd, "192.168.2.80")
        ap1fdndip.set_attribute_value("NetPrefix", 32) # p2p
        pl1tap.connector("fd->").connect(ap1fdnd.connector("->fd"))
        pl1tap.set_attribute_value("pointopoint", "192.168.2.80")
        r = ap1.add_route()
        r.set_attribute_value("Destination", "192.168.2.65")
        r.set_attribute_value("NetPrefix", 32)
        r.set_attribute_value("NextHop", "192.168.2.80")
        
        # return mesh router
        return (
            pl1, pl1if, pl1tap, pl1tapip,
            (wnode1, wnode2, wnode3, wnode4),
            (wnode1wifi, wnode2wifi, wnode3wifi, wnode4wifi),
            ap1, ap1wifi,
            ns3,
            inet,
        )
    
    def run(self):
        pl, exp = self.make_experiment_desc()
    
        pl1, pl1if, pl1tap, pl1tapip, \
            mesh_nodes, mesh_node_ifs, \
            mesh_aps, mesh_ap_ifs, \
            mesh_ns, \
            inet = self.make_mesh(pl, exp, None)
        pl2, pl2if, pl2tap, pl2tapip, \
            hs_nodes, hs_node_ifs, \
            hs_ap, hs_apif, \
            hs_ns, \
            inet = self.make_wifi_hotspot(pl, exp, inet)
        
        # Connect the routers
        pl1etap = pl.create("TapInterface")
        pl1etap.enable_trace("packets") # for error output
        pl1etap.set_attribute_value("label", "pl1etap")
        pl1etapip = pl1etap.add_address()
        pl1etapip.set_attribute_value("Address", "192.168.2.1")
        pl1etapip.set_attribute_value("NetPrefix", 24)
        pl1etapip.set_attribute_value("Broadcast", False)

        pl2etap = pl.create("TapInterface")
        pl2etap.enable_trace("packets") # for error output
        pl2etap.set_attribute_value("label", "pl2etap")
        pl2etapip = pl2etap.add_address()
        pl2etapip.set_attribute_value("Address", "192.168.2.81")
        pl2etapip.set_attribute_value("NetPrefix", 24)
        pl2etapip.set_attribute_value("Broadcast", False)
        
        pl1etap.connector("node").connect(pl1.connector("devs"))
        pl2etap.connector("node").connect(pl2.connector("devs"))
        pl1etap.connector("udp").connect(pl2etap.connector("udp"))
        pl1etap.set_attribute_value("pointopoint", "192.168.2.81")
        pl2etap.set_attribute_value("pointopoint", "192.168.2.1")
        
        # Connect the networks
        
        # apn -> ap2 (n != 2)
        for ap in mesh_aps[:1] + mesh_aps[2:]:
            r = ap.add_route()
            r.set_attribute_value("Destination", "192.168.2.64")
            r.set_attribute_value("NetPrefix", 26)
            r.set_attribute_value("NextHop", 
                mesh_ap_ifs[1].addresses[0].get_attribute_value("Address") )

        for wn in mesh_nodes:
            apif = mesh_ap_ifs[ random.randint(0,len(mesh_aps)-1) ]
            r = wn.add_route()
            r.set_attribute_value("Destination", "192.168.2.64")
            r.set_attribute_value("NetPrefix", 26)
            r.set_attribute_value("NextHop", 
                apif.addresses[0].get_attribute_value("Address"))

        r = mesh_aps[1].add_route()
        r.set_attribute_value("Destination", "192.168.2.64")
        r.set_attribute_value("NetPrefix", 26)
        r.set_attribute_value("NextHop", "192.168.2.2")
        
        r = pl1.add_route()
        r.set_attribute_value("Destination", "192.168.2.64")
        r.set_attribute_value("NetPrefix", 26)
        r.set_attribute_value("NextHop", "192.168.2.81")

        r = pl2.add_route()
        r.set_attribute_value("Destination", "192.168.2.64")
        r.set_attribute_value("NetPrefix", 26)
        r.set_attribute_value("NextHop", "192.168.2.80")

        for wn in hs_nodes:
            r = wn.add_route()
            r.set_attribute_value("Destination", "192.168.2.0")
            r.set_attribute_value("NetPrefix", 26)
            r.set_attribute_value("NextHop", "192.168.2.66")

        r = hs_ap.add_route()
        r.set_attribute_value("Destination", "192.168.2.0")
        r.set_attribute_value("NetPrefix", 26)
        r.set_attribute_value("NextHop", "192.168.2.65")
        
        r = pl2.add_route()
        r.set_attribute_value("Destination", "192.168.2.0")
        r.set_attribute_value("NetPrefix", 26)
        r.set_attribute_value("NextHop", "192.168.2.1")

        r = pl1.add_route()
        r.set_attribute_value("Destination", "192.168.2.0")
        r.set_attribute_value("NetPrefix", 26)
        r.set_attribute_value("NextHop", "192.168.2.20")

        # Add pinger app inside the mesh
        hs_node_ifs[0].set_attribute_value("label", "hotspot_node_1if")
        mesh_node_ifs[0].set_attribute_value("label", "mesh_node_1if")
        ping = mesh_ns.create("ns3::V4Ping")
        ping.set_attribute_value("Remote", "192.168.2.67") #"{#[hotspot_node_1if].addr[0].[Address]#}")
        ping.set_attribute_value("StartTime", "0s")
        ping.set_attribute_value("StopTime", "10s")
        ping.connector("node").connect(mesh_aps[0].connector("apps"))

        xml = exp.to_xml()
        
        print xml

        try:
            controller = ExperimentController(xml, self.root_dir)
            controller.start()
            
            while not controller.is_finished(ping.guid):
                time.sleep(0.5)
            
            taptrace = controller.trace(pl.guid, pl1tap.guid, "packets")
                
        finally:
            controller.stop()
            controller.shutdown()
        
        print "Pakcets at router:"
        print taptrace

    def clean(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    example = Roads09Ns3PLExample()
    example.run()
    example.clean()

