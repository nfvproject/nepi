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

from nepi.execution.resource import ResourceState, ResourceAction 
from nepi.execution.ec import ExperimentController 
from test_utils import skipIfAnyNotAlive

import os
import time
import tempfile
import unittest

class LinuxCCNPeekTestCase(unittest.TestCase):
    def setUp(self):
        #self.fedora_host = "nepi2.pl.sophia.inria.fr"
        #self.fedora_user = "inria_nepi"
        self.fedora_identity = "%s/.ssh/id_rsa" % (os.environ['HOME'])

        self.fedora_host = "mimas.inria.fr"
        self.fedora_user = "aquereil"

    @skipIfAnyNotAlive
    def test_ccnpeek(self):
        ec = ExperimentController(exp_id = "test-linux-ccncat")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        #ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        ccnd = ec.register_resource("LinuxCCND")
        ec.register_connection(ccnd, node)

        # REPO file is in test/resources/linux/ns3/ccn/repoFile1
        repofile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..", "ns3", "ccn", "repoFile1")

        ## Register a repository in node 1
        ccnr = ec.register_resource("LinuxCCNR")
        ec.set(ccnr, "repoFile1", repofile)
        ec.register_connection(ccnr, ccnd)

        ccncat = ec.register_resource("LinuxCCNCat")
        ec.set(ccncat, "contentName", "ccnx:/test/bunny.ts")
        ec.register_connection(ccncat, ccnd)

        ec.deploy()

        ec.wait_finished(ccncat)

        expected = 2873956
        stdout = ec.trace(ccncat, "stdout")
        self.assertTrue(len(stdout) == expected , stdout)

        ec.shutdown()

if __name__ == '__main__':
    unittest.main()

