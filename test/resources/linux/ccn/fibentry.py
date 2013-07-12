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
import tempfile
import unittest

class LinuxFIBEntryTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_nepi"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "alina"
        
        self.target = "nepi5.pl.sophia.inria.fr"

    @skipIfNotAlive
    def t_traces(self, host, user):

        ec = ExperimentController(exp_id = "test-fib-traces")
        
        node1 = ec.register_resource("LinuxNode")
        ec.set(node1, "hostname", host)
        ec.set(node1, "username", user)
        #ec.set(node1, "cleanHome", True)
        ec.set(node1, "cleanProcesses", True)

        ccnd1 = ec.register_resource("LinuxCCND")
        ec.register_connection(ccnd1, node1)

        entry1 = ec.register_resource("LinuxFIBEntry")
        ec.set(entry1, "host", self.target)
        ec.enable_trace(entry1, "ping")
        ec.enable_trace(entry1, "mtr")
        ec.register_connection(entry1, ccnd1)
 
        node2 = ec.register_resource("LinuxNode")
        ec.set(node2, "hostname", self.target)
        ec.set(node2, "username", self.fedora_user)
        ec.set(node2, "cleanHome", True)
        ec.set(node2, "cleanProcesses", True)

        ccnd2 = ec.register_resource("LinuxCCND")
        ec.register_connection(ccnd2, node2)

        entry2 = ec.register_resource("LinuxFIBEntry")
        ec.set(entry2, "host", host)
        ec.register_connection(entry2, ccnd2)

        ec.deploy()

        ec.wait_started([ccnd1, ccnd2])

        stdout = ec.trace(entry1, "ping")
        expected = "icmp_seq=1" 
        self.assertTrue(stdout.find(expected) > -1)

        stdout = ec.trace(entry1, "mtr")
        expected = "1." 
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

    def test_traces_fedora(self):
        self.t_traces(self.fedora_host, self.fedora_user)

    def test_traces_ubuntu(self):
        self.t_traces(self.ubuntu_host, self.ubuntu_user)

if __name__ == '__main__':
    unittest.main()

