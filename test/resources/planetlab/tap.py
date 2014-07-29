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

from test_utils import skipIfNotAlive

import os
import time
import unittest

class PlanetlabTapTestCase(unittest.TestCase):
    def setUp(self):
        self.host = "planetlab1.informatik.uni-erlangen.de"
        self.user = "inria_nepi"
        self.identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])
        self.netblock = "192.168.3"
        #self.host = "nepi2.pl.sophia.inria.fr"
        #self.user = "inria_nepi"
        #self.identity = None
        #self.netblock = "192.168.1"

    @skipIfNotAlive
    def t_tap_create(self, host, user, identity):

        ec = ExperimentController(exp_id = "test-tap-create")
        
        node = ec.register_resource("PlanetlabNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "identity", identity)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        tap = ec.register_resource("PlanetlabTap")
        ec.set(tap, "ip4", "%s.1" % self.netblock)
        ec.set(tap, "prefix4", 24)
        ec.register_connection(tap, node)

        app = ec.register_resource("LinuxApplication")
        cmd = "ping -c3 %s.1" % self.netblock
        ec.set(app, "command", cmd)
        ec.register_connection(app, node)

        ec.deploy()

        ec.wait_finished(app)

        ping = ec.trace(app, 'stdout')
        expected = """3 packets transmitted, 3 received, 0% packet loss"""
        self.assertTrue(ping.find(expected) > -1)
        
        if_name = ec.get(tap, "deviceName")
        self.assertTrue(if_name.startswith("tap"))

        ec.shutdown()

    def test_tap_create(self):
        self.t_tap_create(self.host, self.user, self.identity)

if __name__ == '__main__':
    unittest.main()

