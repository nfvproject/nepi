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
from nepi.execution.resource import ResourceState
from nepi.resources.linux.node import LinuxNode
from nepi.resources.linux.interface import LinuxInterface
from nepi.resources.linux.channel import LinuxChannel

from test_utils import skipIfNotAlive

import os
import time
import tempfile
import unittest

class LinuxInterfaceTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_nepi"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "alina"

    @skipIfNotAlive
    def t_deploy(self, host, user):
        from nepi.execution.resource import ResourceFactory
        
        ResourceFactory.register_type(LinuxNode)
        ResourceFactory.register_type(LinuxInterface)
        ResourceFactory.register_type(LinuxChannel)

        ec = ExperimentController()
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)

        iface = ec.register_resource("LinuxInterface")
        chan = ec.register_resource("LinuxChannel")

        ec.register_connection(iface, node)
        ec.register_connection(iface, chan)

        ec.deploy()

        while not all([ ec.state(guid) == ResourceState.STARTED \
                for guid in [node, iface]]):
            time.sleep(0.5)

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(ec.state(iface) == ResourceState.STARTED)
        self.assertTrue(ec.get(iface, "deviceName") == "eth0")

        ec.shutdown()

    def test_deploy_fedora(self):
        self.t_deploy(self.fedora_host, self.fedora_user)

    def test_deploy_ubuntu(self):
        self.t_deploy(self.ubuntu_host, self.ubuntu_user)


if __name__ == '__main__':
    unittest.main()

