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

# The reason execute tests are run in separate scripts for ns3, is that the 
# same ns3 Simulator will be loaded only once per process, resulting in a 
# dirty state of the Simulator after the first test is executed.
# As it is not possible to reset the state of the Simulator to the original
# one, different tests should be executed in different processes (different 
# unittest instance)
class Ns3ExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    @test_util.skipUnless(test_util.ns3_usable(),
            "Test requires working ns-3 bindings")
    def test_run_ping_routing(self):
        testbed_version = "3_9_RC3"
        instance = ns3.TestbedController(testbed_version)
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_create(2, "ns3::Node")
        instance.defer_create(3, "ns3::Ipv4L3Protocol")
        instance.defer_create(4, "ns3::ArpL3Protocol")
        instance.defer_create(5, "ns3::Icmpv4L4Protocol")
        instance.defer_create(6, "ns3::UdpL4Protocol")
        instance.defer_connect(2, "protos", 3, "node")
        instance.defer_connect(2, "protos", 4, "node")
        instance.defer_connect(2, "protos", 5, "node")
        instance.defer_connect(2, "protos", 6, "node")
        instance.defer_create(7, "ns3::PointToPointNetDevice")
        instance.defer_create(8, "ns3::DropTailQueue")
        instance.defer_connect(2, "devs", 7, "node")
        instance.defer_connect(7, "queue", 8, "dev")
        instance.defer_add_trace(7, "P2PAsciiTrace")
        instance.defer_add_address(7, "10.0.0.1", 24, None)

        instance.defer_create(9, "ns3::Node")
        instance.defer_create(10, "ns3::Ipv4L3Protocol")
        instance.defer_create(11, "ns3::ArpL3Protocol")
        instance.defer_create(12, "ns3::Icmpv4L4Protocol")
        instance.defer_create(13, "ns3::UdpL4Protocol")
        instance.defer_connect(9, "protos", 10, "node")
        instance.defer_connect(9, "protos", 11, "node")
        instance.defer_connect(9, "protos", 12, "node")
        instance.defer_connect(9, "protos", 13, "node")
        instance.defer_create(14, "ns3::PointToPointNetDevice")
        instance.defer_create(15, "ns3::DropTailQueue")
        instance.defer_connect(9, "devs", 14, "node")
        instance.defer_connect(14, "queue", 15, "dev")
        instance.defer_add_trace(14, "P2PAsciiTrace")
        instance.defer_add_address(14, "10.0.0.2", 24, None)

        instance.defer_create(16, "ns3::PointToPointChannel")
        instance.defer_connect(7, "chan", 16, "dev2")
        instance.defer_connect(14, "chan", 16, "dev2")

        instance.defer_create(17, "ns3::PointToPointNetDevice")
        instance.defer_create(18, "ns3::DropTailQueue")
        instance.defer_connect(9, "devs", 17, "node")
        instance.defer_connect(17, "queue", 18, "dev")
        instance.defer_add_trace(17, "P2PAsciiTrace")
        instance.defer_add_address(17, "10.0.1.1", 24, None)

        instance.defer_create(19, "ns3::Node")
        instance.defer_create(20, "ns3::Ipv4L3Protocol")
        instance.defer_create(21, "ns3::ArpL3Protocol")
        instance.defer_create(22, "ns3::Icmpv4L4Protocol")
        instance.defer_create(23, "ns3::UdpL4Protocol")
        instance.defer_connect(19, "protos", 20, "node")
        instance.defer_connect(19, "protos", 21, "node")
        instance.defer_connect(19, "protos", 22, "node")
        instance.defer_connect(19, "protos", 23, "node")
        instance.defer_create(24, "ns3::PointToPointNetDevice")
        instance.defer_create(25, "ns3::DropTailQueue")
        instance.defer_connect(19, "devs", 24, "node")
        instance.defer_connect(24, "queue", 25, "dev")
        instance.defer_add_trace(24, "P2PAsciiTrace")
        instance.defer_add_address(24, "10.0.1.2", 24, None)

        instance.defer_create(26, "ns3::PointToPointChannel")
        instance.defer_connect(17, "chan", 26, "dev2")
        instance.defer_connect(24, "chan", 26, "dev2")

        instance.defer_create(27, "ns3::V4Ping")
        instance.defer_create_set(27, "Remote", "10.0.1.2")
        instance.defer_create_set(27, "StartTime", "0s")
        instance.defer_create_set(27, "StopTime", "10s")
        instance.defer_connect(27, "node", 2, "apps")

        instance.defer_add_route(2, "10.0.1.0", 24, "10.0.0.2")
        instance.defer_add_route(19, "10.0.0.0", 24, "10.0.1.1")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        instance.start()
        while instance.status(27) != STATUS_FINISHED:
            time.sleep(0.1)
        ping_result = instance.trace(24, "P2PAsciiTrace")
        comp_result = "- 9.04199 /NodeList/2/DeviceList/0/$ns3::PointToPointNetDevice/TxQueue/Dequeue ns3::PppHeader (Point-to-Point Protocol: IP (0x0021)) ns3::Ipv4Header (tos 0x0 ttl 64 id 9 protocol 1 offset 0 flags [none] length: 84 10.0.1.2 > 10.0.0.1) ns3::Icmpv4Header (type=0, code=0) ns3::Icmpv4Echo (identifier=0, sequence=9)"
        self.assertNotEqual(ping_result.find(comp_result), -1)
        instance.stop()
        instance.shutdown()

    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

