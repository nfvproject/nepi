#!/usr/bin/env python
from neco.resources.base.linux_node import LinuxNode
from neco.design.box import Box
from neco.util.sshfuncs import RUNNING, FINISHED

import os.path
import time
import unittest

class DummyEC(object):
    pass

class LinuxBoxTestCase(unittest.TestCase):
    def test_execute(self):
        box = Box()
        ec = DummyEC()

        node = LinuxNode(box, ec)
        node.host = 'nepi2.pl.sophia.inria.fr'
        node.user = 'inria_nepi'

        self.assertEquals(node.pm, "yum")
        self.assertTrue(node.is_alive())

        command = "ping -qc3 nepi5.pl.sophia.inria.fr"
        out = node.execute(command)

        expected = """3 packets transmitted, 3 received, 0% packet loss"""

        self.assertTrue(out.find(expected) > 0)

    def test_run(self):
        box = Box()
        ec = DummyEC()

        node = LinuxNode(box, ec)
        node.host = 'nepi2.pl.sophia.inria.fr'
        node.user = 'inria_nepi'

        home = '${HOME}/test-app'
        node.mkdir(home, clean = True)
        
        command = "ping nepi5.pl.sophia.inria.fr"
        dst = os.path.join(home, "app.sh")
        node.upload(command, dst)
        
        cmd = "bash ./app.sh"
        node.run(cmd, home)
        pid, ppid = node.checkpid(home)

        status = node.status(pid, ppid)
        self.assertTrue(status, RUNNING)

        node.kill(pid, ppid)
        status = node.status(pid, ppid)
        self.assertTrue(status, FINISHED)

        node.rmdir(home)

    def test_install(self):
        box = Box()
        ec = DummyEC()

        node = LinuxNode(box, ec)
        node.host = 'nepi2.pl.sophia.inria.fr'
        node.user = 'inria_nepi'

        self.assertEquals(node.pm, "yum")
        self.assertTrue(node.is_alive())

        home = '${HOME}/test-app'
        node.mkdir(home, clean = True)

        prog = """#include <stdio.h>

int
main (void)
{
    printf ("Hello, world!\\n");
    return 0;
}
"""
        dst = os.path.join(home, "hello.c")
        node.upload(prog, dst)

        node.install('gcc')

        command = "cd ${HOME}/test-app; gcc -Wall hello.c -o hello"
        out = node.execute(command)

        command = "${HOME}/test-app/hello"
        out = node.execute(command)

        self.assertEquals(out, "Hello, world!\n")

        node.uninstall('gcc')
        node.rmdir(home)

if __name__ == '__main__':
    unittest.main()

