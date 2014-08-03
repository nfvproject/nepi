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
        ec = ExperimentController(exp_id = "test-linux-ccnpeek")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", self.fedora_host)
        ec.set(node, "username", self.fedora_user)
        ec.set(node, "identity", self.fedora_identity)
        #ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        ccnd = ec.register_resource("LinuxCCND")
        ec.register_connection(ccnd, node)

        peek = ec.register_resource("LinuxCCNPeek")
        ec.set(peek, "contentName", "ccnx:/chunk0")
        ec.register_connection(peek, ccnd)

        poke = ec.register_resource("LinuxCCNPoke")
        ec.set(poke, "contentName", "ccnx:/chunk0")
        ec.set(poke, "content", "DATA")
        ec.register_connection(poke, ccnd)

        ec.register_condition(peek, ResourceAction.START, poke,
            ResourceState.STARTED)
 
        ec.deploy()

        ec.wait_finished(peek)

        stdout = ec.trace(peek, "stdout")
        print stdout
        expected = "DATA"
        self.assertTrue(stdout.find(expected) > -1)

        ec.shutdown()

if __name__ == '__main__':
    unittest.main()

