#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>


# Test based on ns-3 csma/examples/csma-ping.cc file
#
# Network topology
#
#       n0    n1   n2   n3
#       |     |    |    |
#       -----------------
#
#  node n0 sends IGMP traffic to node n3


from nepi.resources.ns3.ns3server import run_server
from nepi.resources.linux.ns3.ns3client import LinuxNS3Client

import os
import threading
import time
import unittest

class LinuxNS3ClientTest(unittest.TestCase):
    def setUp(self):
        self.socket_name = os.path.join("/", "tmp", "NS3WrapperServer.sock")

    def tearDown(self):
        os.remove(self.socket_name) 

    def test_runtime_attr_modify(self):
        thread = threading.Thread(target = run_server,
                args = [self.socket_name])

        thread.setDaemon(True)
        thread.start()

        time.sleep(3)

        # Verify that the communication socket was created
        self.assertTrue(os.path.exists(self.socket_name))

        # Instantiate the NS3 client
        client = LinuxNS3Client(self.socket_name)
 
        # Define a real time simulation 
        stype = client.create("StringValue", "ns3::RealtimeSimulatorImpl")
        client.invoke("singleton::GlobalValue", "Bind", "SimulatorImplementationType", stype)
        btrue = client.create("BooleanValue", True)
        client.invoke("singleton::GlobalValue", "Bind", "ChecksumEnabled", btrue)
        
        # Create Node
        n1 = client.create("Node")
        self.assertTrue(n1.startswith("uuid"))

        ## Install internet stack
        ipv41 = client.create("Ipv4L3Protocol")
        client.invoke(n1, "AggregateObject", ipv41)

        arp1 = client.create("ArpL3Protocol")
        client.invoke(n1, "AggregateObject", arp1)
        
        icmp1 = client.create("Icmpv4L4Protocol")
        client.invoke(n1, "AggregateObject", icmp1)

        ## Add IPv4 routing
        lr1 = client.create("Ipv4ListRouting")
        client.invoke(ipv41, "SetRoutingProtocol", lr1)
        sr1 = client.create("Ipv4StaticRouting")
        client.invoke(lr1, "AddRoutingProtocol", sr1, 1)

        ## NODE 2
        n2 = client.create("Node")

        ## Install internet stack
        ipv42 = client.create("Ipv4L3Protocol")
        client.invoke(n2, "AggregateObject", ipv42)

        arp2 = client.create("ArpL3Protocol")
        client.invoke(n2, "AggregateObject", arp2)
        
        icmp2 = client.create("Icmpv4L4Protocol")
        client.invoke(n2, "AggregateObject", icmp2)

        ## Add IPv4 routing
        lr2 = client.create("Ipv4ListRouting")
        client.invoke(ipv42, "SetRoutingProtocol", lr2)
        sr2 = client.create("Ipv4StaticRouting")
        client.invoke(lr2, "AddRoutingProtocol", sr2, 1)

        ##### Create p2p device and enable ascii tracing
        p2pHelper = client.create("PointToPointHelper")
        asciiHelper = client.create("AsciiTraceHelper")

        # Iface for node1
        p1 = client.create("PointToPointNetDevice")
        client.invoke(n1, "AddDevice", p1)
        q1 = client.create("DropTailQueue")
        client.invoke(p1, "SetQueue", q1)
      
        # Add IPv4 address
        ifindex1 = client.invoke(ipv41, "AddInterface", p1)
        mask1 = client.create("Ipv4Mask", "/30")
        addr1 = client.create("Ipv4Address", "10.0.0.1")
        inaddr1 = client.create("Ipv4InterfaceAddress", addr1, mask1)
        client.invoke(ipv41, "AddAddress", ifindex1, inaddr1)
        client.invoke(ipv41, "SetMetric", ifindex1, 1)
        client.invoke(ipv41, "SetUp", ifindex1)

        # Enable collection of Ascii format to a specific file
        filepath1 = "trace-p2p-1.tr"
        stream1 = client.invoke(asciiHelper, "CreateFileStream", filepath1)
        client.invoke(p2pHelper, "EnableAscii", stream1, p1)
       
        # Iface for node2
        p2 = client.create("PointToPointNetDevice")
        client.invoke(n2, "AddDevice", p2)
        q2 = client.create("DropTailQueue")
        client.invoke(p2, "SetQueue", q2)

        # Add IPv4 address
        ifindex2 = client.invoke(ipv42, "AddInterface", p2)
        mask2 = client.create("Ipv4Mask", "/30")
        addr2 = client.create("Ipv4Address", "10.0.0.2")
        inaddr2 = client.create("Ipv4InterfaceAddress", addr2, mask2)
        client.invoke(ipv42, "AddAddress", ifindex2, inaddr2)
        client.invoke(ipv42, "SetMetric", ifindex2, 1)
        client.invoke(ipv42, "SetUp", ifindex2)

        # Enable collection of Ascii format to a specific file
        filepath2 = "trace-p2p-2.tr"
        stream2 = client.invoke(asciiHelper, "CreateFileStream", filepath2)
        client.invoke(p2pHelper, "EnableAscii", stream2, p2)

        # Create channel
        chan = client.create("PointToPointChannel")
        client.set(chan, "Delay", "0s")
        client.invoke(p1, "Attach", chan)
        client.invoke(p2, "Attach", chan)

        ### create pinger
        ping = client.create("V4Ping")
        client.invoke(n1, "AddApplication", ping)
        client.set (ping, "Remote", "10.0.0.2")
        client.set (ping, "Interval", "1s")
        client.set (ping, "Verbose", True)
        client.set (ping, "StartTime", "0s")
        client.set (ping, "StopTime", "20s")

        ### run Simulation
        client.stop(time = "21s")
        client.start()

        time.sleep(1)

        client.set(chan, "Delay", "5s")

        time.sleep(5)

        client.set(chan, "Delay", "0s")

        # wait until simulation is over
        client.shutdown()


if __name__ == '__main__':
    unittest.main()

