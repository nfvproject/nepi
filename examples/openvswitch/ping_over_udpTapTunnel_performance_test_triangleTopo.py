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
#                  Host3
#                    |
#                    |
#                    |   
#                 Switch3                         
#                 /    \          
#                /      \                
#               /        \              
#              /          \             
#         Switch1 ----- Switch2         
#            /              \           
#           /                \          
#          /                  \         
#       Host1                Host2   

from nepi.execution.ec import ExperimentController 

import os
import time

### Useful Method to Create RM ##
def add_node(ec, host, user):
    node = ec.register_resource("PlanetlabNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    return node

def add_tap(ec, ip4, prefix4, pointopoint, node):
    tap = ec.register_resource("PlanetlabTap")
    ec.set(tap, "ip4", ip4)
    ec.set(tap, "prefix4", prefix4)
    ec.set(tap, "pointopoint", pointopoint)
    ec.set(tap, "up", True)
    ec.register_connection(tap, node)
    return tap

def add_udptun(ec, tap1, tap2):
    udptun = ec.register_resource("UdpTunnel")
    ec.register_connection(tap1, udptun)
    ec.register_connection(tap2, udptun)
    return udptun

def add_vroute(ec, network, tap):
    vroute = ec.register_resource("PlanetlabVroute")
    ec.set(vroute, "action", "add")
    ec.set(vroute, "network", network)
    ec.register_connection(vroute, tap)
    return vroute

def add_app(ec, command, node):
    app = ec.register_resource("LinuxApplication")
    ec.set(app, "command", command)
    ec.register_connection(app, node)
    return app

### Data that can be changed ###
user = "inria_nepi"

hostname_switch1 = "planetlab2.virtues.fi"
hostname_switch2 = "planetlab2.upc.es"
hostname_switch3 = "planetlab2.cs.aueb.gr"
hostname_host1 = "planetlab2.ionio.gr"
hostname_host2 = "iraplab2.iralab.uni-karlsruhe.de"
hostname_host3 = "planetlab2.diku.dk"


### Start Experiment ###
ec = ExperimentController(exp_id = "test-tap-tunnel")
     
## Create The topology ##   
host1 = add_node(ec, hostname_host1, user)
tap1 = add_tap(ec, "192.168.3.1", 24, "192.168.3.2", host1)

switch1 = add_node(ec, hostname_switch1, user)
tap2 = add_tap(ec, "192.168.3.2", 24, "192.168.3.1", switch1)
tap102 = add_tap(ec, "192.168.3.102", 29, "192.168.3.104", switch1)
tap152 = add_tap(ec, "192.168.3.152", 29, "192.168.3.156", switch1)

host2 = add_node(ec, hostname_host2, user)
tap13 = add_tap(ec, "192.168.3.13", 24, "192.168.3.14", host2)

switch2 = add_node(ec, hostname_switch2, user)
tap14 = add_tap(ec, "192.168.3.14", 24, "192.168.3.13", switch2)
tap104 = add_tap(ec, "192.168.3.104", 29, "192.168.3.102", switch2)
tap204 = add_tap(ec, "192.168.3.204", 29, "192.168.3.206", switch2)

host3 = add_node(ec, hostname_host3, user)
tap25 = add_tap(ec, "192.168.3.25", 24, "192.168.3.26", host3)

switch3 = add_node(ec, hostname_switch3, user)
tap26 = add_tap(ec, "192.168.3.26", 24, "192.168.3.25", switch3)
tap156 = add_tap(ec, "192.168.3.156", 29, "192.168.3.152", switch3)
tap206 = add_tap(ec, "192.168.3.206", 29, "192.168.3.204", switch3)

## Create the UDP Tunnel ## 
udptun1 = add_udptun(ec, tap1, tap2)
udptun2 = add_udptun(ec, tap13, tap14)
udptun3 = add_udptun(ec, tap25, tap26)

udptun4 = add_udptun(ec, tap102, tap104)
udptun5 = add_udptun(ec, tap152, tap156)
udptun6 = add_udptun(ec, tap204, tap206)

## Create the PlanetLab Route ## 
vroute1 = add_vroute(ec, "192.168.3.0", tap1)
vroute2 = add_vroute(ec, "192.168.3.0", tap13)
vroute3 = add_vroute(ec, "192.168.3.0", tap25)

vroute7 = add_vroute(ec, "192.168.3.8", tap102)
vroute8 = add_vroute(ec, "192.168.3.0", tap104)
vroute9 = add_vroute(ec, "192.168.3.24", tap152)
vroute10 = add_vroute(ec, "192.168.3.0", tap156)
vroute11 = add_vroute(ec, "192.168.3.24", tap204)
vroute12 = add_vroute(ec, "192.168.3.8", tap206)

## Create all the Ping ## 

app1 = add_app(ec, "ping -c8 192.168.3.13", host1)
app2 = add_app(ec, "ping -c8 192.168.3.25", host1)
app3 = add_app(ec, "ping -c8 192.168.3.104", host1)
app4 = add_app(ec, "ping -c8 192.168.3.156", host1)
app5 = add_app(ec, "ping -c8 192.168.3.2", host1)

app11 = add_app(ec, "ping -c8 192.168.3.1", host2)
app12 = add_app(ec, "ping -c8 192.168.3.25", host2)
app13 = add_app(ec, "ping -c8 192.168.3.102", host2)
app14 = add_app(ec, "ping -c8 192.168.3.206", host2)
app15 = add_app(ec, "ping -c8 192.168.3.14", host2)

app21 = add_app(ec, "ping -c8 192.168.3.1", host3)
app22 = add_app(ec, "ping -c8 192.168.3.13", host3)
app23 = add_app(ec, "ping -c8 192.168.3.152", host3)
app24 = add_app(ec, "ping -c8 192.168.3.204", host3)
app25 = add_app(ec, "ping -c8 192.168.3.26", host3)

ec.deploy()

ec.wait_finished([app1 ,app2, app3, app4, app5, app11 ,app12, app13, app14, app15, app21 ,app22, app23, app24, app25])

# Retreive ping results and save
# them in a file
ping1 = ec.trace(app1, 'stdout')
ping2 = ec.trace(app2, 'stdout')
ping3 = ec.trace(app3, 'stdout')
ping4 = ec.trace(app4, 'stdout')
ping5 = ec.trace(app5, 'stdout')
ping11 = ec.trace(app11, 'stdout')
ping12 = ec.trace(app12, 'stdout')
ping13 = ec.trace(app13, 'stdout')
ping14 = ec.trace(app14, 'stdout')
ping15 = ec.trace(app15, 'stdout')
ping21 = ec.trace(app21, 'stdout')
ping22 = ec.trace(app22, 'stdout')
ping23 = ec.trace(app23, 'stdout')
ping24 = ec.trace(app24, 'stdout')
ping25 = ec.trace(app25, 'stdout')

f = open("examples/openvswitch/ping_over_udpTapTunnel_performance_test.txt", 'w')

if not ping25:
  ec.shutdown()
  

f.write("************ Ping From Host 1 : 192.168.3.1 ********************\n\n")
f.write(ping1)
f.write("----------------------------------------\n\n")
f.write(ping2)
f.write("----------------------------------------\n\n")
f.write(ping3)
f.write("----------------------------------------\n\n")
f.write(ping4)
f.write("----------------------------------------\n\n")
f.write(ping5)
f.write("************ Ping From Host 2 : 192.168.3.13 ********************\n\n")
f.write(ping11)
f.write("----------------------------------------\n\n")
f.write(ping12)
f.write("----------------------------------------\n\n")
f.write(ping13)
f.write("----------------------------------------\n\n")
f.write(ping14)
f.write("----------------------------------------\n\n")
f.write(ping15)
f.write("************ Ping From Host 3 : 192.168.3.25 ********************\n\n")
f.write(ping21)
f.write("----------------------------------------\n\n")
f.write(ping22)
f.write("----------------------------------------\n\n")
f.write(ping23)
f.write("----------------------------------------\n\n")
f.write(ping24)
f.write("----------------------------------------\n\n")
f.write(ping25)

f.close()

# Delete the overlay network
ec.shutdown()





