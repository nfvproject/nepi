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
#         Alexandros Kouvakas <alexandros.kouvakas@gmail.com>
#
#         Switch1 ------- Switch2         
#            /                \           
#           /                  \          
#          /                    \         
#       Host1                  Host2      



from nepi.execution.ec import ExperimentController

def add_node(ec, host, user):
    node = ec.register_resource("PlanetlabNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    return node

def add_ovs(ec, bridge_name, virtual_ip_pref, controller_ip, controller_port, node):
    ovs = ec.register_resource("OVSWitch")
    ec.set(ovs, "bridge_name", bridge_name)
    ec.set(ovs, "virtual_ip_pref", virtual_ip_pref)
    ec.set(ovs, "controller_ip", controller_ip)
    ec.set(ovs, "controller_port", controller_port)
    ec.register_connection(ovs, node)
    return ovs

def add_port(ec, port_name, ovs):
    port = ec.register_resource("OVSPort")
    ec.set(port, "port_name", port_name)
    ec.register_connection(port, ovs)
    return port

def add_tap(ec, ip4, prefix4, pointopoint, node):
    tap = ec.register_resource("PlanetlabTap")
    ec.set(tap, "ip4", ip4)
    ec.set(tap, "prefix4", prefix4)
    ec.set(tap, "pointopoint", pointopoint)
    ec.set(tap, "up", True)
    ec.register_connection(tap, node)
    return tap

def add_tunnel(ec, port0, tap):
    tunnel = ec.register_resource("Tunnel")
    ec.register_connection(port0, tunnel)
    ec.register_connection(tunnel, tap)
    return tunnel

def add_app(ec, command, node):
    app = ec.register_resource("LinuxApplication")
    ec.set(app, "command", command)
    ec.register_connection(app, node)
    return app

# Create the EC
ec = ExperimentController(exp_id = "one")

switch1 = "planetlab2.virtues.fi"
switch2 = "planetlab2.upc.es"
host1 = "planetlab2.ionio.gr"
host2 = "planetlab2.cs.aueb.gr"

slicename = "inria_nepi"

s1_node = add_node(ec, switch1, slicename)
s2_node = add_node(ec, switch2, slicename)

# Add switches 
ovs1 = add_ovs(ec, "nepi_bridge", "192.168.3.1/24", "85.23.168.77", "6633", s1_node)
ovs2 = add_ovs(ec, "nepi_bridge", "192.168.3.2/24", "85.23.168.77", "6633", s2_node)

# Add ports on ovs
port1 = add_port(ec, "nepi_port1", ovs1)
port3 = add_port(ec, "nepi_port3", ovs1)
port2 = add_port(ec, "nepi_port2", ovs2)
port4 = add_port(ec, "nepi_port4", ovs2)

h1_node = add_node(ec, host1, slicename)
h2_node = add_node(ec, host2, slicename) 

# Add tap devices
tap1 = add_tap(ec, "192.168.3.3", 24, "192.168.3.1", h1_node)
tap2 = add_tap(ec, "192.168.3.4", 24, "192.168.3.1", h2_node)

# Connect the nodes
tunnel1 = add_tunnel(ec, port1, tap1)
tunnel2 = add_tunnel(ec, port2, tap2)
tunnel3 = add_tunnel(ec, port3, port4)

# Add ping commands
app1 = add_app(ec, "ping -c3 192.168.3.3", s1_node)
app2 = add_app(ec, "ping -c3 192.168.3.4", s2_node)

ec.deploy()
ec.wait_finished([app2])

# Retreive ping results and save
# them in a file
ping1 = ec.trace(app1, 'stdout')
ping2 = ec.trace(app2, 'stdout')
f = open("examples/openvswitch/ping_res.txt", 'w').close()
f = open("examples/openvswitch/ping_res.txt", 'a')
f.write(ping1)
f.write(ping2)
f.close()

# Delete the overlay network
ec.shutdown()





