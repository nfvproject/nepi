#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util.constants import STATUS_FINISHED
import mock
import mock.metadata_v01 
import sys
import time
import unittest

class ExecuteTestCase(unittest.TestCase):
    def setUp(self):
        sys.modules["nepi.testbeds.mock.metadata_v01"] = mock.metadata_v01

    def test_execute(self):
        testbed_version = "01"
        testbed_id = "mock"
        instance = mock.TestbedInstance(testbed_version)
        instance.configure("fake", True)
        instance.create(2, "Node")
        instance.create(3, "Node")
        instance.create(4, "Node")
        instance.create(5, "Interface")
        instance.create_set(5, "fake", True)
        instance.connect(2, "devs", 5, "node")
        instance.create(6, "Interface")
        instance.create_set(6, "fake", True)
        instance.connect(3, "devs", 6, "node")
        instance.connect(5, "iface", 6, "iface")
        instance.create(7, "Application")
        instance.add_trace(7, "fake")
        instance.connect(7, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_configure()
        instance.start()
        while instance.status(7) != STATUS_FINISHED:
            time.sleep(0.5)
        app_result = instance.trace(7, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        
        self.assertTrue(app_result.startswith(comp_result))
        instance.stop()
        instance.shutdown()

if __name__ == '__main__':
    unittest.main()

