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

class LinuxCCNPingTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_test"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "alina"
        
        self.target = "nepi5.pl.sophia.inria.fr"

    @skipIfAnyNotAlive
    def t_count(self, user1, host1, user2, host2):

        ec = ExperimentController(exp_id = "test-ccn-ping-count")
        
        node1 = ec.register_resource("LinuxNode")
        ec.set(node1, "hostname", host1)
        ec.set(node1, "username", user1)
        ec.set(node1, "cleanHome", True)
        ec.set(node1, "cleanProcesses", True)

        ccnd1 = ec.register_resource("LinuxCCND")
        ec.register_connection(ccnd1, node1)

        entry1 = ec.register_resource("LinuxFIBEntry")
        ec.set(entry1, "host", host2)
        ec.register_connection(entry1, ccnd1)
 
        server = ec.register_resource("LinuxCCNPingServer")
        ec.set(server, "prefix", "ccnx:/test")
        ec.register_connection(server, ccnd1)
 
        node2 = ec.register_resource("LinuxNode")
        ec.set(node2, "hostname", host2)
        ec.set(node2, "username", user2)
        ec.set(node2, "cleanHome", True)
        ec.set(node2, "cleanProcesses", True)

        ccnd2 = ec.register_resource("LinuxCCND")
        ec.register_connection(ccnd2, node2)

        entry2 = ec.register_resource("LinuxFIBEntry")
        ec.set(entry2, "host", host1)
        ec.register_connection(entry2, ccnd2)
 
        client = ec.register_resource("LinuxCCNPing")
        ec.set(client, "c", 15)
        ec.set(client, "prefix", "ccnx:/test")
        ec.register_connection(client, ccnd2)
        ec.register_connection(client, server)

        ec.deploy()

        ec.wait_finished(client)

        stdout = ec.trace(client, "stdout")
        expected = "15 Interests transmitted"
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

    def test_count_fedora(self):
        self.t_count(self.fedora_user, self.fedora_host, self.fedora_user, 
                self.target)

    def test_count_ubuntu(self):
        self.t_count(self.ubuntu_user, self.ubuntu_host, self.fedora_user,
                self.target)

if __name__ == '__main__':
    unittest.main()

