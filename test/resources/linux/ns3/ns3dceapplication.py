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

    udp = ec.register_resource("ns3::UdpL4Protocol")
    ec.register_connection(node, udp)

    return node

def add_point2point_device(ec, node, address = None,  prefix = None):
    dev = ec.register_resource("ns3::PointToPointNetDevice")
    if address:
       ec.set(dev, "ip", address)
    if prefix:
       ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_csma_device(ec, node, address = None, prefix = None):
    dev = ec.register_resource("ns3::CsmaNetDevice")
    if address:
        ec.set(dev, "ip", address)
    if prefix:
        ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_wifi_device(ec, node, address = None, prefix = None, 
        access_point = False):
    dev = ec.register_resource("ns3::WifiNetDevice")
    if address:
        ec.set(dev, "ip", address)
    if prefix:
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

class LinuxNS3DceApplicationTest(unittest.TestCase):
    def setUp(self):
        #elf.fedora_host = "nepi2.pl.sophia.inria.fr"
        #self.fedora_host = "planetlabpc1.upf.edu"
        self.fedora_host = "peeramide.irisa.fr"
        self.fedora_user = "inria_nepi"
        #self.fedora_user = "inria_alina"
        self.fedora_identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])

    def test_dce_application(self):
        ec = ExperimentController(exp_id = "test-linux-ns3-dce")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "enableDCE", True)
        ec.set(simu, "buildMode", "debug")
        ec.set(simu, "nsLog", "DceApplication")
        ec.register_connection(simu, node)

        nsnode1 = add_ns3_node(ec, simu)
        ec.set(nsnode1, "enableDCE", True)
        p2p1 = add_point2point_device(ec, nsnode1, "10.0.0.1", "30")
        ec.set(p2p1, "DataRate", "5Mbps")

        nsnode2 = add_ns3_node(ec, simu)
        ec.set(nsnode2, "enableDCE", True)
        p2p2 = add_point2point_device(ec, nsnode2, "10.0.0.2", "30")
        ec.set(p2p2, "DataRate", "5Mbps")

        # Create channel
        chan = ec.register_resource("ns3::PointToPointChannel")
        ec.set(chan, "Delay", "2ms")

        ec.register_connection(chan, p2p1)
        ec.register_connection(chan, p2p2)

        ### create applications
        ping = ec.register_resource("ns3::LinuxDceApplication")
        """
        ec.set (ping, "sources", "http://www.skbuff.net/iputils/iputils-s20101006.tar.bz2")
        ec.set (ping, "build", "tar xvjf ${SRC}/iputils-s20101006.tar.bz2 && "
                "cd iputils-s20101006/ && "
                "sed -i 's/CFLAGS=/CFLAGS+=/g' Makefile && "
                "make CFLAGS=-fPIC LDFLAGS=-pie ping && "
                "cp ping ${BIN_DCE} ")
        """
        ec.set (ping, "binary", "ping")
        ec.set (ping, "stackSize", 1<<20)
        ec.set (ping, "arguments", "-c 10;-s 1000;10.0.0.2")
        ec.set (ping, "StartTime", "1s")
        ec.set (ping, "StopTime", "20s")
        ec.register_connection(ping, nsnode1)

        ec.deploy()

        ec.wait_finished([ping])

        expected = "ping -c 10 -s 1000 10.0.0.2"
        cmdline = ec.trace(ping, "cmdline")
        self.assertTrue(cmdline.find(expected) > -1, cmdline)
        
        expected = "Start Time: NS3 Time:          1s ("
        status = ec.trace(ping, "status")
        self.assertTrue(status.find(expected) > -1, status)

        expected = "10 packets transmitted, 10 received, 0% packet loss, time 9002ms"
        stdout = ec.trace(ping, "stdout")
        self.assertTrue(stdout.find(expected) > -1, stdout)

        stderr = ec.trace(simu, "stderr")
        expected = "DceApplication:StartApplication"
        self.assertTrue(stderr.find(expected) > -1, stderr)

        ec.shutdown()


if __name__ == '__main__':
    unittest.main()
