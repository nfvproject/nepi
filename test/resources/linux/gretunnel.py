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

from test_utils import skipIfAnyNotAliveWithIdentity

import os
import time
import unittest

class LinuxGRETunnelTestCase(unittest.TestCase):
    def setUp(self):
        self.host1 = "roseval.pl.sophia.inria.fr"
        self.host2 = "138.96.118.11"
        self.user1 = "inria_nepi"
        self.user2 = "omflab"
        self.identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])
        self.netblock = "192.168.1"

    @skipIfAnyNotAliveWithIdentity
    def t_tap_gre_tunnel(self, user1, host1, identity1, user2, host2, 
            identity2):

        ec = ExperimentController(exp_id = "test-tap-gre-tunnel")
        
        node1 = ec.register_resource("LinuxNode")
        ec.set(node1, "hostname", host1)
        ec.set(node1, "username", user1)
        ec.set(node1, "identity", identity1)
        ec.set(node1, "cleanHome", True)
        ec.set(node1, "cleanProcesses", True)

        tap1 = ec.register_resource("LinuxTap")
        ec.set(tap1, "ip4", "%s.1" % self.netblock)
        ec.set(tap1, "prefix4", 32)
        ec.register_connection(tap1, node1)

        node2 = ec.register_resource("LinuxNode")
        ec.set(node2, "hostname", host2)
        ec.set(node2, "username", user2)
        ec.set(node2, "identity", identity2)
        ec.set(node2, "cleanHome", True)
        ec.set(node2, "cleanProcesses", True)

        tap2 = ec.register_resource("LinuxTap")
        ec.set(tap2, "ip4", "%s.2" % self.netblock)
        ec.set(tap2, "prefix4", 32)
        ec.register_connection(tap2, node2)

        gretun = ec.register_resource("LinuxGRETunnel")
        ec.register_connection(tap1, gretun)
        ec.register_connection(tap2, gretun)

        app = ec.register_resource("LinuxApplication")
        cmd = "ping -c3 %s.2" % self.netblock
        ec.set(app, "command", cmd)
        ec.register_connection(app, node1)

        ec.deploy()

        ec.wait_finished(app)

        ping = ec.trace(app, 'stdout')
        expected = """3 packets transmitted, 3 received, 0% packet loss"""
        self.assertTrue(ping.find(expected) > -1)
        
        if_name = ec.get(tap1, "deviceName")
        self.assertTrue(if_name.startswith("tap"))
        
        if_name = ec.get(tap2, "deviceName")
        self.assertTrue(if_name.startswith("tap"))

        ec.shutdown()

    @skipIfAnyNotAliveWithIdentity
    def t_tun_gre_tunnel(self, user1, host1, identity1, user2, host2, 
            identity2):

        ec = ExperimentController(exp_id = "test-tun-gre-tunnel")
        
        node1 = ec.register_resource("LinuxNode")
        ec.set(node1, "hostname", host1)
        ec.set(node1, "username", user1)
        ec.set(node1, "identity", identity1)
        ec.set(node1, "cleanHome", True)
        ec.set(node1, "cleanProcesses", True)

        tun1 = ec.register_resource("LinuxTun")
        ec.set(tun1, "ip4", "%s.1" % self.netblock)
        ec.set(tun1, "prefix4", 32)
        ec.register_connection(tun1, node1)

        node2 = ec.register_resource("LinuxNode")
        ec.set(node2, "hostname", host2)
        ec.set(node2, "username", user2)
        ec.set(node2, "identity", identity2)
        ec.set(node2, "cleanHome", True)
        ec.set(node2, "cleanProcesses", True)

        tun2 = ec.register_resource("LinuxTun")
        ec.set(tun2, "ip4", "%s.2" % self.netblock)
        ec.set(tun2, "prefix4", 32)
        ec.register_connection(tun2, node2)

        udptun = ec.register_resource("LinuxGRETunnel")
        ec.register_connection(tun1, udptun)
        ec.register_connection(tun2, udptun)

        app = ec.register_resource("LinuxApplication")
        cmd = "ping -c3 %s.2" % self.netblock
        ec.set(app, "command", cmd)
        ec.register_connection(app, node1)

        ec.deploy()

        ec.wait_finished(app)

        ping = ec.trace(app, 'stdout')
        expected = """3 packets transmitted, 3 received, 0% packet loss"""
        self.assertTrue(ping.find(expected) > -1)
        
        if_name = ec.get(tun1, "deviceName")
        self.assertTrue(if_name.startswith("tun"))
        
        if_name = ec.get(tun2, "deviceName")
        self.assertTrue(if_name.startswith("tun"))

        ec.shutdown()

    def test_tap_gre_tunnel(self):
        self.t_tap_gre_tunnel(self.user1, self.host1, self.identity,
                self.user2, self.host2, self.identity)

    def test_tun_gre_tunnel(self):
        self.t_tun_gre_tunnel(self.user1, self.host1, self.identity,
                self.user2, self.host2, self.identity)

if __name__ == '__main__':
    unittest.main()

