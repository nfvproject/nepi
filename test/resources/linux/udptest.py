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
from test_utils import skipIfAnyNotAlive

import os
import time
import tempfile
import unittest

class LinuxUdpTestTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_test"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "alina"
        
        self.target = "nepi5.pl.sophia.inria.fr"

    @skipIfAnyNotAlive
    def t_rtt(self, user1, host1, user2, host2):

        ec = ExperimentController(exp_id = "test-udptest-rtt")
        
        node1 = ec.register_resource("LinuxNode")
        ec.set(node1, "hostname", host1)
        ec.set(node1, "username", user1)
        ec.set(node1, "cleanHome", True)
        ec.set(node1, "cleanProcesses", True)

        server = ec.register_resource("LinuxUdpTest")
        ec.set(server, "s", True)
        ec.register_connection(server, node1)
 
        node2 = ec.register_resource("LinuxNode")
        ec.set(node2, "hostname", host2)
        ec.set(node2, "username", user2)
        ec.set(node2, "cleanHome", True)
        ec.set(node2, "cleanProcesses", True)

        client = ec.register_resource("LinuxUdpTest")
        ec.set(client, "a", True)
        ec.set(client, "target", host1)
        ec.register_connection(client, node2)

        ec.deploy()

        ec.wait_finished(client)

        stdout = ec.trace(client, "stderr")
        self.assertTrue(stdout.find("10 trials with message size 64 Bytes.") > -1)

        ec.shutdown()

    def test_rtt_fedora(self):
        self.t_rtt(self.fedora_user, self.fedora_host, self.fedora_user, 
                self.target)

    def test_rtt_ubuntu(self):
        self.t_rtt(self.ubuntu_user, self.ubuntu_host, self.fedora_user,
                self.target)

if __name__ == '__main__':
    unittest.main()

