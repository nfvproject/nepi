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
 
Initial positions. AP is fixed.

    +
100m| (30,100)  (60,100)  (90,100)
    |    n1       n2       n3
 90m|
    |
    |
 60m|  (30,60)  (60,60)   (90,60)
    |    n4       n5       n6
    |
 30m|             
    |            (60,0)
    |             n7 (AP)
    +----------------------------+
    0     30       60       90  100m

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

def add_wifi_device(ec, node, ip, prefix, access_point = False):
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

bounds_width = bounds_height = 100
speed = 1

ec = ExperimentController(exp_id = "ns3-wifi-ping")

# Simulation will run in a remote machine
node = ec.register_resource("LinuxNode")
ec.set(node, "hostname", "localhost")

# Add a simulation resource
simu = ec.register_resource("LinuxNS3Simulation")
ec.set(simu, "verbose", True)
ec.set(simu, "enableDump", True)
ec.set (simu, "StopTime", "22s")
ec.register_connection(simu, node)

x = 30
y = 100
nsnode1 = add_node(ec, simu)
dev1, phy1 = add_wifi_device(ec, nsnode1, "10.0.0.1", "24", access_point = False)
mobility1 = add_random_mobility(ec, nsnode1, x, y, 0, speed, bounds_width, bounds_height)

x = 60
y = 100
nsnode2 = add_node(ec, simu)
dev2, phy2 = add_wifi_device(ec, nsnode2, "10.0.0.2", "24", access_point = False)
mobility2 = add_random_mobility(ec, nsnode2, x, y, 0, speed, bounds_width, bounds_height)

x = 90
y = 100
nsnode3 = add_node(ec, simu)
dev3, phy3 = add_wifi_device(ec, nsnode3, "10.0.0.3", "24", access_point = False)
mobility3 = add_random_mobility(ec, nsnode3, x, y, 0, speed, bounds_width, bounds_height)

x = 30
y = 60
nsnode4 = add_node(ec, simu)
dev4, phy4 = add_wifi_device(ec, nsnode4, "10.0.0.4", "24", access_point = False)
mobility4 = add_random_mobility(ec, nsnode4, x, y, 0, speed, bounds_width, bounds_height)

x = 60
y = 60
nsnode5 = add_node(ec, simu)
dev5, phy5 = add_wifi_device(ec, nsnode5, "10.0.0.5", "24", access_point = False)
mobility5 = add_random_mobility(ec, nsnode5, x, y, 0, speed, bounds_width, bounds_height)

x = 90
y = 60
nsnode6 = add_node(ec, simu)
dev6, phy6 = add_wifi_device(ec, nsnode6, "10.0.0.6", "24", access_point = False)
mobility6 = add_random_mobility(ec, nsnode6, x, y, 0, speed, bounds_width, bounds_height)

x = 60
y = 0
nsnode7 = add_node(ec, simu)
dev7, phy7 = add_wifi_device(ec, nsnode7, "10.0.0.7", "24", access_point = True)
mobility7 = add_constant_mobility(ec, nsnode7, x, y, 0)

# Create channel
chan = add_wifi_channel(ec)
ec.register_connection(chan, phy1)
ec.register_connection(chan, phy2)
ec.register_connection(chan, phy3)
ec.register_connection(chan, phy4)
ec.register_connection(chan, phy5)
ec.register_connection(chan, phy6)
ec.register_connection(chan, phy7)

### create pinger
ping = ec.register_resource("ns3::V4Ping")
ec.set (ping, "Remote", "10.0.0.6")
ec.set (ping, "Interval", "1s")
ec.set (ping, "Verbose", True)
ec.set (ping, "StartTime", "1s")
ec.set (ping, "StopTime", "21s")
ec.register_connection(ping, nsnode1)

ec.deploy()

ec.wait_finished([ping])

stdout = ec.trace(simu, "stdout") 

ec.shutdown()

print "PING OUTPUT", stdout

