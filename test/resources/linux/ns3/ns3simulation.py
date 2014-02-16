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
    node = ec.register_resource("ns3::Node")
    ec.register_connection(node, simu)

    ipv4 = ec.register_resource("ns3::Ipv4L3Protocol")
    ec.register_connection(node, ipv4)

    arp = ec.register_resource("ns3::ArpL3Protocol")
    ec.register_connection(node, arp)
    
    icmp = ec.register_resource("ns3::Icmpv4L4Protocol")
    ec.register_connection(node, icmp)

    return node

def add_point2point_device(ec, node, address, prefix):
    dev = ec.register_resource("ns3::PointToPointNetDevice")
    ec.set(dev, "ip", address)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_csma_device(ec, node, address, prefix):
    dev = ec.register_resource("ns3::CsmaNetDevice")
    ec.set(dev, "ip", address)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_wifi_device(ec, node, address, prefix, 
        access_point = False):
    dev = ec.register_resource("ns3::WifiNetDevice")
    ec.set(dev, "ip", address)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    phy = ec.register_resource("ns3::YansWifiPhy")
    ec.set(phy, "Standard", "WIFI_PHY_STANDARD_80211a")
    ec.register_connection(dev, phy)

    error = ec.register_resource("ns3::NistErrorRateModel")
    ec.register_connection(phy, error)

    manager = ec.register_resource("ns3::ArfWifiManager")
    ec.register_connection(dev, manager)

    if access_point:
        mac = ec.register_resource("ns3::ApWifiMac")
    else:
        mac = ec.register_resource("ns3::StaWifiMac")

    ec.set(mac, "Standard", "WIFI_PHY_STANDARD_80211a")
    ec.register_connection(dev, mac)

    return dev, phy

def add_random_mobility(ec, node, x, y, z, speed, bounds_width, 
        bounds_height):
    position = "%d:%d:%d" % (x, y, z)
    bounds = "0|%d|0|%d" % (bounds_width, bounds_height) 
    speed = "ns3::UniformRandomVariable[Min=%d|Max=%s]" % (speed, speed)
    pause = "ns3::ConstantRandomVariable[Constant=1.0]"
    
    mobility = ec.register_resource("ns3::RandomDirection2dMobilityModel")
    ec.set(mobility, "Position", position)
    ec.set(mobility, "Bounds", bounds)
    ec.set(mobility, "Speed", speed)
    ec.set(mobility, "Pause",  pause)
    ec.register_connection(node, mobility)
    return mobility

def add_constant_mobility(ec, node, x, y, z):
    mobility = ec.register_resource("ns3::ConstantPositionMobilityModel") 
    position = "%d:%d:%d" % (x, y, z)
    ec.set(mobility, "Position", position)
    ec.register_connection(node, mobility)
    return mobility

def add_wifi_channel(ec):
    channel = ec.register_resource("ns3::YansWifiChannel")
    delay = ec.register_resource("ns3::ConstantSpeedPropagationDelayModel")
    ec.register_connection(channel, delay)

    loss  = ec.register_resource("ns3::LogDistancePropagationLossModel")
    ec.register_connection(channel, loss)

    return channel

