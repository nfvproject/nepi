#!/usr/bin/env python
from neco.resources.linux.node import LinuxNode
from neco.design.box import Box
from neco.util.sshfuncs import RUNNING, FINISHED

import os.path
import time
import tempfile
import unittest


class DummyEC(object):
    pass

class LinuxBoxTestCase(unittest.TestCase):
    def setUp(self):
        host = 'nepi2.pl.sophia.inria.fr'
        user = 'inria_nepi'
        self.node_fedora = self.create_node(host, user)

        host = 'roseval.pl.sophia.inria.fr'
        user = 'alina'
        self.node_ubuntu = self.create_node(host, user)
        
        self.target = 'nepi5.pl.sophia.inria.fr'
        self.home = '${HOME}/test-app'

    def create_node(self, host, user):
        box = Box()
        ec = DummyEC()

        node = LinuxNode(box, ec)
        node.host = host
        node.user = user

        return node

    def t_xterm(self, node):
        if not node.is_alive():
            print "*** WARNING: Skipping test: Node %s is not alive\n" % (node.host)
            return 

        node.enable_x11 = True

        node.install('xterm')

        out = node.execute('xterm')

        node.uninstall('xterm')

        self.assertEquals(out, "")

    def t_execute(self, node, target):
        if not node.is_alive():
            print "*** WARNING: Skipping test: Node %s is not alive\n" % (node.host)
            return 

        command = "ping -qc3 %s" % target
        out = node.execute(command)

        expected = """3 packets transmitted, 3 received, 0% packet loss"""

        self.assertTrue(out.find(expected) > 0)

    def t_run(self, node, target):
        if not node.is_alive():
            print "*** WARNING: Skipping test: Node %s is not alive\n" % (node.host)
            return

        node.mkdir(self.home, clean = True)
        
        command = "ping %s" % target
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

        node.rmdir(self.home)

    def t_install(self, node):
        if not node.is_alive():
            print "*** WARNING: Skipping test: Node %s is not alive\n" % (node.host)
            return

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
        node.install('gcc')

        # compile the program using gcc
        command = "cd %s; gcc -Wall hello.c -o hello" % self.home
        out = node.execute(command)

        # execute the program and get the output from stout
        command = "%s/hello" % self.home
        out = node.execute(command)

        # execute the program and get the output from a file
        command = "%s/hello > %s/hello.out" % (self.home, self.home)
        node.execute(command)

        # retrieve the output file 
        src = os.path.join(self.home, "hello.out")
        f = tempfile.NamedTemporaryFile(delete=False)
        dst = f.name
        node.download(src, dst)
        f.close()

        node.uninstall('gcc')
        node.rmdir(self.home)

        self.assertEquals(out, "Hello, world!\n")

        f = open(dst, "r")
        out = f.read()
        f.close()
        
        self.assertEquals(out, "Hello, world!\n")

    def test_execute_fedora(self):
        self.t_execute(self.node_fedora, self.target)

    def test_execute_ubuntu(self):
        self.t_execute(self.node_ubuntu, self.target)

    def test_run_fedora(self):
        self.t_run(self.node_fedora, self.target)

    def test_run_ubuntu(self):
        self.t_run(self.node_ubuntu, self.target)

    def test_intall_fedora(self):
        self.t_install(self.node_fedora)

    def test_install_ubuntu(self):
        self.t_install(self.node_ubuntu)

    def xtest_xterm_fedora(self):
        """ PlanetLab doesn't currently support X11 forwarding.
        Interactive test. Should not run automatically """
        self.t_xterm(self.node_fedora)

    def xtest_xterm_ubuntu(self):
        """ Interactive test. Should not run automatically """
        self.t_xterm(self.node_ubuntu)


if __name__ == '__main__':
    unittest.main()

