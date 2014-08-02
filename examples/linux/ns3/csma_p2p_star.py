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

""" 
network topology:
  
                        
                        n6
                        |
                       p2p
                        |
                        n4
                        |
   n1 -- p2p -- n2 -- csma -- n5 -- p2p -- n8
                        | 
                        n3
                        |
                        p2p
                        |
                        n7

"""

from nepi.execution.ec import ExperimentController 

def add_node(ec, simu):
    ## Add a ns-3 node with its protocol stack
    nsnode = ec.register_resource("ns3::Node")
    ec.register_connection(nsnode, simu)

    ipv4 = ec.register_resource("ns3::Ipv4L3Protocol")
    ec.register_connection(nsnode, ipv4)
    arp = ec.register_resource("ns3::ArpL3Protocol")
    ec.register_connection(nsnode, arp)
    icmp = ec.register_resource("ns3::Icmpv4L4Protocol")
    ec.register_connection(nsnode, icmp)
    return nsnode

def add_p2p_dev(ec, nsnode, ip, prefix):
    # Add a point to point net device to the node
    dev = ec.register_resource("ns3::PointToPointNetDevice")
    ec.set(dev, "ip", ip)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(nsnode, dev)
    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)
    return dev

def add_csma_dev(ec, nsnode, ip, prefix):
    dev = ec.register_resource("ns3::CsmaNetDevice")
    ec.set(dev, "ip", ip)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(nsnode, dev)
    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)
    return dev

def add_csma_chan(ec, devs):
    # Create channel
    chan = ec.register_resource("ns3::CsmaChannel")
    ec.set(chan, "Delay", "0s")

    for dev in devs:
        ec.register_connection(chan, dev)

    return chan

def add_p2p_chan(ec, dev1, dev2):
    # Add a point to point channel
    chan = ec.register_resource("ns3::PointToPointChannel")
    ec.set(chan, "Delay", "0s")
    ec.register_connection(chan, dev1)
    ec.register_connection(chan, dev2)
    return chan

ec = ExperimentController(exp_id = "ns3-csma-p2p-ping")

# Simulation will run in a remote machine
node = ec.register_resource("LinuxNode")
ec.set(node, "hostname", "localhost")

# Add a simulation resource
simu = ec.register_resource("LinuxNS3Simulation")
ec.set(simu, "verbose", True)
ec.set(simu, "enableDump", True)
ec.register_connection(simu, node)

# Add simulated nodes
nsnode1 = add_node(ec, simu)
nsnode2 = add_node(ec, simu)
nsnode3 = add_node(ec, simu)
nsnode4 = add_node(ec, simu)
nsnode5 = add_node(ec, simu)
nsnode6 = add_node(ec, simu)
nsnode7 = add_node(ec, simu)
nsnode8 = add_node(ec, simu)

# Build the start topology
dev12 = add_p2p_dev(ec, nsnode1, "10.0.1.1", "30") 
dev21 = add_p2p_dev(ec, nsnode2, "10.0.1.2", "30") 
p2p1 = add_p2p_chan(ec, dev12, dev21)

dev46 = add_p2p_dev(ec, nsnode4, "10.0.2.1", "30") 
dev64 = add_p2p_dev(ec, nsnode6, "10.0.2.2", "30") 
p2p2 = add_p2p_chan(ec, dev46, dev64)

dev37 = add_p2p_dev(ec, nsnode3, "10.0.3.1", "30") 
dev73 = add_p2p_dev(ec, nsnode7, "10.0.3.2", "30") 
p2p3 = add_p2p_chan(ec, dev37, dev73)

dev85 = add_p2p_dev(ec, nsnode5, "10.0.4.1", "30") 
dev58 = add_p2p_dev(ec, nsnode8, "10.0.4.2", "30") 
p2p4 = add_p2p_chan(ec, dev85, dev58)

dev2 = add_csma_dev(ec, nsnode2, "10.0.0.1", "24")
dev3 = add_csma_dev(ec, nsnode3, "10.0.0.2", "24")
dev4 = add_csma_dev(ec, nsnode4, "10.0.0.3", "24")
dev5 = add_csma_dev(ec, nsnode5, "10.0.0.4", "24")

csma1 = add_csma_chan(ec, [dev2, dev3, dev4, dev5])

## Add routes
# Add n2 as default gw for n1
r1 = ec.register_resource("ns3::Route")
ec.set(r1, "network", "0.0.0.0")
ec.set(r1, "prefix", "30")
ec.set(r1, "nexthop", "10.0.1.2")
ec.register_connection(r1, nsnode1)

# Add route to n8 from n2
r28 = ec.register_resource("ns3::Route")
ec.set(r28, "network", "10.0.4.0")
ec.set(r28, "prefix", "30")
ec.set(r28, "nexthop", "10.0.0.4")
ec.register_connection(r28, nsnode2)

# Add n5 as default gw for n8
r8 = ec.register_resource("ns3::Route")
ec.set(r8, "network", "0.0.0.0")
ec.set(r8, "prefix", "30")
ec.set(r8, "nexthop", "10.0.4.1")
ec.register_connection(r8, nsnode8)

# Add route to n1 from n5
r51 = ec.register_resource("ns3::Route")
ec.set(r51, "network", "10.0.1.0")
ec.set(r51, "prefix", "30")
ec.set(r51, "nexthop", "10.0.0.1")
ec.register_connection(r51, nsnode5)

### create pinger
ping = ec.register_resource("ns3::V4Ping")
ec.set (ping, "Remote", "10.0.4.2")
ec.set (ping, "Interval", "1s")
ec.set (ping, "Verbose", True)
ec.set (ping, "StartTime", "0s")
ec.set (ping, "StopTime", "20s")
ec.register_connection(ping, nsnode1)

ec.deploy()

ec.wait_finished([ping])

stdout = ec.trace(simu, "stdout") 

ec.shutdown()

print "PING OUTPUT", stdout
