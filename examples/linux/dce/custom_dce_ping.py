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


def add_point2point_device(ec, node, ip,  prefix):
    dev = ec.register_resource("ns3::PointToPointNetDevice")
    ec.set(dev, "ip", ip)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

ec = ExperimentController(exp_id = "dce-custom-ping")

node = ec.register_resource("LinuxNode")
ec.set(node, "hostname", "localhost")
ec.set(node, "cleanProcesses", True)
#ec.set(node, "cleanHome", True)

simu = ec.register_resource("LinuxNS3Simulation")
ec.set(simu, "verbose", True)
ec.set(simu, "nsLog", "DceApplication")
ec.set(simu, "enableDump", True)
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

stdout = ec.trace(ping, "stdout") 

ec.shutdown()

print "PING OUTPUT", stdout
