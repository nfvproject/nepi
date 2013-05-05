#!/usr/bin/env python
from neco.execution.ec import ExperimentController 
from neco.execution.resource import ResourceState
from neco.resources.linux.node import LinuxNode
from neco.resources.linux.interface import LinuxInterface
from neco.resources.linux.channel import LinuxChannel
from neco.util.sshfuncs import RUNNING, FINISHED

from test_utils import skipIfNotAlive

import os
import time
import tempfile
import unittest

class LinuxInterfaceTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = 'nepi2.pl.sophia.inria.fr'
        self.fedora_user = 'inria_nepi'

        self.ubuntu_host = 'roseval.pl.sophia.inria.fr'
        self.ubuntu_user = 'alina'

    @skipIfNotAlive
    def t_deploy(self, host, user):
        from neco.execution.resource import ResourceFactory
        
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

        try:
            ec.deploy()

            while not all([ ec.state(guid) == ResourceState.STARTED \
                    for guid in [node, iface]]):
                time.sleep(0.5)

            self.assertTrue(ec.state(node) == ResourceState.STARTED)
            self.assertTrue(ec.state(iface) == ResourceState.STARTED)
            self.assertTrue(ec.get(iface, "deviceName") == "eth0")

        finally:
            ec.shutdown()

    def test_deploy_fedora(self):
        self.t_deploy(self.fedora_host, self.fedora_user)

    def test_deploy_ubuntu(self):
        self.t_deploy(self.ubuntu_host, self.ubuntu_user)


if __name__ == '__main__':
    unittest.main()

