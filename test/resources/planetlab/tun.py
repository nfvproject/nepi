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

from test_utils import skipIfNotAlive, skipInteractive

import os
import time
import unittest

class PlanetlabTunTestCase(unittest.TestCase):
    def setUp(self):
        self.host = "nepi2.pl.sophia.inria.fr"
        self.user = "inria_nepi"

    @skipIfNotAlive
    def t_tun_create(self, host, user):

        ec = ExperimentController(exp_id = "test-un-create")
        
        node = ec.register_resource("PlanetlabNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        tun = ec.register_resource("PlanetlabTun")
        ec.set(tun, "ip4", "192.168.1.1")
        ec.set(tun, "prefix4", 24)
        ec.register_connection(tun, node)

        app = ec.register_resource("LinuxApplication")
        cmd = "ping -c3 192.168.1.1" 
        ec.set(app, "command", cmd)
        ec.register_connection(app, node)

        ec.deploy()

        ec.wait_finished(app)

        ping = ec.trace(app, 'stdout')
        expected = """3 packets transmitted, 3 received, 0% packet loss"""
        self.assertTrue(ping.find(expected) > -1)
        
        if_name = ec.get(tun, "deviceName")
        self.assertTrue(if_name.startswith("tun"))

        ec.shutdown()

    def test_tun_create(self):
        self.t_tun_create(self.host, self.user)

if __name__ == '__main__':
    unittest.main()

