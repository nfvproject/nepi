#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
import os
import shutil
import test_util
import unittest
import uuid

class Ns3DesignTestCase(unittest.TestCase):
    def test_design_if(self):
        testbed_id = "ns3"
        exp_desc = ExperimentDescription()
        provider = FactoriesProvider(testbed_id)
        tstbd_desc = exp_desc.add_testbed_description(provider)

        node1 = tstbd_desc.create("ns3::Node")
        ipv41 = tstbd_desc.create("ns3::Ipv4L3Protocol")
        arp1  = tstbd_desc.create("ns3::ArpL3Protocol")
        icmp1 = tstbd_desc.create("ns3::Icmpv4L4Protocol")
        udp1 = tstbd_desc.create("ns3::UdpL4Protocol")
        node1.connector("protos").connect(ipv41.connector("node"))
        node1.connector("protos").connect(arp1.connector("node"))
        node1.connector("protos").connect(icmp1.connector("node"))
        node1.connector("protos").connect(udp1.connector("node"))
        iface1 = tstbd_desc.create("ns3::PointToPointNetDevice")
        queue1 = tstbd_desc.create("ns3::DropTailQueue")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("queue").connect(queue1.connector("dev"))
        trace1 = iface1.enable_trace("P2PPcapTrace")
        ip1 = iface1.add_address()
        ip1.set_attribute_value("Address", "10.0.0.1")

        node2 = tstbd_desc.create("ns3::Node")
        ipv42 = tstbd_desc.create("ns3::Ipv4L3Protocol")
        arp2  = tstbd_desc.create("ns3::ArpL3Protocol")
        icmp2 = tstbd_desc.create("ns3::Icmpv4L4Protocol")
        udp2 = tstbd_desc.create("ns3::UdpL4Protocol")
        node2.connector("protos").connect(ipv42.connector("node"))
        node2.connector("protos").connect(arp2.connector("node"))
        node2.connector("protos").connect(icmp2.connector("node"))
        node2.connector("protos").connect(udp2.connector("node"))
        iface2 = tstbd_desc.create("ns3::PointToPointNetDevice")
        queue2 = tstbd_desc.create("ns3::DropTailQueue")
        node2.connector("devs").connect(iface2.connector("node"))
        iface2.connector("queue").connect(queue2.connector("dev"))
        trace2 = iface2.enable_trace("P2PPcapTrace")
        ip2 = iface2.add_address()
        ip2.set_attribute_value("Address", "10.0.0.2")

        chan = tstbd_desc.create("ns3::PointToPointChannel")
        iface1.connector("chan").connect(chan.connector("dev2"))
        iface2.connector("chan").connect(chan.connector("dev2"))

        app = tstbd_desc.create("ns3::V4Ping")
        app.set_attribute_value("Remote", "10.0.0.2")
        app.set_attribute_value("StartTime", "0s")
        app.set_attribute_value("StopTime", "20s")
        app.set_attribute_value("Verbose", False)
        app.connector("node").connect(node1.connector("apps"))

        xml = exp_desc.to_xml()
        exp_desc2 = ExperimentDescription()
        exp_desc2.from_xml(xml)
        xml2 = exp_desc2.to_xml()
        self.assertTrue(xml == xml2)
        
if __name__ == '__main__':
    unittest.main()

