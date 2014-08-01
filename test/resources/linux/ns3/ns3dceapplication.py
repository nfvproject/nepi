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

    tcp = ec.register_resource("ns3::TcpL4Protocol")
    ec.register_connection(node, tcp)

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

class LinuxNS3DceApplicationTest(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_nepi"
        self.fedora_identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "inria_nepi"
        self.ubuntu_identity = "%s/.ssh/id_rsa" % (os.environ['HOME'])
 
    @skipIfNotAlive
    def t_dce_ping(self, host, user = None, identity = None):
        ec = ExperimentController(exp_id = "test-dce-ping")

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
        ec.set(simu, "buildMode", "debug")
        ec.set(simu, "nsLog", "DceApplication")
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
        ping = ec.register_resource("ns3::LinuxDceApplication")
        ec.set (ping, "sources", "http://www.skbuff.net/iputils/iputils-s20101006.tar.bz2")
        ec.set (ping, "build", "tar xvjf ${SRC}/iputils-s20101006.tar.bz2 && "
                "cd iputils-s20101006/ && "
                "sed -i 's/CFLAGS=/CFLAGS+=/g' Makefile && "
                "make CFLAGS=-fPIC LDFLAGS='-pie -rdynamic' ping && "
                "cp ping ${BIN_DCE} && cd - ")
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

    @skipIfNotAlive
    def t_dce_ccn(self, host, user = None, identity = None):
        ec = ExperimentController(exp_id = "test-dce-ccn")
       
        node = ec.register_resource("LinuxNode")
        if host == "localhost":
            ec.set(node, "hostname", host)
        else:
            ec.set(node, "hostname", host)
            ec.set(node, "username", user)
            ec.set(node, "identity", identity)

        #ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "buildMode", "debug")
        ec.set(simu, "nsLog", "DceApplication")
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
        ccnd1 = ec.register_resource("ns3::LinuxCCNDceApplication")

        # NOTE THAT INSTALLATION MIGHT FAIL IF openjdk-6-jdk is not installed
        ec.set(ccnd1, "depends", "libpcap0.8-dev openjdk-6-jdk ant1.8 autoconf "
            "libssl-dev libexpat-dev libpcap-dev libecryptfs0 libxml2-utils auto"
            "make gawk gcc g++ git-core pkg-config libpcre3-dev openjdk-6-jre-lib")
        ec.set (ccnd1, "sources", "http://www.ccnx.org/releases/ccnx-0.7.2.tar.gz")
        ec.set (ccnd1, "build", "tar zxf ${SRC}/ccnx-0.7.2.tar.gz && "
                "cd ccnx-0.7.2 && "
                " INSTALL_BASE=${BIN_DCE}/.. ./configure && "
                " make MORE_LDLIBS='-pie -rdynamic' && "
                " make install && "
                " cp ${BIN_DCE}/../bin/ccn* ${BIN_DCE} && "
                " cd -")
        ec.set (ccnd1, "binary", "ccnd")
        ec.set (ccnd1, "stackSize", 1<<20)
        ec.set (ccnd1, "environment", "CCND_CAP=50000; CCND_DEBUG=7")
        ec.set (ccnd1, "StartTime", "1s")
        ec.set (ccnd1, "StopTime", "20s")
        ec.register_connection(ccnd1, nsnode1)

        repofile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "ccn", 
            "repoFile1")

        ccnr = ec.register_resource("ns3::LinuxCCNDceApplication")
        ec.set (ccnr, "binary", "ccnr")
        ec.set (ccnr, "environment", "CCNR_DIRECTORY=/REPO/")
        ec.set (ccnr, "files", "%s=/REPO/repoFile1" % repofile) 
        ec.set (ccnr, "stackSize", 1<<20)
        ec.set (ccnr, "StartTime", "2s")
        ec.set (ccnr, "StopTime", "120s")
        ec.register_connection(ccnr, nsnode1)

        ccndc1 = ec.register_resource("ns3::LinuxCCNDceApplication")
        ec.set (ccndc1, "binary", "ccndc")
        ec.set (ccndc1, "arguments", "-v;add;ccnx:/;udp;10.0.0.2")
        ec.set (ccndc1, "stackSize", 1<<20)
        ec.set (ccndc1, "StartTime", "2s")
        ec.set (ccndc1, "StopTime", "120s")
        ec.register_connection(ccndc1, nsnode1)

        ccnd2 = ec.register_resource("ns3::LinuxCCNDceApplication")
        ec.set (ccnd2, "binary", "ccnd")
        ec.set (ccnd2, "stackSize", 1<<20)
        ec.set (ccnd2, "environment", "CCND_CAP=50000; CCND_DEBUG=7")
        ec.set (ccnd2, "StartTime", "1s")
        ec.set (ccnd2, "StopTime", "120s")
        ec.register_connection(ccnd2, nsnode2)

        ccndc2 = ec.register_resource("ns3::LinuxCCNDceApplication")
        ec.set (ccndc2, "binary", "ccndc")
        ec.set (ccndc2, "arguments", "-v;add;ccnx:/;udp;10.0.0.1")
        ec.set (ccndc2, "stackSize", 1<<20)
        ec.set (ccndc2, "StartTime", "2s")
        ec.set (ccndc2, "StopTime", "120s")
        ec.register_connection(ccndc2, nsnode2)

        ccnpeek = ec.register_resource("ns3::LinuxCCNDceApplication")
        ec.set (ccnpeek, "binary", "ccnpeek")
        ec.set (ccnpeek, "arguments", "ccnx:/test/bunny.ts")
        ec.set (ccnpeek, "stdinFile", "")
        ec.set (ccnpeek, "stackSize", 1<<20)
        ec.set (ccnpeek, "StartTime", "4s")
        ec.set (ccnpeek, "StopTime", "120s")
        ec.register_connection(ccnpeek, nsnode2)

        ccncat = ec.register_resource("ns3::LinuxCCNDceApplication")
        ec.set (ccncat, "binary", "ccncat")
        ec.set (ccncat, "arguments", "ccnx:/test/bunny.ts")
        ec.set (ccncat, "stdinFile", "")
        ec.set (ccncat, "stackSize", 1<<20)
        ec.set (ccncat, "StartTime", "4s")
        ec.set (ccncat, "StopTime", "120s")
        ec.register_connection(ccncat, nsnode2)

        ec.deploy()

        ec.wait_finished([ccncat])

        expected = "ccncat ccnx:/test/bunny.ts"
        cmdline = ec.trace(ccncat, "cmdline")
        self.assertTrue(cmdline.find(expected) > -1, cmdline)

        expected = "Start Time: NS3 Time:          4s ("
        status = ec.trace(ccncat, "status")
        self.assertTrue(status.find(expected) > -1, status)

        expected = 2873956
        stdout = ec.trace(ccncat, "stdout")
        self.assertTrue(len(stdout) == expected , stdout)

        ec.shutdown()

    def test_dce_ping_fedora(self):
        self.t_dce_ping(self.fedora_host, self.fedora_user, self.fedora_identity)

    def test_dce_ping_ubuntu(self):
        self.t_dce_ping(self.ubuntu_host, self.ubuntu_user, self.ubuntu_identity)

    def test_dce_ping_local(self):
        self.t_dce_ping("localhost")

    def test_dce_ccn_fedora(self):
        self.t_dce_ccn(self.fedora_host, self.fedora_user, self.fedora_identity)

    def test_dce_ccn_ubuntu(self):
        self.t_dce_ccn(self.ubuntu_host, self.ubuntu_user, self.ubuntu_identity)

    def test_dce_ccn_local(self):
        self.t_dce_ccn("localhost")

if __name__ == '__main__':
    unittest.main()
