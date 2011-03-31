#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util.constants import STATUS_FINISHED
from nepi.testbeds import ns3
import os
import shutil
import tempfile
import test_util
import time
import unittest

class Ns3ExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    @test_util.skipUnless(test_util.ns3_usable(), 
           "Test requires working ns-3 bindings")
    def test_run_ping_if(self):
        testbed_version = "3_9_RC3"
        instance = ns3.TestbedInstance(testbed_version)
        instance.configure("homeDirectory", self.root_dir)
        instance.create(2, "ns3::Node")
        instance.create(3, "ns3::Ipv4L3Protocol")
        instance.create(4, "ns3::ArpL3Protocol")
        instance.create(5, "ns3::Icmpv4L4Protocol")
        instance.create(6, "ns3::UdpL4Protocol")
        instance.connect(2, "protos", 3, "node")
        instance.connect(2, "protos", 4, "node")
        instance.connect(2, "protos", 5, "node")
        instance.connect(2, "protos", 6, "node")
        instance.create(7, "ns3::PointToPointNetDevice")
        instance.create(8, "ns3::DropTailQueue")
        instance.connect(2, "devs", 7, "node")
        instance.connect(7, "queue", 8, "dev")
        instance.add_trace(7, "P2PPcapTrace")
        instance.add_address(7, "10.0.0.1", 24, None)

        instance.create(9, "ns3::Node")
        instance.create(10, "ns3::Ipv4L3Protocol")
        instance.create(11, "ns3::ArpL3Protocol")
        instance.create(12, "ns3::Icmpv4L4Protocol")
        instance.create(13, "ns3::UdpL4Protocol")
        instance.connect(9, "protos", 10, "node")
        instance.connect(9, "protos", 11, "node")
        instance.connect(9, "protos", 12, "node")
        instance.connect(9, "protos", 13, "node")
        instance.create(14, "ns3::PointToPointNetDevice")
        instance.create(15, "ns3::DropTailQueue")
        instance.connect(9, "devs", 14, "node")
        instance.connect(14, "queue", 15, "dev")
        instance.add_trace(14, "P2PPcapTrace")
        instance.add_address(14, "10.0.0.2", 24, None)

        instance.create(16, "ns3::PointToPointChannel")
        instance.connect(7, "chan", 16, "dev2")
        instance.connect(14, "chan", 16, "dev2")

        instance.create(17, "ns3::V4Ping")
        instance.create_set(17, "Remote", "10.0.0.2")
        instance.create_set(17, "StartTime", "0s")
        instance.create_set(17, "StopTime", "10s")
        instance.create_set(17, "Verbose", True)
        instance.connect(17, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_configure()
        instance.start()
        while instance.status(17) != STATUS_FINISHED:
            time.sleep(0.1)
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        #self.assertTrue(ping_result.startswith(comp_result))
        instance.stop()
        instance.shutdown()

    @test_util.skipUnless(test_util.ns3_usable(),
            "Test requires working ns-3 bindings")
    def test_run_ping_routing(self):
        testbed_version = "3_9_RC3"
        instance = ns3.TestbedInstance(testbed_version)
        instance.configure("homeDirectory", self.root_dir)
        instance.create(2, "ns3::Node")
        instance.create(3, "ns3::Ipv4L3Protocol")
        instance.create(4, "ns3::ArpL3Protocol")
        instance.create(5, "ns3::Icmpv4L4Protocol")
        instance.create(6, "ns3::UdpL4Protocol")
        instance.connect(2, "protos", 3, "node")
        instance.connect(2, "protos", 4, "node")
        instance.connect(2, "protos", 5, "node")
        instance.connect(2, "protos", 6, "node")
        instance.create(7, "ns3::PointToPointNetDevice")
        instance.create(8, "ns3::DropTailQueue")
        instance.connect(2, "devs", 7, "node")
        instance.connect(7, "queue", 8, "dev")
        instance.add_trace(7, "P2PPcapTrace")
        instance.add_address(7, "10.0.0.1", 24, None)

        instance.create(9, "ns3::Node")
        instance.create(10, "ns3::Ipv4L3Protocol")
        instance.create(11, "ns3::ArpL3Protocol")
        instance.create(12, "ns3::Icmpv4L4Protocol")
        instance.create(13, "ns3::UdpL4Protocol")
        instance.connect(9, "protos", 10, "node")
        instance.connect(9, "protos", 11, "node")
        instance.connect(9, "protos", 12, "node")
        instance.connect(9, "protos", 13, "node")
        instance.create(14, "ns3::PointToPointNetDevice")
        instance.create(15, "ns3::DropTailQueue")
        instance.connect(9, "devs", 14, "node")
        instance.connect(14, "queue", 15, "dev")
        instance.add_trace(14, "P2PPcapTrace")
        instance.add_address(14, "10.0.0.2", 24, None)

        instance.create(16, "ns3::PointToPointChannel")
        instance.connect(7, "chan", 16, "dev2")
        instance.connect(14, "chan", 16, "dev2")

        instance.create(17, "ns3::PointToPointNetDevice")
        instance.create(18, "ns3::DropTailQueue")
        instance.connect(9, "devs", 17, "node")
        instance.connect(17, "queue", 18, "dev")
        instance.add_trace(17, "P2PPcapTrace")
        instance.add_address(17, "10.0.1.1", 24, None)

        instance.create(19, "ns3::Node")
        instance.create(20, "ns3::Ipv4L3Protocol")
        instance.create(21, "ns3::ArpL3Protocol")
        instance.create(22, "ns3::Icmpv4L4Protocol")
        instance.create(23, "ns3::UdpL4Protocol")
        instance.connect(19, "protos", 20, "node")
        instance.connect(19, "protos", 21, "node")
        instance.connect(19, "protos", 22, "node")
        instance.connect(19, "protos", 23, "node")
        instance.create(24, "ns3::PointToPointNetDevice")
        instance.create(25, "ns3::DropTailQueue")
        instance.connect(19, "devs", 24, "node")
        instance.connect(24, "queue", 25, "dev")
        instance.add_trace(24, "P2PPcapTrace")
        instance.add_address(24, "10.0.1.2", 24, None)

        instance.create(26, "ns3::PointToPointChannel")
        instance.connect(17, "chan", 26, "dev2")
        instance.connect(24, "chan", 26, "dev2")

        instance.create(27, "ns3::V4Ping")
        instance.create_set(27, "Remote", "10.0.1.2")
        instance.create_set(27, "StartTime", "0s")
        instance.create_set(27, "StopTime", "10s")
        instance.create_set(27, "Verbose", True)
        instance.connect(27, "node", 2, "apps")

        instance.add_route(2, "10.0.1.0", 24, "10.0.0.2")
        instance.add_route(19, "10.0.0.0", 24, "10.0.1.1")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_configure()
        instance.start()
        while instance.status(27) != STATUS_FINISHED:
            time.sleep(0.1)
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        #self.assertTrue(ping_result.startswith(comp_result))
        instance.stop()
        instance.shutdown()

    def tearDown(self):
        #shutil.rmtree(self.root_dir)
        pass

if __name__ == '__main__':
    unittest.main()

