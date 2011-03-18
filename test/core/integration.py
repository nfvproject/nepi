#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.util.constants import STATUS_FINISHED
from nepi.util import proxy
import mock
import mock.metadata_v01
import os
import shutil
import sys
import tempfile
import test_util
import time
import unittest

class ExecuteTestCase(unittest.TestCase):
    def setUp(self):
        sys.modules["nepi.testbeds.mock.metadata_v01"] = mock.metadata_v01
        sys.modules["nepi.testbeds.mock"] = mock
        self.root_dir = tempfile.mkdtemp()

    def test_single_process_integration(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "mock"
        provider = FactoriesProvider(testbed_id, testbed_version)
        desc = exp_desc.add_testbed_description(provider)
        desc.set_attribute_value("fake", True)
        node1 = desc.create("Node")
        node2 = desc.create("Node")
        iface1 = desc.create("Interface")
        iface1.set_attribute_value("fake", True)
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = desc.create("Interface")
        iface2.set_attribute_value("fake", True)
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("iface").connect(iface2.connector("iface"))
        app = desc.create("Application")
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("fake")

        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_controller(xml, access_config)
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(desc.guid, app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()

    def test_daemonized_controller_integration(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "mock"
        provider = FactoriesProvider(testbed_id, testbed_version)
        desc = exp_desc.add_testbed_description(provider)
        desc.set_attribute_value("fake", True)
        node1 = desc.create("Node")
        node2 = desc.create("Node")
        iface1 = desc.create("Interface")
        iface1.set_attribute_value("fake", True)
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = desc.create("Interface")
        iface2.set_attribute_value("fake", True)
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("iface").connect(iface2.connector("iface"))
        app = desc.create("Application")
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("fake")

        xml = exp_desc.to_xml()
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        access_config.set_attribute_value("rootDirectory", self.root_dir)
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(desc.guid, app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()

    def test_daemonized_testbed_integration(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "mock"
        provider = FactoriesProvider(testbed_id, testbed_version)
        desc = exp_desc.add_testbed_description(provider)
        desc.set_attribute_value("fake", True)
        node1 = desc.create("Node")
        node2 = desc.create("Node")
        iface1 = desc.create("Interface")
        iface1.set_attribute_value("fake", True)
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = desc.create("Interface")
        iface2.set_attribute_value("fake", True)
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("iface").connect(iface2.connector("iface"))
        app = desc.create("Application")
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("fake")

        xml = exp_desc.to_xml()
        controller = proxy.create_controller(xml, access_config = None)
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        access_config.set_attribute_value("rootDirectory", self.root_dir)
        controller.set_access_configuration(desc.guid, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(desc.guid, app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()

    def test_daemonized_all_integration(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "mock"
        provider = FactoriesProvider(testbed_id, testbed_version)
        desc = exp_desc.add_testbed_description(provider)
        desc.set_attribute_value("fake", True)
        node1 = desc.create("Node")
        node2 = desc.create("Node")
        iface1 = desc.create("Interface")
        iface1.set_attribute_value("fake", True)
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = desc.create("Interface")
        iface2.set_attribute_value("fake", True)
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("iface").connect(iface2.connector("iface"))
        app = desc.create("Application")
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("fake")

        xml = exp_desc.to_xml()
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        access_config.set_attribute_value("rootDirectory", self.root_dir)
        controller = proxy.create_controller(xml, access_config)

        access_config2 = proxy.AccessConfiguration()
        access_config2.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        inst_root_dir = os.path.join(self.root_dir, "instance")
        os.mkdir(inst_root_dir)
        access_config2.set_attribute_value("rootDirectory", inst_root_dir)
        controller.set_access_configuration(desc.guid, access_config2)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(desc.guid, app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()

    def TODO_test_ssh_daemonized_all_integration(self):
        # TODO: This test doesn't run because
        # sys.modules["nepi.testbeds.mock"] = mock
        # is not set in the ssh process
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "mock"
        env = test_util.test_environment()
        provider = FactoriesProvider(testbed_id, testbed_version)
        desc = exp_desc.add_testbed_description(provider)
        desc.set_attribute_value("fake", True)
        node1 = desc.create("Node")
        node2 = desc.create("Node")
        iface1 = desc.create("Interface")
        iface1.set_attribute_value("fake", True)
        node1.connector("devs").connect(iface1.connector("node"))
        iface2 = desc.create("Interface")
        iface2.set_attribute_value("fake", True)
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("iface").connect(iface2.connector("iface"))
        app = desc.create("Application")
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("fake")

        xml = exp_desc.to_xml()
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        access_config.set_attribute_value("rootDirectory", self.root_dir)
        access_config.set_attribute_value("communication", 
                proxy.AccessConfiguration.ACCESS_SSH)
        access_config.set_attribute_value("port", env.port)
        access_config.set_attribute_value("useAgent", True)
        controller = proxy.create_controller(xml, access_config)

        access_config2 = proxy.AccessConfiguration()
        access_config2.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        inst_root_dir = os.path.join(self.root_dir, "instance")
        os.mkdir(inst_root_dir)
        access_config2.set_attribute_value("rootDirectory", inst_root_dir)
        access_config2.set_attribute_value("communication", 
                proxy.AccessConfiguration.ACCESS_SSH)
        access_config2.set_attribute_value("port", env.port)
        access_config2.set_attribute_value("useAgent", True)
        controller.set_access_configuration(desc.guid, access_config2)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(desc.guid, app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()
 
    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

