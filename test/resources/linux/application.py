#!/usr/bin/env python
from neco.execution.ec import ExperimentController 
from neco.execution.resource import ResourceState, ResourceAction
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
    def t_stdout(self, host, user):
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
        cmd = "echo 'HOLA'"
        ec.set(app, "command", cmd)
        ec.register_connection(app, node)

        ec.deploy()

        ec.wait_finished([app])

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(ec.state(app) == ResourceState.FINISHED)

        stdout = ec.trace(app, 'stdout')
        self.assertTrue(stdout.strip() == "HOLA")

        ec.shutdown()

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

        ec.deploy()

        ec.wait_finished([app])

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(ec.state(app) == ResourceState.FINISHED)

        stdout = ec.trace(app, 'stdout')
        size = ec.trace(app, 'stdout', attr = TraceAttr.SIZE)
        self.assertEquals(len(stdout), size)
        
        block = ec.trace(app, 'stdout', attr = TraceAttr.STREAM, block = 5, offset = 1)
        self.assertEquals(block, stdout[5:10])

        path = ec.trace(app, 'stdout', attr = TraceAttr.PATH)
        rm = ec.get_resource(app)
        p = os.path.join(rm.app_home, 'stdout')
        self.assertEquals(path, p)

        ec.shutdown()

    @skipIfNotAlive
    def t_concurrency(self, host, user):
        from neco.execution.resource import ResourceFactory
        
        ResourceFactory.register_type(LinuxNode)
        ResourceFactory.register_type(LinuxApplication)

        ec = ExperimentController()
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        apps = list()
        for i in xrange(50):
            app = ec.register_resource("LinuxApplication")
            cmd = "ping -c5 %s" % self.target 
            ec.set(app, "command", cmd)
            ec.register_connection(app, node)
            apps.append(app)

        ec.deploy()

        ec.wait_finished(apps)

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(
               all([ec.state(guid) == ResourceState.FINISHED \
                for guid in apps])
                )

        for app in apps:
            stdout = ec.trace(app, 'stdout')
            size = ec.trace(app, 'stdout', attr = TraceAttr.SIZE)
            self.assertEquals(len(stdout), size)
            
            block = ec.trace(app, 'stdout', attr = TraceAttr.STREAM, block = 5, offset = 1)
            self.assertEquals(block, stdout[5:10])

            path = ec.trace(app, 'stdout', attr = TraceAttr.PATH)
            rm = ec.get_resource(app)
            p = os.path.join(rm.app_home, 'stdout')
            self.assertEquals(path, p)

        ec.shutdown()

    @skipIfNotAlive
    def t_condition(self, host, user, depends):
        from neco.execution.resource import ResourceFactory
        
        ResourceFactory.register_type(LinuxNode)
        ResourceFactory.register_type(LinuxApplication)

        ec = ExperimentController()
        
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
        
        ec.deploy()

        ec.wait_finished(apps)

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(ec.state(server) == ResourceState.FINISHED)
        self.assertTrue(ec.state(client) == ResourceState.FINISHED)

        stdout = ec.trace(client, 'stdout')
        self.assertTrue(stdout.strip() == "HOLA")

        ec.shutdown()

    @skipIfNotAlive
    def t_http_sources(self, host, user):
        from neco.execution.resource import ResourceFactory
        
        ResourceFactory.register_type(LinuxNode)
        ResourceFactory.register_type(LinuxApplication)

        ec = ExperimentController()
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        sources = "http://nepi.inria.fr/attachment/wiki/WikiStart/pybindgen-r794.tar.gz " \
            "http://nepi.inria.fr/attachment/wiki/WikiStart/nepi_integration_framework.pdf"

        app = ec.register_resource("LinuxApplication")
        ec.set(app, "sources", sources)

        ec.register_connection(app, node)

        ec.deploy()

        ec.wait_finished([app])

        self.assertTrue(ec.state(node) == ResourceState.STARTED)
        self.assertTrue(ec.state(app) == ResourceState.FINISHED)

        err = ec.trace(app, 'http_sources_err')
        self.assertTrue(err == "")
        
        out = ec.trace(app, 'http_sources_out')
        self.assertTrue(out.find("pybindgen-r794.tar.gz") > -1)
        self.assertTrue(out.find("nepi_integration_framework.pdf") > -1)

        ec.shutdown()

    def test_stdout_fedora(self):
        self.t_stdout(self.fedora_host, self.fedora_user)

    def test_stdout_ubuntu(self):
        self.t_stdout(self.ubuntu_host, self.ubuntu_user)

    def test_ping_fedora(self):
        self.t_ping(self.fedora_host, self.fedora_user)

    def test_ping_ubuntu(self):
        self.t_ping(self.ubuntu_host, self.ubuntu_user)

    def test_concurrency_fedora(self):
        self.t_concurrency(self.fedora_host, self.fedora_user)

    def test_concurrency_ubuntu(self):
        self.t_concurrency(self.ubuntu_host, self.ubuntu_user)

    def test_condition_fedora(self):
        self.t_condition(self.fedora_host, self.fedora_user, "nc")

    def test_condition_ubuntu(self):
        self.t_condition(self.ubuntu_host, self.ubuntu_user, "netcat")

    def test_http_sources_fedora(self):
        self.t_http_sources(self.fedora_host, self.fedora_user)

    def test_http_sources_ubuntu(self):
        self.t_http_sources(self.ubuntu_host, self.ubuntu_user)


    # TODO: test compilation, sources, dependencies, etc!!!

if __name__ == '__main__':
    unittest.main()

