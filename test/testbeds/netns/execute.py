#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.util.constants import STATUS_FINISHED
from nepi.testbeds import netns
import os
import shutil
import tempfile
import test_util
import time
import unittest

class NetnsExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_run_ping_if(self):
        user = getpass.getuser()
        testbed_version = "01"
        instance = netns.TestbedController(testbed_version)
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_create(2, "Node")
        instance.defer_create(3, "Node")
        instance.defer_create(4, "NodeInterface")
        instance.defer_create_set(4, "up", True)
        instance.defer_connect(2, "devs", 4, "node")
        instance.defer_add_address(4, "10.0.0.1", 24, None)
        instance.defer_create(5, "NodeInterface")
        instance.defer_create_set(5, "up", True)
        instance.defer_connect(3, "devs", 5, "node")
        instance.defer_add_address(5, "10.0.0.2", 24, None)
        instance.defer_create(6, "Switch")
        instance.defer_create_set(6, "up", True)
        instance.defer_connect(4, "switch", 6, "devs")
        instance.defer_connect(5, "switch", 6, "devs")
        instance.defer_create(7, "Application")
        instance.defer_create_set(7, "command", "ping -qc1 10.0.0.2")
        instance.defer_create_set(7, "user", user)
        instance.defer_add_trace(7, "stdout")
        instance.defer_connect(7, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        instance.start()
        while instance.status(7) != STATUS_FINISHED:
            time.sleep(0.5)
        ping_result = instance.trace(7, "stdout")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(ping_result.startswith(comp_result))
        instance.stop()
        instance.shutdown()

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_run_ping_p2pif(self):
        user = getpass.getuser()
        testbed_version = "01"
        instance = netns.TestbedController(testbed_version)
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_create(2, "Node")
        instance.defer_create(3, "Node")
        instance.defer_create(4, "P2PNodeInterface")
        instance.defer_create_set(4, "up", True)
        instance.defer_connect(2, "devs", 4, "node")
        instance.defer_add_address(4, "10.0.0.1", 24, None)
        instance.defer_create(5, "P2PNodeInterface")
        instance.defer_create_set(5, "up", True)
        instance.defer_connect(3, "devs", 5, "node")
        instance.defer_add_address(5, "10.0.0.2", 24, None)
        instance.defer_connect(4, "p2p", 5, "p2p")
        instance.defer_create(6, "Application")
        instance.defer_create_set(6, "command", "ping -qc1 10.0.0.2")
        instance.defer_create_set(6, "user", user)
        instance.defer_add_trace(6, "stdout")
        instance.defer_connect(6, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        instance.start()
        while instance.status(6) != STATUS_FINISHED:
            time.sleep(0.5)
        ping_result = instance.trace(6, "stdout")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(ping_result.startswith(comp_result))
        instance.stop()
        instance.shutdown()

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_run_ping_routing(self):
        user = getpass.getuser()
        testbed_version = "01"
        instance = netns.TestbedController(testbed_version)
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_create(2, "Node")
        instance.defer_create(3, "Node")
        instance.defer_create(4, "Node")
        instance.defer_create(5, "NodeInterface")
        instance.defer_create_set(5, "up", True)
        instance.defer_connect(2, "devs", 5, "node")
        instance.defer_add_address(5, "10.0.0.1", 24, None)
        instance.defer_create(6, "NodeInterface")
        instance.defer_create_set(6, "up", True)
        instance.defer_connect(3, "devs", 6, "node")
        instance.defer_add_address(6, "10.0.0.2", 24, None)
        instance.defer_create(7, "NodeInterface")
        instance.defer_create_set(7, "up", True)
        instance.defer_connect(3, "devs", 7, "node")
        instance.defer_add_address(7, "10.0.1.1", 24, None)
        instance.defer_create(8, "NodeInterface")
        instance.defer_create_set(8, "up", True)
        instance.defer_connect(4, "devs", 8, "node")
        instance.defer_add_address(8, "10.0.1.2", 24, None)
        instance.defer_create(9, "Switch")
        instance.defer_create_set(9, "up", True)
        instance.defer_connect(5, "switch", 9, "devs")
        instance.defer_connect(6, "switch", 9, "devs")
        instance.defer_create(10, "Switch")
        instance.defer_create_set(10, "up", True)
        instance.defer_connect(7, "switch", 10, "devs")
        instance.defer_connect(8, "switch", 10, "devs")
        instance.defer_create(11, "Application")
        instance.defer_create_set(11, "command", "ping -qc1 10.0.1.2")
        instance.defer_create_set(11, "user", user)
        instance.defer_add_trace(11, "stdout")
        instance.defer_connect(11, "node", 2, "apps")

        instance.defer_add_route(2, "10.0.1.0", 24, "10.0.0.2")
        instance.defer_add_route(4, "10.0.0.0", 24, "10.0.1.1")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        instance.start()
        while instance.status(11) != STATUS_FINISHED:
            time.sleep(0.5)
        ping_result = instance.trace(11, "stdout")
        comp_result = """PING 10.0.1.2 (10.0.1.2) 56(84) bytes of data.

--- 10.0.1.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(ping_result.startswith(comp_result))
        instance.stop()
        instance.shutdown()
        
    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

