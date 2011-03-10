#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util import server
import os
import shutil
import sys
import unittest
import uuid

class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self._root_dir = os.path.join(os.getenv("HOME"), ".nepi", 
                str(uuid.uuid1()))
        os.makedirs(self._root_dir)

    def test_server(self):
        s = server.Server(self._root_dir)
        s.run()
        c = server.Client(self._root_dir)
        c.send_msg("Hola")
        reply = c.read_reply()
        self.assertTrue(reply == "Reply to: Hola")
        c.send_stop()
        reply = c.read_reply()
        self.assertTrue(reply == "Stopping server")

    def tearDown(self):
        shutil.rmtree(self._root_dir)

if __name__ == '__main__':
    unittest.main()

