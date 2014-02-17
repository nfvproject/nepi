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
# Authors :  Julien Tribino <julien.tribino@inria.fr>
#          Alina Quereilhac <alina.quereilhac@inria.fr>
#
# Topology :
# 
#         Switch1 -------- Switch2         
#            /                \           
#           /                  \          
#          /                    \         
#       Host1                  Host2      



from nepi.execution.ec import ExperimentController
import os, time
import sys

def add_node(ec, host, user, pl_user, pl_password):
    node = ec.register_resource("PlanetlabNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    if pl_user:
        ec.set(node, "pluser", pl_user)
    if pl_password:
        ec.set(node, "plpassword", pl_password)
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

def add_tunnel(ec, network, port0, tap):
    tunnel = ec.register_resource("OVSTunnel")
    ec.set(tunnel, "network", network)
    ec.register_connection(port0, tunnel)
    ec.register_connection(tunnel, tap)
    return tunnel

def add_app(ec, command, node):
    app = ec.register_resource("LinuxApplication")
    ec.set(app, "command", command)
    ec.register_connection(app, node)
    return app

# Create the EC
ec = ExperimentController(exp_id = "test")

switch1 = "planetlab2.virtues.fi"
switch2 = "planetlab2.upc.es"
host1 = "planetlab2.ionio.gr"
host2 = "iraplab2.iralab.uni-karlsruhe.de"

ip_controller = "194.254.215.12"
network = "192.168.3.0"

slicename = "inria_nepi"

pl_user = os.environ.get("PL_USER")
pl_password = os.environ.get("PL_PASS")

s1_node = add_node(ec, switch1, slicename, pl_user, pl_password)
s2_node = add_node(ec, switch2, slicename, pl_user, pl_password)

# Add switches 
ovs1 = add_ovs(ec, "nepi_bridge_1", "192.168.3.1/24", ip_controller, "6633", s1_node)
ovs2 = add_ovs(ec, "nepi_bridge_2", "192.168.3.2/24", ip_controller, "6633", s2_node)

# Add ports on ovs
port1 = add_port(ec, "nepi_port1", ovs1)
port3 = add_port(ec, "nepi_port3", ovs1)
port2 = add_port(ec, "nepi_port2", ovs2)
port4 = add_port(ec, "nepi_port4", ovs2)

h1_node = add_node(ec, host1, slicename, pl_user, pl_password)
h2_node = add_node(ec, host2, slicename, pl_user, pl_password)

# Add tap devices
tap1 = add_tap(ec, "192.168.3.3", 24, "192.168.3.1", h1_node)
tap2 = add_tap(ec, "192.168.3.4", 24, "192.168.3.2", h2_node)

# Connect the nodes
tunnel1 = add_tunnel(ec, network, port1, tap1)
tunnel2 = add_tunnel(ec, network, port2, tap2)
tunnel3 = add_tunnel(ec, network, port3, port4)

# Add ping commands
app1 = add_app(ec, "ping -c5 192.168.3.2", s1_node)
app2 = add_app(ec, "ping -c5 192.168.3.3", s1_node)
app3 = add_app(ec, "ping -c5 192.168.3.4", s1_node)
app4 = add_app(ec, "ping -c5 192.168.3.1", s2_node)
app5 = add_app(ec, "ping -c5 192.168.3.3", s2_node)
app6 = add_app(ec, "ping -c5 192.168.3.4", s2_node)
app7 = add_app(ec, "ping -c5 192.168.3.1", h1_node)
app8 = add_app(ec, "ping -c5 192.168.3.2", h1_node)
app9 = add_app(ec, "ping -c5 192.168.3.4", h1_node)
app10 = add_app(ec, "ping -c5 192.168.3.1", h2_node)
app11 = add_app(ec, "ping -c5 192.168.3.2", h2_node)
app12 = add_app(ec, "ping -c5 192.168.3.3", h2_node)

ec.deploy()

ec.wait_finished([app1, app2, app3, app4, app5, app6, app7, app8, app9, app10, app11, app12])

# Retreive ping results and save
# them in a file
ping1 = ec.trace(app1, 'stdout')
ping2 = ec.trace(app2, 'stdout')
ping3 = ec.trace(app3, 'stdout')
ping4 = ec.trace(app4, 'stdout')
ping5 = ec.trace(app5, 'stdout')
ping6 = ec.trace(app6, 'stdout')
ping7 = ec.trace(app7, 'stdout')
ping8 = ec.trace(app8, 'stdout')
ping9 = ec.trace(app9, 'stdout')
ping10 = ec.trace(app10, 'stdout')
ping11 = ec.trace(app11, 'stdout')
ping12 = ec.trace(app12, 'stdout')

if not ping12:
  ec.shutdown()
  sys.exit("No ping found")

f = open("examples/openvswitch/ovs_ping_2switches.txt", 'w')
f.write("************ Ping From Switch 1 : 192.168.3.1 ********************\n\n")
f.write(ping1)
f.write("----------------------------------------\n\n")
f.write(ping2)
f.write("----------------------------------------\n\n")
f.write(ping3)
f.write("************ Ping From Switch 2 : 192.168.3.2 ********************\n\n")
f.write(ping4)
f.write("----------------------------------------\n\n")
f.write(ping5)
f.write("----------------------------------------\n\n")
f.write(ping6)
f.write("************ Ping From Host 1 : 192.168.3.3 ********************\n\n")
f.write(ping7)
f.write("----------------------------------------\n\n")
f.write(ping8)
f.write("----------------------------------------\n\n")
f.write(ping9)
f.write("************ Ping From Host 2 : 192.168.3.4 ********************\n\n")
f.write(ping10)
f.write("----------------------------------------\n\n")
f.write(ping11)
f.write("----------------------------------------\n\n")
f.write(ping12)

f.close()

# Delete the overlay network
ec.shutdown()





