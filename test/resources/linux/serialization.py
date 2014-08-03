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
from nepi.execution.resource import ResourceState, ResourceAction
from nepi.execution.trace import TraceAttr

from test_utils import skipIfNotAlive, skipInteractive

import os
import shutil
import time
import tempfile
import unittest

class LinuxSerializationTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_nepi"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "inria_nepi"
        
        self.target = "nepi5.pl.sophia.inria.fr"

    @skipIfNotAlive
    def t_condition_serialize(self, host, user, depends):

        dirpath = tempfile.mkdtemp()

        ec = ExperimentController(exp_id="test-condition-serial")
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        server = ec.register_resource("LinuxApplication")
        cmd = "echo 'HOLA' | nc -l 3333"
        ec.set(server, "command", cmd)
        ec.set(server, "depends", depends)
        ec.register_connection(server, node)

        client = ec.register_resource("LinuxApplication")
        cmd = "nc 127.0.0.1 3333"
        ec.set(client, "command", cmd)
        ec.register_connection(client, node)

        ec.register_condition(client, ResourceAction.START, server, ResourceState.STARTED)

        apps = [client, server]
        
        filepath = ec.save(dirpath)
        
        ec.deploy()

        ec.wait_finished(apps)

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(ec.state(server) == ResourceState.STOPPED)
        self.assertTrue(ec.state(client) == ResourceState.STOPPED)

        stdout = ec.trace(client, "stdout")
        self.assertTrue(stdout.strip() == "HOLA")

        ec.shutdown()

        # Load serialized experiment
        ec2 = ExperimentController.load(filepath)
        
        ec2.deploy()
        ec2.wait_finished(apps)
        
        self.assertEquals(len(ec.resources), len(ec2.resources))
        
        self.assertTrue(ec2.state(node) == ResourceState.STARTED)
        self.assertTrue(ec2.state(server) == ResourceState.STOPPED)
        self.assertTrue(ec2.state(client) == ResourceState.STOPPED)

        stdout = ec2.trace(client, "stdout")

        self.assertTrue(stdout.strip() == "HOLA")
        
        ec2.shutdown()

        shutil.rmtree(dirpath)

    def test_condition_serialize_fedora(self):
        self.t_condition_serialize(self.fedora_host, self.fedora_user, "nc")

    def test_condition_serialize_ubuntu(self):
        self.t_condition_serialize(self.ubuntu_host, self.ubuntu_user, "netcat")

if __name__ == '__main__':
    unittest.main()

