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

from nepi.execution.ec import ExperimentController 
from nepi.execution.trace import TraceAttr

from test_utils import skipIfNotAlive

import os
import shutil
import time
import tempfile
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

    udp = ec.register_resource("ns3::UdpL4Protocol")
    ec.register_connection(node, udp)

    return node

def add_point2point_device(ec, node, ip, prefix):
    dev = ec.register_resource("ns3::PointToPointNetDevice")
    ec.set(dev, "ip", ip)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_csma_device(ec, node, ip, prefix):
    dev = ec.register_resource("ns3::CsmaNetDevice")
    ec.set(dev, "ip", ip)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_wifi_device(ec, node, ip, prefix, 
        access_point = False):
    dev = ec.register_resource("ns3::WifiNetDevice")
    ec.set(dev, "ip", ip)
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

class LinuxNS3SimulationSerializationTest(unittest.TestCase):
    def setUp(self):
        #self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_host = "planetlab1.informatik.uni-erlangen.de"
        self.fedora_user = "inria_nepi"
        self.fedora_identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])

    @skipIfNotAlive
    def t_wifi_serialize(self, host, user = None, identity = None):
        bounds_width = bounds_height = 200
        x = y = 100
        speed = 1

        dirpath = tempfile.mkdtemp()
        
        ec = ExperimentController(exp_id = "test-ns3-wifi-ping")
        
        node = ec.register_resource("LinuxNode")
        if host == "localhost":
            ec.set(node, "hostname", "localhost")
        else:
            ec.set(node, "hostname", host)
            ec.set(node, "username", user)
            ec.set(node, "identity", identity)

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

        filepath = ec.save(dirpath)
        print filepath
        
        ec.deploy()

        ec.wait_finished([ping])
        
        stdout = ec.trace(simu, "stdout")

        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

        # Load serialized experiment
        ec2 = ExperimentController.load(filepath)
        
        ec2.deploy()

        ec2.wait_finished([ping])
        
        self.assertEquals(len(ec.resources), len(ec2.resources))
        
        stdout = ec2.trace(simu, "stdout")
 
        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)
        
        ec2.shutdown()

        shutil.rmtree(dirpath)

    @skipIfNotAlive
    def t_routing_serialize(self, host, user = None, identity = None):
        """ 
        network topology:
                                n4
                                |
           n1 -- p2p -- n2 -- csma -- n5 -- p2p -- n6
           |                    | 
           ping n6              n3
           

        """
        dirpath = tempfile.mkdtemp()
        
        ec = ExperimentController(exp_id = "test-ns3-routes")
        
        node = ec.register_resource("LinuxNode")
        if host == "localhost":
            ec.set(node, "hostname", host)
        else:
            ec.set(node, "hostname", host)
            ec.set(node, "username", user)
            ec.set(node, "identity", identity)

        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        p2p12 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")

        nsnode2 = add_ns3_node(ec, simu)
        p2p21 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")
        csma2 = add_csma_device(ec, nsnode2, "10.0.1.1", "24")

        nsnode3 = add_ns3_node(ec, simu)
        csma3 = add_csma_device(ec, nsnode3, "10.0.1.2", "24")

        nsnode4 = add_ns3_node(ec, simu)
        csma4 = add_csma_device(ec, nsnode4, "10.0.1.3", "24")

        nsnode5 = add_ns3_node(ec, simu)
        p2p56 = add_point2point_device(ec, nsnode5, "10.0.2.1", "30")
        csma5 = add_csma_device(ec, nsnode5, "10.0.1.4", "24")

        nsnode6 = add_ns3_node(ec, simu)
        p2p65 = add_point2point_device(ec, nsnode6, "10.0.2.2", "30")

        # P2P chan1
        p2p_chan1 = ec.register_resource("ns3::PointToPointChannel")
        ec.set(p2p_chan1, "Delay", "0s")
        ec.register_connection(p2p_chan1, p2p12)
        ec.register_connection(p2p_chan1, p2p21)

        # CSMA chan
        csma_chan = ec.register_resource("ns3::CsmaChannel")
        ec.set(csma_chan, "Delay", "0s")
        ec.register_connection(csma_chan, csma2)
        ec.register_connection(csma_chan, csma3)
        ec.register_connection(csma_chan, csma4)
        ec.register_connection(csma_chan, csma5)

        # P2P chan2
        p2p_chan2 = ec.register_resource("ns3::PointToPointChannel")
        ec.set(p2p_chan2, "Delay", "0s")
        ec.register_connection(p2p_chan2, p2p56)
        ec.register_connection(p2p_chan2, p2p65)

        # Add routes - n1 - n6
        r1 = ec.register_resource("ns3::Route")
        ec.set(r1, "network", "10.0.2.0")
        ec.set(r1, "prefix", "30")
        ec.set(r1, "nexthop", "10.0.0.2")
        ec.register_connection(r1, nsnode1)

        # Add routes - n2 - n6
        r2 = ec.register_resource("ns3::Route")
        ec.set(r2, "network", "10.0.2.0")
        ec.set(r2, "prefix", "30")
        ec.set(r2, "nexthop", "10.0.1.4")
        ec.register_connection(r2, nsnode2)

        # Add routes - n5 - n1
        r5 = ec.register_resource("ns3::Route")
        ec.set(r5, "network", "10.0.0.0")
        ec.set(r5, "prefix", "30")
        ec.set(r5, "nexthop", "10.0.1.1")
        ec.register_connection(r5, nsnode5)

        # Add routes - n6 - n1
        r6 = ec.register_resource("ns3::Route")
        ec.set(r6, "network", "10.0.0.0")
        ec.set(r6, "prefix", "30")
        ec.set(r6, "nexthop", "10.0.2.1")
        ec.register_connection(r6, nsnode6)

        ### create pinger
        ping = ec.register_resource("ns3::V4Ping")
        ec.set (ping, "Remote", "10.0.2.2")
        ec.set (ping, "Interval", "1s")
        ec.set (ping, "Verbose", True)
        ec.set (ping, "StartTime", "1s")
        ec.set (ping, "StopTime", "21s")
        ec.register_connection(ping, nsnode1)

        filepath = ec.save(dirpath)
        print filepath
        
        ec.deploy()

        ec.wait_finished([ping])
        
        stdout = ec.trace(simu, "stdout")

        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

        # Load serialized experiment
        ec2 = ExperimentController.load(filepath)
        
        ec2.deploy()

        ec2.wait_finished([ping])
        
        self.assertEquals(len(ec.resources), len(ec2.resources))
        
        stdout = ec2.trace(simu, "stdout")
 
        expected = "20 packets transmitted, 20 received, 0% packet loss"
        self.assertTrue(stdout.find(expected) > -1)
        
        ec2.shutdown()

        shutil.rmtree(dirpath)

    @skipIfNotAlive
    def t_dce_serialize(self, host, user = None, identity = None):
        dirpath = tempfile.mkdtemp()
        
        ec = ExperimentController(exp_id = "test-ns3-dce")
        
        node = ec.register_resource("LinuxNode")
        if host == "localhost":
            ec.set(node, "hostname", host)
        else:
            ec.set(node, "hostname", host)
            ec.set(node, "username", user)
            ec.set(node, "identity", identity)

        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        p2p1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")
        ec.set(p2p1, "DataRate", "5Mbps")

        nsnode2 = add_ns3_node(ec, simu)
        p2p2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")
        ec.set(p2p2, "DataRate", "5Mbps")

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "2ms")

        ec.register_connection(chan, p2p1)
        ec.register_connection(chan, p2p2)

        ### create applications
        udp_perf = ec.register_resource("ns3::DceApplication")
        ec.set (udp_perf, "binary", "udp-perf")
        ec.set (udp_perf, "stackSize", 1<<20)
        ec.set (udp_perf, "arguments", "--duration=10;--nodes=2")
        ec.set (udp_perf, "StartTime", "1s")
        ec.set (udp_perf, "StopTime", "20s")
        ec.register_connection(udp_perf, nsnode1)

        udp_perf_client = ec.register_resource("ns3::DceApplication")
        ec.set (udp_perf_client, "binary", "udp-perf")
        ec.set (udp_perf_client, "stackSize", 1<<20)
        ec.set (udp_perf_client, "arguments", "--client;--nodes=2;--host=10.0.0.1;--duration=10")
        ec.set (udp_perf_client, "StartTime", "2s")
        ec.set (udp_perf_client, "StopTime", "20s")
        ec.register_connection(udp_perf_client, nsnode2)

        filepath = ec.save(dirpath)
        
        ec.deploy()

        ec.wait_finished([udp_perf_client])

        # Give time to flush the streams
        import time
        time.sleep(5) 

        expected = "udp-perf --duration=10 --nodes=2"
        cmdline = ec.trace(udp_perf, "cmdline")
        self.assertTrue(cmdline.find(expected) > -1, cmdline)

        expected = "Start Time: NS3 Time:          1s ("
        status = ec.trace(udp_perf, "status")
        self.assertTrue(status.find(expected) > -1, status)

        expected = "received=1500 bytes, 1 reads (@1500 bytes) 1500"
        stdout = ec.trace(udp_perf, "stdout")
        self.assertTrue(stdout.find(expected) > -1, stdout)

        ec.shutdown()

        # Load serialized experiment
        ec2 = ExperimentController.load(filepath)
        
        ec2.deploy()
        ec2.wait_finished([udp_perf_client])

        # Give time to flush the streams
        time.sleep(5) 
       
        self.assertEquals(len(ec.resources), len(ec2.resources))
 
        expected = "udp-perf --duration=10 --nodes=2"
        cmdline = ec2.trace(udp_perf, "cmdline")
        self.assertTrue(cmdline.find(expected) > -1, cmdline)

        expected = "Start Time: NS3 Time:          1s ("
        status = ec2.trace(udp_perf, "status")
        self.assertTrue(status.find(expected) > -1, status)

        expected = "received=1500 bytes, 1 reads (@1500 bytes) 1500"
        stdout = ec2.trace(udp_perf, "stdout")
        self.assertTrue(stdout.find(expected) > -1, stdout)

        ec2.shutdown()

        shutil.rmtree(dirpath)
    
    def test_wifi_serialize_fedora(self):
        self.t_wifi_serialize(self.fedora_host, self.fedora_user, self.fedora_identity)

    def test_wifi_serialize_local(self):
        self.t_wifi_serialize("localhost")

    def test_routing_serialize_fedora(self):
        self.t_routing_serialize(self.fedora_host, self.fedora_user, self.fedora_identity)

    def test_routing_serialize_local(self):
        self.t_routing_serialize("localhost")

    def test_dce_serialize_fedora(self):
        self.t_dce_serialize(self.fedora_host, self.fedora_user, self.fedora_identity)

    def test_dce_serialize_local(self):
        self.t_dce_serialize("localhost")


if __name__ == '__main__':
    unittest.main()

