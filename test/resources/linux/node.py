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


from nepi.resources.linux.node import LinuxNode, ExitCode
from nepi.util.sshfuncs import ProcStatus

from test_utils import skipIfNotAlive, skipInteractive, create_node

import os
import time
import tempfile
import unittest

class LinuxNodeTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_host = "planetlab2.u-strasbg.fr"
        self.fedora_user = "inria_nepi"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "alina"
        
        self.target = "nepi5.pl.sophia.inria.fr"

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
        pid, ppid = node.getpid(app_home)

        status = node.status(pid, ppid)
        self.assertTrue(status, ProcStatus.RUNNING)

        node.kill(pid, ppid)
        status = node.status(pid, ppid)
        self.assertTrue(status, ProcStatus.FINISHED)
        
        (out, err), proc = node.check_output(app_home, "stdout")

        expected = """64 bytes from"""

        self.assertTrue(out.find(expected) > 0)

        node.rmdir(app_home)

    @skipIfNotAlive
    def t_exitcode_ok(self, host, user):
        command = "echo 'OK!'"
        
        node, ec = create_node(host, user)
         
        app_home = os.path.join(node.exp_home, "my-app")
        node.mkdir(app_home, clean = True)
         
        (out, err), proc = node.run_and_wait(command, app_home,
            shfile = "cmd.sh",
            pidfile = "pid",
            ecodefile = "exitcode",
            stdout = "stdout", 
            stderr = "stderr",
            raise_on_error = True)
 
        # get the pid of the process
        ecode = node.exitcode(app_home)
        self.assertEquals(ecode, ExitCode.OK)

    @skipIfNotAlive
    def t_exitcode_kill(self, host, user):
        node, ec = create_node(host, user)
         
        app_home = os.path.join(node.exp_home, "my-app")
        node.mkdir(app_home, clean = True)
       
        # Upload command that will not finish
        command = "ping localhost"
        (out, err), proc = node.upload_command(command, app_home, 
            shfile = "cmd.sh",
            ecodefile = "exitcode")

        (out, err), proc = node.run(command, app_home,
            pidfile = "pidfile",
            stdout = "stdout", 
            stderr = "stderr")
 
        # Just wait to make sure the ping started
        time.sleep(5)

        # The process is still running, so no retfile has been created yet
        ecode = node.exitcode(app_home)
        self.assertEquals(ecode, ExitCode.FILENOTFOUND)
        
        (out, err), proc = node.check_errors(app_home)
        self.assertEquals(err, "")
        
        # Now kill the app
        pid, ppid = node.getpid(app_home)
        node.kill(pid, ppid)
         
        (out, err), proc = node.check_errors(app_home)
        self.assertEquals(err, "")

    @skipIfNotAlive
    def t_exitcode_error(self, host, user):
        # Try to execute a command that doesn't exist
        command = "unexistent-command"
        
        node, ec = create_node(host, user)
         
        app_home = os.path.join(node.exp_home, "my-app")
        node.mkdir(app_home, clean = True)
         
        (out, err), proc = node.run_and_wait(command, app_home,
            shfile = "cmd.sh",
            pidfile = "pid",
            ecodefile = "exitcode",
            stdout = "stdout", 
            stderr = "stderr",
            raise_on_error = False)
 
        # get the pid of the process
        ecode = node.exitcode(app_home)

        # bash erro 127 - command not found
        self.assertEquals(ecode, 127)
 
        (out, err), proc = node.check_errors(app_home)

        self.assertEquals(err.strip(), "./cmd.sh: line 1: unexistent-command: command not found")

    @skipIfNotAlive
    def t_install(self, host, user):
        node, ec = create_node(host, user)

        (out, err), proc = node.mkdir(node.node_home, clean = True)
        self.assertEquals(err, "")

        (out, err), proc = node.install_packages("gcc", node.node_home)
        self.assertEquals(err, "")

        (out, err), proc = node.remove_packages("gcc", node.node_home)
        self.assertEquals(err, "")

        (out, err), proc = node.rmdir(node.exp_home)
        self.assertEquals(err, "")

    @skipIfNotAlive
    def t_xterm(self, host, user):
        node, ec = create_node(host, user)

        (out, err), proc = node.mkdir(node.node_home, clean = True)
        self.assertEquals(err, "")
        
        node.install_packages("xterm", node.node_home)
        self.assertEquals(err, "")

        (out, err), proc = node.execute("xterm", forward_x11 = True)
        self.assertEquals(err, "")

        (out, err), proc = node.remove_packages("xterm", node.node_home)
        self.assertEquals(err, "")

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
        node.install_packages('gcc', app_home)

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
        f = tempfile.NamedTemporaryFile(delete = False)
        dst = f.name
        node.download(src, dst)
        f.close()

        node.remove_packages("gcc", app_home)
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

    def test_exitcode_ok_fedora(self):
        self.t_exitcode_ok(self.fedora_host, self.fedora_user)

    def test_exitcode_ok_ubuntu(self):
        self.t_exitcode_ok(self.ubuntu_host, self.ubuntu_user)

    def test_exitcode_kill_fedora(self):
        self.t_exitcode_kill(self.fedora_host, self.fedora_user)

    def test_exitcode_kill_ubuntu(self):
        self.t_exitcode_kill(self.ubuntu_host, self.ubuntu_user)

    def test_exitcode_error_fedora(self):
        self.t_exitcode_error(self.fedora_host, self.fedora_user)

    def test_exitcode_error_ubuntu(self):
        self.t_exitcode_error(self.ubuntu_host, self.ubuntu_user)
    
    @skipInteractive
    def test_xterm_ubuntu(self):
        """ Interactive test. Should not run automatically """
        self.t_xterm(self.ubuntu_host, self.ubuntu_user)


if __name__ == '__main__':
    unittest.main()

