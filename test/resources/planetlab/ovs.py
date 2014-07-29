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

#         Switch1 ------- Switch2         
#            /                \           
#           /                  \          
#          /                    \         
#       Host1                  Host2      

from nepi.execution.ec import ExperimentController 

from test_utils import skipIfAnyNotAlive

import os
import time
import unittest

class OvsTestCase(unittest.TestCase):
    def setUp(self):
        self.switch1 = "planetlab2.virtues.fi"
        self.switch2 = "planetlab2.upc.es"
        self.host1 = "planetlab2.ionio.gr"
        self.host2 = "planetlab2.cs.aueb.gr"
        self.user = "inria_nepi"

    @skipIfAnyNotAlive
    def t_ovs(self, user1, switch1, user2, switch2, user3, host1, user4, host2):

        ec = ExperimentController(exp_id = "test-ovs")
        
        node1 = ec.register_resource("PlanetlabNode")
        ec.set(node1, "hostname", switch1)
        ec.set(node1, "username", user1)
        ec.set(node1, "cleanHome", True)
        ec.set(node1, "cleanProcesses", True)  

        ovs1 = ec.register_resource("OVSSwitch")
        ec.set(ovs1, "bridge_name", "nepi_bridge")
        ec.set(ovs1, "virtual_ip_pref", "192.168.3.1/24")
        ec.set(ovs1, "controller_ip", "85.23.168.77")
        ec.set(ovs1, "controller_port", "6633")
        ec.register_connection(ovs1, node1)

        port1 = ec.register_resource("OVSPort")
        ec.set(port1, "port_name", "port-1")
        ec.register_connection(port1, ovs1)

        port2 = ec.register_resource("OVSPort")
        ec.set(port2, "port_name", "port-2")
        ec.register_connection(port2, ovs1)

        node2 = ec.register_resource("PlanetlabNode")
        ec.set(node2, "hostname", switch2)
        ec.set(node2, "username", user2)
        ec.set(node2, "cleanHome", True)
        ec.set(node2, "cleanProcesses", True) 

        ovs2 = ec.register_resource("OVSSwitch")
        ec.set(ovs2, "bridge_name", "nepi_bridge")
        ec.set(ovs2, "virtual_ip_pref", "192.168.3.2/24")
        ec.set(ovs2, "controller_ip", "85.23.168.77")
        ec.set(ovs2, "controller_port", "6633")
        ec.register_connection(ovs2, node2)

        port3 = ec.register_resource("OVSPort")
        ec.set(port3, "port_name", "port-3")
        ec.register_connection(port3, ovs2)  

        port4 = ec.register_resource("OVSPort")
        ec.set(port4, "port_name", "port-4")
        ec.register_connection(port4, ovs2)

        node3 = ec.register_resource("PlanetlabNode")
        ec.set(node3, "hostname", host1)
        ec.set(node3, "username", user3)
        ec.set(node3, "cleanHome", True)
        ec.set(node3, "cleanProcesses", True)

        tap1 = ec.register_resource("PlanetlabTap")
        ec.set(tap1, "ip4", "192.168.3.3")
        ec.set(tap1, "pointopoint", "192.168.3.1")
        ec.set(tap1, "prefix4", 24)
        ec.register_connection(tap1, node3)

        node4 = ec.register_resource("PlanetlabNode")
        ec.set(node4, "hostname", host2)
        ec.set(node4, "username", user4)
        ec.set(node4, "cleanHome", True)
        ec.set(node4, "cleanProcesses", True)

        tap2 = ec.register_resource("PlanetlabTap")
        ec.set(tap2, "ip4", "192.168.3.4")
        ec.set(tap2, "pointopoint", "192.168.3.2")
        ec.set(tap2, "prefix4", 24)
        ec.register_connection(tap2, node4)

        ovstun1 = ec.register_resource("OVSTunnel")
        ec.register_connection(port1, ovstun1)
        ec.register_connection(tap1, ovstun1)

        ovstun2 = ec.register_resource("OVSTunnel")
        ec.register_connection(port3, ovstun2)
        ec.register_connection(tap2, ovstun2)

        ovstun3 = ec.register_resource("OVSTunnel")
        ec.register_connection(port2, ovstun3)
        ec.register_connection(port4, ovstun3)

        app1 = ec.register_resource("LinuxApplication")
        cmd = "ping -c3 192.168.3.2"
        ec.set(app1, "command", cmd)
        ec.register_connection(app1, node1)

        app2 = ec.register_resource("LinuxApplication")
        cmd = "ping -c3 192.168.3.4"
        ec.set(app2, "command", cmd)
        ec.register_connection(app2, node2)

        ec.deploy()

        ec.wait_finished(app2)
        
        if_name = ec.get(tap1, "deviceName")
        self.assertTrue(if_name.startswith("tap"))
        
        if_name = ec.get(tap2, "deviceName")
        self.assertTrue(if_name.startswith("tap"))

        ping1 = ec.trace(app1, 'stdout')
        expected1 = """3 packets transmitted, 3 received, 0% packet loss"""
        self.assertTrue(ping1.find(expected1) > -1)

        ping2 = ec.trace(app2, 'stdout')
        expected2 = """3 packets transmitted, 3 received, 0% packet loss"""
        self.assertTrue(ping2.find(expected2) > -1)

        ec.shutdown()

    def test_ovs(self):
        self.t_ovs(self.user, self.switch1, self.user, self.switch2, self.user, self.host1, self.user, self.host2)

if __name__ == '__main__':
    unittest.main()

