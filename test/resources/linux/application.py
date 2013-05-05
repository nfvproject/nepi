#!/usr/bin/env python
from neco.execution.ec import ExperimentController 
from neco.execution.resource import ResourceState
from neco.execution.trace import TraceAttr
from neco.resources.linux.node import LinuxNode
from neco.resources.linux.application import LinuxApplication

from test_utils import skipIfNotAlive

import os
import time
import tempfile
import unittest

class LinuxApplicationTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = 'nepi2.pl.sophia.inria.fr'
        self.fedora_user = 'inria_nepi'

        self.ubuntu_host = 'roseval.pl.sophia.inria.fr'
        self.ubuntu_user = 'alina'
        
        self.target = 'nepi5.pl.sophia.inria.fr'

    @skipIfNotAlive
    def t_ping(self, host, user):
        from neco.execution.resource import ResourceFactory
        
        ResourceFactory.register_type(LinuxNode)
        ResourceFactory.register_type(LinuxApplication)

        ec = ExperimentController()
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        app = ec.register_resource("LinuxApplication")
        cmd = "ping -c5 %s" % self.target 
        ec.set(app, "command", cmd)
        
        ec.register_connection(app, node)

        try:
            ec.deploy()

            while not ec.state(app) == ResourceState.FINISHED:
                time.sleep(0.5)

            self.assertTrue(ec.state(node) == ResourceState.STARTED)
            self.assertTrue(ec.state(app) == ResourceState.FINISHED)

            stdout = ec.trace(app, 'stdout')
            size = ec.trace(app, 'stdout', attr = TraceAttr.SIZE)
            self.assertEquals(len(stdout), size)
            
            block = ec.trace(app, 'stdout', attr = TraceAttr.STREAM, block = 5, offset = 1)
            self.assertEquals(block, stdout[5:10])

            path = ec.trace(app, 'stdout', attr = TraceAttr.PATH)
            rm = ec.get_resource(app)
            p = os.path.join(rm.home, 'stdout')
            self.assertEquals(path, p)

        finally:
            ec.shutdown()

    def test_deploy_fedora(self):
        self.t_ping(self.fedora_host, self.fedora_user)

    def test_deploy_ubuntu(self):
        self.t_ping(self.ubuntu_host, self.ubuntu_user)


if __name__ == '__main__':
    unittest.main()

