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

import os

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

ec = ExperimentController(exp_id = "dce-ccn-app")

node = ec.register_resource("LinuxNode")
ec.set(node, "hostname", "localhost")
ec.set(node, "cleanProcesses", True)
#ec.set(node, "cleanHome", True)

simu = ec.register_resource("LinuxNS3Simulation")
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
# Add ccnd to ns-3 node1
ccnd1 = ec.register_resource("ns3::LinuxDceCCND")
ec.set (ccnd1, "stackSize", 1<<20)
ec.set (ccnd1, "debug", 7)
ec.set (ccnd1, "capacity", 50000)
ec.set (ccnd1, "StartTime", "1s")
ec.set (ccnd1, "StopTime", "20s")
ec.register_connection(ccnd1, nsnode1)

# Add CCN repository with content to ns-3 node1
repofile = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 
    "..", "..", "..",
    "test", "resources", "linux", "ns3", "ccn", "repoFile1")

ccnr = ec.register_resource("ns3::LinuxDceCCNR")
ec.set (ccnr, "repoFile1", repofile) 
ec.set (ccnr, "stackSize", 1<<20)
ec.set (ccnr, "StartTime", "2s")
ec.set (ccnr, "StopTime", "120s")
ec.register_connection(ccnr, nsnode1)

# Add CCN repository with content to ns-3 node2
ccnd2 = ec.register_resource("ns3::LinuxDceCCND")
ec.set (ccnd2, "stackSize", 1<<20)
ec.set (ccnd2, "debug", 7)
ec.set (ccnd2, "capacity", 50000)
ec.set (ccnd2, "StartTime", "1s")
ec.set (ccnd2, "StopTime", "20s")
ec.register_connection(ccnd2, nsnode2)

# Add face from ns-3 node1 to ns-3 node2
ccndc1 = ec.register_resource("ns3::LinuxDceFIBEntry")
ec.set (ccndc1, "protocol", "udp") 
ec.set (ccndc1, "uri", "ccnx:/") 
ec.set (ccndc1, "host", "10.0.0.2") 
ec.set (ccndc1, "stackSize", 1<<20)
ec.set (ccndc1, "StartTime", "2s")
ec.set (ccndc1, "StopTime", "120s")
ec.register_connection(ccndc1, nsnode1)

# Add face from ns-3 node2 to ns-3 node1
ccndc2 = ec.register_resource("ns3::LinuxDceFIBEntry")
ec.set (ccndc2, "protocol", "udp") 
ec.set (ccndc2, "uri", "ccnx:/") 
ec.set (ccndc2, "host", "10.0.0.1") 
ec.set (ccndc2, "stackSize", 1<<20)
ec.set (ccndc2, "StartTime", "2s")
ec.set (ccndc2, "StopTime", "120s")
ec.register_connection(ccndc2, nsnode2)

# Add a ccncat to node2 to retrieve content
ccncat = ec.register_resource("ns3::LinuxDceCCNCat")
ec.set (ccncat, "contentName", "ccnx:/test/bunny.ts")
ec.set (ccncat, "stackSize", 1<<20)
ec.set (ccncat, "StartTime", "4s")
ec.set (ccncat, "StopTime", "120s")
ec.register_connection(ccncat, nsnode2)

ec.deploy()

ec.wait_finished([ccncat])

stdout = ec.trace(ccncat, "stdout")
# convert from bytes to MB
print "%0.2f MBytes received" % (len(stdout) / 1024.0 / 1024.0 )

ec.shutdown()

