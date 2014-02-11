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
from nepi.execution.trace import TraceAttr

import os
import time
import unittest

def add_ns3_node(ec, simu):
    ns3_node = ec.register_resource("ns3::Node")
    ec.register_connection(ns3_node, simu)

    ipv4 = ec.register_resource("ns3::Ipv4L3Protocol")
    ec.register_connection(ns3_node, ipv4)

    arp = ec.register_resource("ns3::ArpL3Protocol")
    ec.register_connection(ns3_node, arp)
    
    icmp = ec.register_resource("ns3::Icmpv4L4Protocol")
    ec.register_connection(ns3_node, icmp)

    return ns3_node

def add_point2point_device(ec, ns3_node, address, prefix):
    dev = ec.register_resource("ns3::PointToPointNetDevice")
    ec.set(dev, "ip", address)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(ns3_node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

class LinuxNS3ClientTest(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
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

        nsnode1 = add_ns3_node(ec, simu)
        p1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        p2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")

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

        nsnode1 = add_ns3_node(ec, simu)
        p1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        p2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")

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

    def test_p2p_traces(self):
        ec = ExperimentController(exp_id = "test-ns3-p2p-traces")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "nsLog", "V4Ping:Node")
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        p1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        p2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")

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

        # enable traces
        ec.enable_trace(p1, "pcap")
        ec.enable_trace(p1, "promiscPcap")
        ec.enable_trace(p1, "ascii")

        ec.enable_trace(p2, "pcap")
        ec.enable_trace(p2, "promiscPcap")
        ec.enable_trace(p2, "ascii")

        ec.deploy()

        ec.wait_finished([ping])

        # Trace verification
        rm_simu = ec.get_resource(simu)

        # TODO: Fix this in ns-3: pcap traces do not flush until the Simulator 
        #   process is ended, so we can't get the traces of the 'pcap' and
        #   'promiscPcap' traces.
        #
        #for trace in ["pcap", "promiscPcap", "ascii"]:
        for trace in ["ascii"]:
            for guid in [p1, p2]:
                output = ec.trace(guid, trace)

                size = ec.trace(guid, trace, attr = TraceAttr.SIZE)
                self.assertEquals(size, len(output))
                self.assertTrue(size > 100)
                
                block = ec.trace(guid, trace, attr = TraceAttr.STREAM, block = 5, offset = 1)
                self.assertEquals(block, output[5:10])

                trace_path = ec.trace(guid, trace, attr = TraceAttr.PATH)
                rm = ec.get_resource(guid)
                path = os.path.join(rm_simu.run_home, rm._trace_filename.get(trace))
                self.assertEquals(trace_path, path)

        ec.shutdown()

if __name__ == '__main__':
    unittest.main()

