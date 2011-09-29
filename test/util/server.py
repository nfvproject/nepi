#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util import server
from nepi.util.constants import DeploymentConfiguration as DC

import getpass
import os
import shutil
import sys
import tempfile
import test_util
import unittest
import time

class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        
        # Silence the server
        self.stderr = sys.stderr
        sys.stderr = open("/dev/null","r+b")

    def tearDown(self):
        sys.stderr = self.stderr
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def test_server(self):
        s = server.Server(self.root_dir)
        s.run()
        c = server.Client(self.root_dir)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

    def test_server_reconnect(self):
        s = server.Server(self.root_dir)
        s.run()
        c = server.Client(self.root_dir)
        
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        
        # disconnect
        del c
        
        # reconnect
        c = server.Client(self.root_dir)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
                
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

    def test_server_auto_reconnect(self):
        s = server.Server(self.root_dir)
        s.run()
        c = server.Client(self.root_dir)
        
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        
        # purposedly break the connection
        c._process.stdin.close()
        c._process.stdout.close()
        c._process.stderr.close()
        
        # assert that the communication works (possible with auto-reconnection)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
                
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

    def test_server_long_message(self):
        s = server.Server(self.root_dir)
        s.run()
        c = server.Client(self.root_dir)
        msg = "1"*1145
        c.send_msg(msg)
        reply = c.read_reply()
        self.assertEqual(reply, ("Reply to: "+msg))
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_sudo_server(self):
        env = test_util.test_environment()
        user = getpass.getuser()
        # launch server
        python_code = "from nepi.util import server;s=server.Server('%s');\
                s.run()" % self.root_dir
        server.popen_python(python_code, 
                sudo = True)
        c = server.Client(self.root_dir, 
                sudo = True)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")


    def test_ssh_server(self):
        env = test_util.test_environment()
        user = getpass.getuser()
        # launch server
        python_code = "from nepi.util import server;s=server.Server('%s');\
                s.run()" % self.root_dir
        server.popen_python(python_code, 
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port, 
                user = user, 
                agent = True)
        c = server.Client(self.root_dir, 
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port,
                user = user, 
                agent = True)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

    def test_ssh_server_reconnect(self):
        env = test_util.test_environment()
        user = getpass.getuser()
        # launch server
        python_code = "from nepi.util import server;s=server.Server('%s');\
                s.run()" % self.root_dir
        server.popen_python(python_code, 
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port, 
                user = user, 
                agent = True)
        
        c = server.Client(self.root_dir, 
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port,
                user = user, 
                agent = True)
                
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        
        # disconnect
        del c
        
        # reconnect
        c = server.Client(self.root_dir,
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port,
                user = user, 
                agent = True)
                
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

    def test_ssh_server_auto_reconnect(self):
        env = test_util.test_environment()
        user = getpass.getuser()
        # launch server
        python_code = "from nepi.util import server;s=server.Server('%s');\
                s.run()" % self.root_dir
        server.popen_python(python_code, 
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port, 
                user = user, 
                agent = True)
        
        c = server.Client(self.root_dir, 
                communication = DC.ACCESS_SSH,
                host = "localhost", 
                port = env.port,
                user = user, 
                agent = True)
                
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        
        # purposedly break the connection
        c._process.stdin.close()
        c._process.stdout.close()
        c._process.stderr.close()
        
        # assert that the communication works (possible with auto-reconnection)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertEqual(reply, "Reply to: Hola")
        
        c.send_stop()
        reply = c.read_reply()
        self.assertEqual(reply, "Stopping server")

if __name__ == '__main__':
    unittest.main()

