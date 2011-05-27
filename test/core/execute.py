#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util import tags
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
        instance = mock.TestbedController(testbed_version)
        instance.defer_configure("fake", True)
        instance.defer_create(2, "Node")
        instance.defer_create(3, "Node")
        instance.defer_create(4, "Node")
        instance.defer_create(5, "Interface")
        instance.defer_create_set(5, "fake", True)
        instance.defer_connect(2, "devs", 5, "node")
        instance.defer_create(6, "Interface")
        instance.defer_create_set(6, "fake", True)
        instance.defer_connect(3, "devs", 6, "node")
        instance.defer_connect(5, "iface", 6, "iface")
        instance.defer_create(7, "Application")
        instance.defer_add_trace(7, "fake")
        instance.defer_connect(7, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect_init()
        instance.do_connect_compl()
        instance.do_configure()
        instance.start()
        attr_list = instance.get_attribute_list(5)
        self.assertEquals(attr_list, ["test", "fake", "cross", "label"])
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

