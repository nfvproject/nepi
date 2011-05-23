#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from optparse import OptionParser, SUPPRESS_HELP
from nepi.util import proxy
import os
import shutil
import tempfile
import test_util
import time

class Roads09Example(object):
    def __init__(self):
        self.root_dir = tempfile.mkdtemp()

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

    def add_ip_address(self, iface, address):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)

    def run(self):
        exp_desc = ExperimentDescription()

        testbed_version = "3_9_RC3"
        testbed_id = "ns3"
        ns3_provider = FactoriesProvider(testbed_id, testbed_version)
        ns3_desc = exp_desc.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("homeDirectory", self.root_dir)
        ns3_desc.set_attribute_value("StopTime", "8.1s")

        node1 = self.add_ns3_node(ns3_desc)
        node2 = self.add_ns3_node(ns3_desc)
        node3 = self.add_ns3_node(ns3_desc)

        channel = ns3_desc.create("ns3::SimpleOfdmWimaxChannel")

        ss1 = self.add_ns3_wimax_ss(ns3_desc, node1, channel)
        ss2 = self.add_ns3_wimax_ss(ns3_desc, node2, channel)
        bs = self.add_ns3_wimax_bs(ns3_desc, node3, channel)

        self.add_ns3_service_flow(ns3_desc, ss1, "0.0.0.0", "0.0.0.0",
                "10.1.1.1", "255.255.255.255", 0, 65000, 100, 100, 
                "UdpL4Protocol", 1, "SF_DIRECTION_DOWN", "SF_TYPE_RTPS")
        self.add_ns3_service_flow(ns3_desc, ss2, "10.1.1.2", "255.255.255.255",
                "0.0.0.0", "0.0.0.0", 0, 65000, 100, 100, "UdpL4Protocol",
                1, "SF_DIRECTION_UP", "SF_TYPE_RTPS")

        self.add_ip_address(ss1, "10.1.1.1")
        self.add_ip_address(ss2, "10.1.1.2")
        self.add_ip_address(bs, "10.1.1.3")

        udp_server = ns3_desc.create("ns3::UdpServer")
        udp_server.set_attribute_value("Port", 100)
        udp_server.set_attribute_value("StartTime", "6s")
        udp_server.set_attribute_value("StopTime", "8s")
        udp_server.connector("node").connect(node1.connector("apps"))

        udp_client = ns3_desc.create("ns3::UdpClient")
        udp_client.set_attribute_value("RemotePort", 100)
        udp_client.set_attribute_value("RemoteAddress", "10.1.1.1")
        udp_client.set_attribute_value("MaxPackets", 1200)
        udp_client.set_attribute_value("Interval", "0.5s")
        udp_client.set_attribute_value("PacketSize", 1024)
        udp_client.set_attribute_value("StartTime", "6s")
        udp_client.set_attribute_value("StopTime", "8s")
        udp_client.connector("node").connect(node2.connector("apps"))

        xml = exp_desc.to_xml()
        controller = ExperimentController(xml, self.root_dir)
        controller.start()
        while not (controller.is_finished(udp_server.guid) and controller.is_finished(udp_client.guid)):
            time.sleep(0.5)
        time.sleep(0.1)
        controller.stop()
        controller.shutdown()

    def clean(self):
        #shutil.rmtree(self.root_dir)
        pass

if __name__ == '__main__':
    example = Roads09Example()
    example.run()
    example.clean()

