#!/usr/bin/env python
from neco.resources.linux.ssh_api import SSHApiFactory
from neco.util.sshfuncs import RUNNING, FINISHED

import os
import time
import tempfile
import unittest

def skipIfNotAlive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        host = args[1]
        user = args[2]

        api = SSHApiFactory.get_api(host, user)
        if not api.is_alive():
            print "*** WARNING: Skipping test %s: Node %s is not alive\n" % (name, host)
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

class SSHApiTestCase(unittest.TestCase):
    def setUp(self):
        self.host_fedora = 'nepi2.pl.sophia.inria.fr'
        self.user_fedora = 'inria_nepi'

        self.host_ubuntu = 'roseval.pl.sophia.inria.fr'
        self.user_ubuntu = 'alina'
        
        self.target = 'nepi5.pl.sophia.inria.fr'
        self.home = '${HOME}/test-app'

    @skipIfNotAlive
    def t_xterm(self, host, user):
        api = SSHApiFactory.get_api(host, user)

        api.enable_x11 = True

        api.install('xterm')

        out = api.execute('xterm')

        api.uninstall('xterm')

        self.assertEquals(out, "")

    @skipIfNotAlive
    def t_execute(self, host, user):
        api = SSHApiFactory.get_api(host, user)
        
        command = "ping -qc3 %s" % self.target
        out, err = api.execute(command)

        expected = """3 packets transmitted, 3 received, 0% packet loss"""

        self.assertTrue(out.find(expected) > 0)

    @skipIfNotAlive
    def t_run(self, host, user):
        api = SSHApiFactory.get_api(host, user)
        
        api.mkdir(self.home, clean = True)
        
        command = "ping %s" % self.target
        dst = os.path.join(self.home, "app.sh")
        api.upload(command, dst)
        
        cmd = "bash ./app.sh"
        api.run(cmd, self.home)
        pid, ppid = api.checkpid(self.home)

        status = api.status(pid, ppid)
        self.assertTrue(status, RUNNING)

        api.kill(pid, ppid)
        status = api.status(pid, ppid)
        self.assertTrue(status, FINISHED)

        api.rmdir(self.home)

    @skipIfNotAlive
    def t_install(self, host, user):
        api = SSHApiFactory.get_api(host, user)
        
        api.mkdir(self.home, clean = True)

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
        api.upload(prog, dst)

        # install gcc
        api.install('gcc')

        # compile the program using gcc
        command = "cd %s; gcc -Wall hello.c -o hello" % self.home
        out = api.execute(command)

        # execute the program and get the output from stout
        command = "%s/hello" % self.home
        out, err = api.execute(command)

        # execute the program and get the output from a file
        command = "%s/hello > %s/hello.out" % (self.home, self.home)
        api.execute(command)

        # retrieve the output file 
        src = os.path.join(self.home, "hello.out")
        f = tempfile.NamedTemporaryFile(delete=False)
        dst = f.name
        api.download(src, dst)
        f.close()

        api.uninstall('gcc')
        api.rmdir(self.home)

        self.assertEquals(out, "Hello, world!\n")

        f = open(dst, "r")
        out = f.read()
        f.close()
        
        self.assertEquals(out, "Hello, world!\n")

    def test_execute_fedora(self):
        self.t_execute(self.host_fedora, self.user_fedora)

    def test_execute_ubuntu(self):
        self.t_execute(self.host_ubuntu, self.user_ubuntu)

    def test_run_fedora(self):
        self.t_run(self.host_fedora, self.user_fedora)

    def test_run_ubuntu(self):
        self.t_run(self.host_ubuntu, self.user_ubuntu)

    def test_intall_fedora(self):
        self.t_install(self.host_fedora, self.user_fedora)

    def test_install_ubuntu(self):
        self.t_install(self.host_ubuntu, self.user_ubuntu)
    
    @skipInteractive
    def test_xterm_ubuntu(self):
        """ Interactive test. Should not run automatically """
        self.t_xterm(self.host_ubuntu, self.user_ubuntu)


if __name__ == '__main__':
    unittest.main()

