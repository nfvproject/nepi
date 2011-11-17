#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from optparse import OptionParser, SUPPRESS_HELP
from nepi.util.constants import DeploymentConfiguration as DC
import os
import shutil
import tempfile
import time

class WimaxOverlayExample(object):
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
        self.user = os.getlogin()
        #self.movie =  options.movie
        self.root_dir = tempfile.mkdtemp()

    def add_ns3_node(self, ns3_desc):
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
        return node

    def add_ns3_wimax_bs(self, ns3_desc, node, channel):
        bs = ns3_desc.create("ns3::BaseStationNetDevice")
        node.connector("devs").connect(bs.connector("node"))
        bs.connector("chan").connect(channel.connector("devs"))
        phy = ns3_desc.create("ns3::SimpleOfdmWimaxPhy")
        bs.connector("phy").connect(phy.connector("dev"))
        uplink = ns3_desc.create("ns3::UplinkSchedulerSimple")
        bs.connector("uplnk").connect(uplink.connector("dev"))
        bssched = ns3_desc.create("ns3::BSSchedulerSimple")
        bs.connector("dwnlnk").connect(bssched.connector("dev"))
        bs.enable_trace("WimaxPcapTrace")
        bs.enable_trace("WimaxAsciiTrace")
        return bs

    def add_ns3_wimax_ss(self, ns3_desc, node, channel):
        ss = ns3_desc.create("ns3::SubscriberStationNetDevice")
        node.connector("devs").connect(ss.connector("node"))
        ss.connector("chan").connect(channel.connector("devs"))
        phy = ns3_desc.create("ns3::SimpleOfdmWimaxPhy")
        ss.connector("phy").connect(phy.connector("dev"))
        ss.enable_trace("WimaxPcapTrace")
        ss.enable_trace("WimaxAsciiTrace")
        return ss

    def add_ns3_p2p(self, ns3_desc, node, channel):
        iface = ns3_desc.create("ns3::PointToPointNetDevice")
        queue = ns3_desc.create("ns3::DropTailQueue")
        node.connector("devs").connect(iface.connector("node"))
        iface.connector("queue").connect(queue.connector("dev"))
        trace = iface.enable_trace("P2PAsciiTrace")
        iface.connector("chan").connect(channel.connector("dev2"))
        return iface

    def add_ns3_service_flow(self, ns3_desc, ss, src_address, src_mask,
            dst_address, dst_mask, src_portlow, src_porthigh, dst_portlow,
            dst_porthigh, protocol, priority, direction, scheduling_type):
        classifier = ns3_desc.create("ns3::IpcsClassifierRecord")
        classifier.set_attribute_value("SrcAddress", src_address)
        classifier.set_attribute_value("SrcMask", src_mask)
        classifier.set_attribute_value("DstAddress", dst_address)
        classifier.set_attribute_value("DstMask", dst_mask)
        classifier.set_attribute_value("SrcPortLow", src_portlow)
        classifier.set_attribute_value("SrcPortHigh",src_porthigh)
        classifier.set_attribute_value("DstPortLow", dst_portlow)
        classifier.set_attribute_value("DstPortHigh", dst_porthigh)
        classifier.set_attribute_value("Protocol", protocol)
        classifier.set_attribute_value("Priority", priority)
        sflow = ns3_desc.create("ns3::ServiceFlow")
        sflow.set_attribute_value("Direction", direction)
        sflow.set_attribute_value("SchedulingType", scheduling_type)
        sflow.connector("classif").connect(classifier.connector("sflow"))
        ss.connector("sflows").connect(sflow.connector("dev"))

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
        base_addr = "192.168.4.%d"
        exp_desc = ExperimentDescription()

        # NS3
        ns3_provider = FactoriesProvider("ns3")
        ns3_desc = exp_desc.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("homeDirectory", self.root_dir)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)

        ## WIMAX network 32/27
        node_bs = self.add_ns3_node(ns3_desc)
        node_ss1 = self.add_ns3_node(ns3_desc)
        node_ss2 = self.add_ns3_node(ns3_desc)
        node_ss3 = self.add_ns3_node(ns3_desc)
        node_ss4 = self.add_ns3_node(ns3_desc)
        node_ss5 = self.add_ns3_node(ns3_desc)
        node_ss6 = self.add_ns3_node(ns3_desc)

        wimax_channel = ns3_desc.create("ns3::SimpleOfdmWimaxChannel")

        bs = self.add_ns3_wimax_bs(ns3_desc, node_bs, wimax_channel)
        ss1 = self.add_ns3_wimax_ss(ns3_desc, node_ss1, wimax_channel)
        ss2 = self.add_ns3_wimax_ss(ns3_desc, node_ss2, wimax_channel)
        ss3 = self.add_ns3_wimax_ss(ns3_desc, node_ss3, wimax_channel)
        ss4 = self.add_ns3_wimax_ss(ns3_desc, node_ss4, wimax_channel)
        ss5 = self.add_ns3_wimax_ss(ns3_desc, node_ss5, wimax_channel)
        ss6 = self.add_ns3_wimax_ss(ns3_desc, node_ss6, wimax_channel)

        self.add_ip_address(bs, (base_addr%33), 27)
        self.add_ip_address(ss1, (base_addr%34), 27)
        self.add_ip_address(ss2, (base_addr%35), 27)
        self.add_ip_address(ss3, (base_addr%36), 27)
        self.add_ip_address(ss4, (base_addr%37), 27)
        self.add_ip_address(ss5, (base_addr%38), 27)
        self.add_ip_address(ss6, (base_addr%39), 27)

        #self.add_ns3_service_flow(ns3_desc, ss1, "0.0.0.0", "0.0.0.0",
        #        "10.1.1.1", "255.255.255.255", 0, 65000, 100, 100, 
        #       "UdpL4Protocol", 1, "SF_DIRECTION_DOWN", "SF_TYPE_RTPS")
        #self.add_ns3_service_flow(ns3_desc, ss2, "10.1.1.2", "255.255.255.255",
        #        "0.0.0.0", "0.0.0.0", 0, 65000, 100, 100, "UdpL4Protocol",
        #        1, "SF_DIRECTION_UP", "SF_TYPE_RTPS")

        self.add_ns3_service_flow(ns3_desc, ss1, "0.0.0.0", "0.0.0.0",
                "192.168.4.35", "255.255.255.225", 0, 65000, 11, 11, "Icmpv4L4Protocol",
                1, "SF_DIRECTION_DOWN", "SF_TYPE_RTPS")

        self.add_ns3_service_flow(ns3_desc, ss2, "192.168.4.34", "255.255.255.255",
                "0.0.0.0", "0.0.0.0", 0, 65000, 11, 11, "Icmpv4L4Protocol",
                1, "SF_DIRECTION_UP", "SF_TYPE_RTPS")

        ## Point-to-Point wimax/fdnd 224/30
        node_fdnd = self.add_ns3_node(ns3_desc)
        p2p_channel = ns3_desc.create("ns3::PointToPointChannel")
        
        p2p1 = self.add_ns3_p2p(ns3_desc, node_ss1, p2p_channel)
        p2p2 = self.add_ns3_p2p(ns3_desc, node_fdnd, p2p_channel)

        self.add_ip_address(p2p1, (base_addr%225), 30)
        self.add_ip_address(p2p2, (base_addr%226), 30)

        # NETNS
        netns_provider = FactoriesProvider("netns")
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self.root_dir)
        netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        netns_root_dir = os.path.join(self.root_dir, "netns_instance")
        os.mkdir(netns_root_dir)
        netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
        netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        netns_desc.set_attribute_value(DC.USE_SUDO, True)

        node_netns = netns_desc.create("Node")
        node_netns.set_attribute_value("forward_X11", True)
        tap = self.add_netns_tap(netns_desc, node_netns)

        command = "xterm" 
        app = netns_desc.create("Application")
        app.set_attribute_value("command", command)
        app.set_attribute_value("user", self.user)
        app.connector("node").connect(node_netns.connector("apps"))

        ## Point-to-Point NS3::fdnd/NETNS::tap 228/30
        fdnd = self.add_ns3_fdnd(ns3_desc, node_fdnd)

        fdnd.connector("->fd").connect(tap.connector("fd->"))
 
        self.add_ip_address(fdnd, (base_addr%229), 30)
        self.add_ip_address(tap, (base_addr%230), 30)

        # ROUTES
        self.add_route(node_netns, (base_addr%32), 27, (base_addr%229))
        self.add_route(node_netns, (base_addr%224), 30, (base_addr%229))
        
        self.add_route(node_fdnd, (base_addr%32), 27, (base_addr%225))
        self.add_route(node_ss1, (base_addr%228), 30, (base_addr%226))

        self.add_route(node_ss2, (base_addr%224), 30, (base_addr%34))
        self.add_route(node_ss2, (base_addr%228), 30, (base_addr%34))
        self.add_route(node_bs, (base_addr%224), 30, (base_addr%34))
        self.add_route(node_bs, (base_addr%228), 30, (base_addr%34))


        xml = exp_desc.to_xml()
        controller = ExperimentController(xml, self.root_dir)
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        time.sleep(0.1)
        controller.stop()
        controller.shutdown()

    def clean(self):
        #shutil.rmtree(self.root_dir)
        print self.root_dir
        pass

if __name__ == '__main__':
    example = WimaxOverlayExample()
    example.run()
    example.clean()

