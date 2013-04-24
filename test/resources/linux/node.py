#!/usr/bin/env python
from neco.resources.linux.node import LinuxNode
from neco.util.sshfuncs import RUNNING, FINISHED

import os
import time
import tempfile
import unittest

def skipIfNotAlive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        node = args[1]

        if not node.is_alive():
            print "*** WARNING: Skipping test %s: Node %s is not alive\n" % (
                name, node.get("hostname"))
            return

        return func(*args, **kwargs)
    
    return wrapped

def skipInteractive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        mode = os.environ.get("NEPI_INTERACTIVE", False) in ['True', 'true', 'yes', 'YES']
        if not mode:
            print "*** WARNING: Skipping test %s: Interactive mode off \n" % name
            return

        return func(*args, **kwargs)
    
    return wrapped

class DummyEC(object):
    pass

class LinuxNodeTestCase(unittest.TestCase):
    def setUp(self):
        host = 'nepi2.pl.sophia.inria.fr'
        user = 'inria_nepi'
        self.node_fedora = self.create_node(host, user)

        host = 'roseval.pl.sophia.inria.fr'
        user = 'alina'
        self.node_ubuntu = self.create_node(host, user)
        
        self.target = 'nepi5.pl.sophia.inria.fr'
        self.home = '/tmp/nepi-home/test-app'

    def create_node(self, host, user):
        ec = DummyEC()

        node = LinuxNode(ec, 1)
        node.set("hostname", host)
        node.set("username", user)

        return node

    @skipIfNotAlive
    def t_xterm(self, node):
        node.install_packages('xterm')

        (out, err), proc = node.execute('xterm', forward_x11 = True)
        
        self.assertEquals(out, "")

        (out, err), proc = node.remove_packages('xterm')
        
        self.assertEquals(out, "")

    @skipIfNotAlive
    def t_execute(self, node):
        command = "ping -qc3 %s" % self.target
        
        (out, err), proc = node.execute(command)

        expected = """3 packets transmitted, 3 received, 0% packet loss"""

        self.assertTrue(out.find(expected) > 0)

    @skipIfNotAlive
    def t_run(self, node):
        node.mkdir(self.home, clean = True)
        
        command = "ping %s" % self.target
        dst = os.path.join(self.home, "app.sh")
        node.upload(command, dst)
        
        cmd = "bash ./app.sh"
        node.run(cmd, self.home)
        pid, ppid = node.checkpid(self.home)

        status = node.status(pid, ppid)
        self.assertTrue(status, RUNNING)

        node.kill(pid, ppid)
        status = node.status(pid, ppid)
        self.assertTrue(status, FINISHED)
        
        (out, err), proc = node.check_run_output(self.home)

        expected = """64 bytes from"""

        self.assertTrue(out.find(expected) > 0)

        node.rmdir(self.home)

    @skipIfNotAlive
    def t_install(self, node):
        node.mkdir(self.home, clean = True)

        prog = """#include <stdio.h>

int
main (void)
{
    printf ("Hello, world!\\n");
    return 0;
}
"""
        # upload the test program
        dst = os.path.join(self.home, "hello.c")
        node.upload(prog, dst)

        # install gcc
        node.install_packages('gcc')

        # compile the program using gcc
        command = "cd %s; gcc -Wall hello.c -o hello" % self.home
        (out, err), proc = node.execute(command)

        # execute the program and get the output from stdout
        command = "%s/hello" % self.home
        (out, err), proc = node.execute(command)

        self.assertEquals(out, "Hello, world!\n")

        # execute the program and get the output from a file
        command = "%(home)s/hello > %(home)s/hello.out" % {'home':self.home}
        (out, err), proc = node.execute(command)

        # retrieve the output file 
        src = os.path.join(self.home, "hello.out")
        f = tempfile.NamedTemporaryFile(delete=False)
        dst = f.name
        node.download(src, dst)
        f.close()

        node.remove_packages('gcc')
        node.rmdir(self.home)

        f = open(dst, "r")
        out = f.read()
        f.close()
        
        self.assertEquals(out, "Hello, world!\n")

    def test_execute_fedora(self):
        self.t_execute(self.node_fedora)

    def test_execute_ubuntu(self):
        self.t_execute(self.node_ubuntu)

    def test_run_fedora(self):
        self.t_run(self.node_fedora)

    def test_run_ubuntu(self):
        self.t_run(self.node_ubuntu)

    def test_intall_fedora(self):
        self.t_install(self.node_fedora)

    def test_install_ubuntu(self):
        self.t_install(self.node_ubuntu)
    
    @skipInteractive
    def test_xterm_ubuntu(self):
        """ Interactive test. Should not run automatically """
        self.t_xterm(self.node_ubuntu)


if __name__ == '__main__':
    unittest.main()

