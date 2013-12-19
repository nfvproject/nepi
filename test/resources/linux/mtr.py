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

class LinuxMtrTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_test"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "alina"
        
        self.target = "nepi5.pl.sophia.inria.fr"

    @skipIfNotAlive
    def t_nodns(self, host, user):

        ec = ExperimentController(exp_id = "test-nodns")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        app = ec.register_resource("LinuxMtr")
        ec.set(app, "noDns", False)
        ec.set(app, "target", self.target)
        ec.register_connection(app, node)

        ec.deploy()

        ec.wait_finished(app)

        stdout = ec.trace(app, "stdout")
        self.assertTrue(stdout.find("1.") > -1)

        ec.shutdown()

    def test_nodns_fedora(self):
        self.t_nodns(self.fedora_host, self.fedora_user)

    def test_nodns_ubuntu(self):
        self.t_nodns(self.ubuntu_host, self.ubuntu_user)

if __name__ == '__main__':
    unittest.main()

