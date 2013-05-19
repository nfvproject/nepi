#!/usr/bin/env python
from nepi.resources.linux.node import LinuxNode
from nepi.util.sshfuncs import RUNNING, FINISHED

from test_utils import skipIfNotAlive, skipInteractive, create_node

import os
import time
import tempfile
import unittest

class LinuxNodeTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = 'nepi2.pl.sophia.inria.fr'
        self.fedora_user = 'inria_nepi'

        self.ubuntu_host = 'roseval.pl.sophia.inria.fr'
        self.ubuntu_user = 'alina'
        
        self.target = 'nepi5.pl.sophia.inria.fr'

    @skipIfNotAlive
    def t_xterm(self, host, user):
        node, ec = create_node(host, user)

        node.install_packages('xterm')

        (out, err), proc = node.execute('xterm', forward_x11 = True)
        
        self.assertEquals(out, "")

        (out, err), proc = node.remove_packages('xterm')
        
        self.assertEquals(out, "")

    @skipIfNotAlive
    def t_execute(self, host, user):
        node, ec = create_node(host, user)

        command = "ping -qc3 %s" % self.target
        
        (out, err), proc = node.execute(command)

        expected = """3 packets transmitted, 3 received, 0% packet loss"""

        self.assertTrue(out.find(expected) > 0)

    @skipIfNotAlive
    def t_run(self, host, user):
        node, ec = create_node(host, user)
        
        app_home = os.path.join(node.exp_home, "my-app")
        node.mkdir(app_home, clean = True)
        
        command = "ping %s" % self.target
        node.run(command, app_home)
        pid, ppid = node.checkpid(app_home)

        status = node.status(pid, ppid)
        self.assertTrue(status, RUNNING)

        node.kill(pid, ppid)
        status = node.status(pid, ppid)
        self.assertTrue(status, FINISHED)
        
        (out, err), proc = node.check_output(app_home, "stdout")

        expected = """64 bytes from"""

        self.assertTrue(out.find(expected) > 0)

        node.rmdir(app_home)

    @skipIfNotAlive
    def t_install(self, host, user):
        node, ec = create_node(host, user)

        (out, err), proc = node.install_packages('gcc')
        self.assertEquals(out, "")

        (out, err), proc = node.remove_packages('gcc')
        
        self.assertEquals(out, "")


    @skipIfNotAlive
    def t_compile(self, host, user):
        node, ec = create_node(host, user)

        app_home = os.path.join(node.exp_home, "my-app")
        node.mkdir(app_home, clean = True)

        prog = """#include <stdio.h>

int
main (void)
{
    printf ("Hello, world!\\n");
    return 0;
}
"""
        # upload the test program
        dst = os.path.join(app_home, "hello.c")
        node.upload(prog, dst, text = True)

        # install gcc
        node.install_packages('gcc')

        # compile the program using gcc
        command = "cd %s; gcc -Wall hello.c -o hello" % app_home
        (out, err), proc = node.execute(command)

        # execute the program and get the output from stdout
        command = "%s/hello" % app_home 
        (out, err), proc = node.execute(command)

        self.assertEquals(out, "Hello, world!\n")

        # execute the program and get the output from a file
        command = "%(home)s/hello > %(home)s/hello.out" % {
                'home': app_home}
        (out, err), proc = node.execute(command)

        # retrieve the output file 
        src = os.path.join(app_home, "hello.out")
        f = tempfile.NamedTemporaryFile(delete=False)
        dst = f.name
        node.download(src, dst)
        f.close()

        node.remove_packages('gcc')
        node.rmdir(app_home)

        f = open(dst, "r")
        out = f.read()
        f.close()
        
        self.assertEquals(out, "Hello, world!\n")

    def test_execute_fedora(self):
        self.t_execute(self.fedora_host, self.fedora_user)

    def test_execute_ubuntu(self):
        self.t_execute(self.ubuntu_host, self.ubuntu_user)

    def test_run_fedora(self):
        self.t_run(self.fedora_host, self.fedora_user)

    def test_run_ubuntu(self):
        self.t_run(self.ubuntu_host, self.ubuntu_user)

    def test_intall_fedora(self):
        self.t_install(self.fedora_host, self.fedora_user)

    def test_install_ubuntu(self):
        self.t_install(self.ubuntu_host, self.ubuntu_user)

    def test_compile_fedora(self):
        self.t_compile(self.fedora_host, self.fedora_user)

    def test_compile_ubuntu(self):
        self.t_compile(self.ubuntu_host, self.ubuntu_user)
    
    @skipInteractive
    def test_xterm_ubuntu(self):
        """ Interactive test. Should not run automatically """
        self.t_xterm(self.ubuntu_host, self.ubuntu_user)


if __name__ == '__main__':
    unittest.main()

