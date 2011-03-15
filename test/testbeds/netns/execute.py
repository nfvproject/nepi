#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.util.constants import AF_INET, STATUS_FINISHED
from nepi.testbeds import netns
import os
import shutil
import test_util
import time
import unittest
import uuid

class NetnsExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self._home_dir = os.path.join(os.getenv("HOME"), ".nepi", 
                str(uuid.uuid1()))
        os.makedirs(self._home_dir)

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_run_ping_if(self):
        user = getpass.getuser()
        testbed_version = "01"
        instance = netns.TestbedInstance(testbed_version)
        instance.configure("homeDirectory", self._home_dir)
        instance.create(2, "Node")
        instance.create(3, "Node")
        instance.create(4, "NodeInterface")
        instance.create_set(4, "up", True)
        instance.connect(2, "devs", 4, "node")
        instance.add_address(4, AF_INET, "10.0.0.1", 24, None)
        instance.create(5, "NodeInterface")
        instance.create_set(5, "up", True)
        instance.connect(3, "devs", 5, "node")
        instance.add_address(5, AF_INET, "10.0.0.2", 24, None)
        instance.create(6, "Switch")
        instance.create_set(6, "up", True)
        instance.connect(4, "switch", 6, "devs")
        instance.connect(5, "switch", 6, "devs")
        instance.create(7, "Application")
        instance.create_set(7, "command", "ping -qc1 10.0.0.2")
        instance.create_set(7, "user", user)
        instance.add_trace(7, "stdout")
        instance.connect(7, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
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
        instance = netns.TestbedInstance(testbed_version)
        instance.configure("homeDirectory", self._home_dir)
        instance.create(2, "Node")
        instance.create(3, "Node")
        instance.create(4, "P2PNodeInterface")
        instance.create_set(4, "up", True)
        instance.connect(2, "devs", 4, "node")
        instance.add_address(4, AF_INET, "10.0.0.1", 24, None)
        instance.create(5, "P2PNodeInterface")
        instance.create_set(5, "up", True)
        instance.connect(3, "devs", 5, "node")
        instance.add_address(5, AF_INET, "10.0.0.2", 24, None)
        instance.connect(4, "p2p", 5, "p2p")
        instance.create(6, "Application")
        instance.create_set(6, "command", "ping -qc1 10.0.0.2")
        instance.create_set(6, "user", user)
        instance.add_trace(6, "stdout")
        instance.connect(6, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
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
        instance = netns.TestbedInstance(testbed_version)
        instance.configure("homeDirectory", self._home_dir)
        instance.create(2, "Node")
        instance.create(3, "Node")
        instance.create(4, "Node")
        instance.create(5, "NodeInterface")
        instance.create_set(5, "up", True)
        instance.connect(2, "devs", 5, "node")
        instance.add_address(5, AF_INET, "10.0.0.1", 24, None)
        instance.create(6, "NodeInterface")
        instance.create_set(6, "up", True)
        instance.connect(3, "devs", 6, "node")
        instance.add_address(6, AF_INET, "10.0.0.2", 24, None)
        instance.create(7, "NodeInterface")
        instance.create_set(7, "up", True)
        instance.connect(3, "devs", 7, "node")
        instance.add_address(7, AF_INET, "10.0.1.1", 24, None)
        instance.create(8, "NodeInterface")
        instance.create_set(8, "up", True)
        instance.connect(4, "devs", 8, "node")
        instance.add_address(8, AF_INET, "10.0.1.2", 24, None)
        instance.create(9, "Switch")
        instance.create_set(9, "up", True)
        instance.connect(5, "switch", 9, "devs")
        instance.connect(6, "switch", 9, "devs")
        instance.create(10, "Switch")
        instance.create_set(10, "up", True)
        instance.connect(7, "switch", 10, "devs")
        instance.connect(8, "switch", 10, "devs")
        instance.create(11, "Application")
        instance.create_set(11, "command", "ping -qc1 10.0.1.2")
        instance.create_set(11, "user", user)
        instance.add_trace(11, "stdout")
        instance.connect(11, "node", 2, "apps")

        instance.add_route(2, "10.0.1.0", 24, "10.0.0.2")
        instance.add_route(4, "10.0.0.0", 24, "10.0.1.1")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
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
        shutil.rmtree(self._home_dir)

if __name__ == '__main__':
    unittest.main()

