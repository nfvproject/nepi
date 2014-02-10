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


#
# Network topology
#
#       n0    n1   n2   n3
#       |     |    |    |
#       -----------------
#
#  node n0 sends IGMP traffic to node n3


from nepi.execution.ec import ExperimentController 

import os
import time
import unittest

class LinuxNS3ClientTest(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        #self.fedora_host = "peeramide.irisa.fr"
        self.fedora_user = "inria_test"

    def test_simple_ping(self):
        ec = ExperimentController(exp_id = "test-ns3-ping")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "nsLog", "V4Ping:Node")
        ec.register_connection(simu, node)

        nsnode1 = ec.register_resource("ns3::Node")
        ec.register_connection(nsnode1, simu)

        ipv41 = ec.register_resource("ns3::Ipv4L3Protocol")
        ec.register_connection(nsnode1, ipv41)

        arp1 = ec.register_resource("ns3::ArpL3Protocol")
        ec.register_connection(nsnode1, arp1)
        
        icmp1 = ec.register_resource("ns3::Icmpv4L4Protocol")
        ec.register_connection(nsnode1, icmp1)

        p1 = ec.register_resource("ns3::PointToPointNetDevice")
        ec.set(p1, "ip", "10.0.0.1")
        ec.set(p1, "prefix", "30")
        ec.register_connection(nsnode1, p1)
        q1 = ec.register_resource("ns3::DropTailQueue")
        ec.register_connection(p1, q1)

        nsnode2 = ec.register_resource("ns3::Node")
        ec.register_connection(nsnode2, simu)

        ipv42 = ec.register_resource("ns3::Ipv4L3Protocol")
        ec.register_connection(nsnode2, ipv42)

        arp2 = ec.register_resource("ns3::ArpL3Protocol")
        ec.register_connection(nsnode2, arp2)
        
        icmp2 = ec.register_resource("ns3::Icmpv4L4Protocol")
        ec.register_connection(nsnode2, icmp2)

        p2 = ec.register_resource("ns3::PointToPointNetDevice")
        ec.set(p2, "ip", "10.0.0.2")
        ec.set(p2, "prefix", "30")
        ec.register_connection(nsnode2, p2)
        q2 = ec.register_resource("ns3::DropTailQueue")
        ec.register_connection(p2, q2)

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, p1)
        ec.register_connection(chan, p2)

        ### create pinger
        ping = ec.register_resource("ns3::V4Ping")
        ec.set (ping, "Remote", "10.0.0.2")
        ec.set (ping, "Interval", "1s")
        ec.set (ping, "Verbose", True)
        ec.set (ping, "StartTime", "0s")
        ec.set (ping, "StopTime", "20s")
        ec.register_connection(ping, nsnode1)

        ec.deploy()

        ec.wait_finished([ping])
        
        stdout = ec.trace(simu, "stdout") 

        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

    def test_real_time(self):
        ec = ExperimentController(exp_id = "test-ns3-real-time")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "simulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ec.set(simu, "checksumEnabled", True)
        ec.register_connection(simu, node)

        nsnode1 = ec.register_resource("ns3::Node")
        ec.register_connection(nsnode1, simu)

        ipv41 = ec.register_resource("ns3::Ipv4L3Protocol")
        ec.register_connection(nsnode1, ipv41)

        arp1 = ec.register_resource("ns3::ArpL3Protocol")
        ec.register_connection(nsnode1, arp1)
        
        icmp1 = ec.register_resource("ns3::Icmpv4L4Protocol")
        ec.register_connection(nsnode1, icmp1)

        p1 = ec.register_resource("ns3::PointToPointNetDevice")
        ec.set(p1, "ip", "10.0.0.1")
        ec.set(p1, "prefix", "30")
        ec.register_connection(nsnode1, p1)
        q1 = ec.register_resource("ns3::DropTailQueue")
        ec.register_connection(p1, q1)

        nsnode2 = ec.register_resource("ns3::Node")
        ec.register_connection(nsnode2, simu)

        ipv42 = ec.register_resource("ns3::Ipv4L3Protocol")
        ec.register_connection(nsnode2, ipv42)

        arp2 = ec.register_resource("ns3::ArpL3Protocol")
        ec.register_connection(nsnode2, arp2)
        
        icmp2 = ec.register_resource("ns3::Icmpv4L4Protocol")
        ec.register_connection(nsnode2, icmp2)

        p2 = ec.register_resource("ns3::PointToPointNetDevice")
        ec.set(p2, "ip", "10.0.0.2")
        ec.set(p2, "prefix", "30")
        ec.register_connection(nsnode2, p2)
        q2 = ec.register_resource("ns3::DropTailQueue")
        ec.register_connection(p2, q2)

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, p1)
        ec.register_connection(chan, p2)

        ### create pinger
        ping = ec.register_resource("ns3::V4Ping")
        ec.set (ping, "Remote", "10.0.0.2")
        ec.set (ping, "Interval", "1s")
        ec.set (ping, "Verbose", True)
        ec.set (ping, "StartTime", "0s")
        ec.set (ping, "StopTime", "20s")
        ec.register_connection(ping, nsnode1)

        ec.deploy()

        ec.wait_finished([ping])
       
        stdout = ec.trace(simu, "stdout") 

        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)

        rm = ec.get_resource(ping)
        start_time = rm.start_time
        stop_time = rm.stop_time
        delta =  stop_time - start_time

        self.assertTrue(delta.seconds >= 20)
        self.assertTrue(delta.seconds < 25)

        ec.shutdown()

if __name__ == '__main__':
    unittest.main()

