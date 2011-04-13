#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.util import server
import os
import shutil
import sys
import tempfile
import test_util
import unittest

class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def test_server(self):
        s = server.Server(self.root_dir)
        s.run()
        c = server.Client(self.root_dir)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertTrue(reply == "Reply to: Hola")
        c.send_stop()
        reply = c.read_reply()
        self.assertTrue(reply == "Stopping server")

    def test_server_long_message(self):
        s = server.Server(self.root_dir)
        s.run()
        c = server.Client(self.root_dir)
        msg = "1"*1145
        c.send_msg(msg)
        reply = c.read_reply()
        self.assertTrue(reply == ("Reply to: "+msg))
        c.send_stop()
        reply = c.read_reply()
        self.assertTrue(reply == "Stopping server")

    def test_ssh_server(self):
        env = test_util.test_environment()
        user = getpass.getuser()
        # launch server
        python_code = "from nepi.util import server;s=server.Server('%s');\
                s.run()" % self.root_dir
        server.popen_ssh_subprocess(python_code, host = "localhost", 
                port = env.port, user = user, agent = True)
        c = server.Client(self.root_dir, host = "localhost", port = env.port,
                user = user, agent = True)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertTrue(reply == "Reply to: Hola")
        c.send_stop()
        reply = c.read_reply()
        self.assertTrue(reply == "Stopping server")

    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