class LinuxNS3ClientTest(unittest.TestCase):
    def setUp(self):
        #self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_host = "planetlabpc1.upf.edu"
        #self.fedora_host = "peeramide.irisa.fr"
        self.fedora_user = "inria_nepi"
        self.fedora_identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])

    def test_simple_p2p_ping(self):
        ec = ExperimentController(exp_id = "test-ns3-p2p-ping")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        dev2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, dev1)
        ec.register_connection(chan, dev2)

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

    def test_simple_cmsa_ping(self):
        ec = ExperimentController(exp_id = "test-ns3-csma-ping")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1 = add_csma_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        dev2 = add_csma_device(ec, nsnode2, "10.0.0.2", "30")

        # Create channel
        chan = ec.register_resource("ns3::CsmaChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, dev1)
        ec.register_connection(chan, dev2)

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

    def test_compile_local_source(self):
        ec = ExperimentController(exp_id = "test-ns3-local-source")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        sources = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                "ns-3.18-user.tar.gz")
        ec.set(simu, "sources", sources)
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1 = add_csma_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        dev2 = add_csma_device(ec, nsnode2, "10.0.0.2", "30")

        # Create channel
        chan = ec.register_resource("ns3::CsmaChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, dev1)
        ec.register_connection(chan, dev2)

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

    def test_compile_debug_mode(self):
        ec = ExperimentController(exp_id = "test-ns3-debug-mode")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "nsLog", "V4Ping:Node")
        ec.set(simu, "buildMode", "debug")
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1 = add_csma_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        dev2 = add_csma_device(ec, nsnode2, "10.0.0.2", "30")

        # Create channel
        chan = ec.register_resource("ns3::CsmaChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, dev1)
        ec.register_connection(chan, dev2)

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
        
        stderr = ec.trace(simu, "stderr")
        expected = "V4Ping:Read32"
        self.assertTrue(stderr.find(expected) > -1)

        ec.shutdown()

    def test_real_time(self):
        ec = ExperimentController(exp_id = "test-ns3-real-time")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "simulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ec.set(simu, "checksumEnabled", True)
        ec.set(simu, "verbose", True)
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        dev2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, dev1)
        ec.register_connection(chan, dev2)

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

    def test_dev2p_traces(self):
        ec = ExperimentController(exp_id = "test-ns3-dev2p-traces")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        dev2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "0s")
        ec.register_connection(chan, dev1)
        ec.register_connection(chan, dev2)

        ### create pinger
        ping = ec.register_resource("ns3::V4Ping")
        ec.set (ping, "Remote", "10.0.0.2")
        ec.set (ping, "Interval", "1s")
        ec.set (ping, "Verbose", True)
        ec.set (ping, "StartTime", "0s")
        ec.set (ping, "StopTime", "20s")
        ec.register_connection(ping, nsnode1)

        # enable traces
        ec.enable_trace(dev1, "pcap")
        ec.enable_trace(dev1, "promiscPcap")
        ec.enable_trace(dev1, "ascii")

        ec.enable_trace(dev2, "pcap")
        ec.enable_trace(dev2, "promiscPcap")
        ec.enable_trace(dev2, "ascii")

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
            for guid in [dev1, dev2]:
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

    def test_simple_wifi_ping(self):
        bounds_width = bounds_height = 200
        x = y = 100
        speed = 1

        ec = ExperimentController(exp_id = "test-ns3-wifi-ping")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        dev1, phy1 = add_wifi_device(ec, nsnode1, "10.0.0.1", "24", access_point = True)
        mobility1 = add_constant_mobility(ec, nsnode1, x, y, 0)

        nsnode2 = add_ns3_node(ec, simu)
        dev2, phy2 = add_wifi_device(ec, nsnode2, "10.0.0.2", "24", access_point = False)
        mobility1 = add_constant_mobility(ec, nsnode2, x, y, 0)
        #mobility2 = add_random_mobility(ec, nsnode2, x, y, 0, speed, bounds_width, bounds_height)

        # Create channel
        chan = add_wifi_channel(ec)
        ec.register_connection(chan, phy1)
        ec.register_connection(chan, phy2)

        ### create pinger
        ping = ec.register_resource("ns3::V4Ping")
        ec.set (ping, "Remote", "10.0.0.1")
        ec.set (ping, "Interval", "1s")
        ec.set (ping, "Verbose", True)
        ec.set (ping, "StartTime", "1s")
        ec.set (ping, "StopTime", "21s")
        ec.register_connection(ping, nsnode2)

        ec.deploy()

        ec.wait_finished([ping])
        
        stdout = ec.trace(simu, "stdout")

        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

if __name__ == '__main__':
    unittest.main()

