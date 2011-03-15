#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
import os
import shutil
import test_util
import time
import unittest
import uuid

class NetnsIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self._root_dir = os.path.join(os.getenv("HOME"), ".nepi", 
                str(uuid.uuid1()))
        os.makedirs(self._root_dir)

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_local_if(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "netns"
        user = getpass.getuser()
        netns_provider = FactoriesProvider(testbed_id, testbed_version)
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self._root_dir)
        #netns_desc.set_attribute_value("enableDebug", True)
        node1 = netns_desc.create("Node")
        node2 = netns_desc.create("Node")
        iface1 = netns_desc.create("NodeInterface")
        iface1.set_attribute_value("up", True)
        node1.connector("devs").connect(iface1.connector("node"))
        ip1 = iface1.add_address()
        ip1.set_attribute_value("Address", "10.0.0.1")
        iface2 = netns_desc.create("NodeInterface")
        iface2.set_attribute_value("up", True)
        node2.connector("devs").connect(iface2.connector("node"))
        ip2 = iface2.add_address()
        ip2.set_attribute_value("Address", "10.0.0.2")
        switch = netns_desc.create("Switch")
        switch.set_attribute_value("up", True)
        iface1.connector("switch").connect(switch.connector("devs"))
        iface2.connector("switch").connect(switch.connector("devs"))
        app = netns_desc.create("Application")
        app.set_attribute_value("command", "ping -qc1 10.0.0.2")
        app.set_attribute_value("user", user)
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("stdout")
        xml = exp_desc.to_xml()

        controller = ExperimentController(xml)
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        ping_result = controller.trace(netns_desc.guid, app.guid, "stdout")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(ping_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_all_daemonized_if(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "netns"
        user = getpass.getuser()
        netns_provider = FactoriesProvider(testbed_id, testbed_version)
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self._root_dir)
        #netns_desc.set_attribute_value("enableDebug", True)
        node1 = netns_desc.create("Node")
        node2 = netns_desc.create("Node")
        iface1 = netns_desc.create("NodeInterface")
        iface1.set_attribute_value("up", True)
        node1.connector("devs").connect(iface1.connector("node"))
        ip1 = iface1.add_address()
        ip1.set_attribute_value("Address", "10.0.0.1")
        iface2 = netns_desc.create("NodeInterface")
        iface2.set_attribute_value("up", True)
        node2.connector("devs").connect(iface2.connector("node"))
        ip2 = iface2.add_address()
        ip2.set_attribute_value("Address", "10.0.0.2")
        switch = netns_desc.create("Switch")
        switch.set_attribute_value("up", True)
        iface1.connector("switch").connect(switch.connector("devs"))
        iface2.connector("switch").connect(switch.connector("devs"))
        app = netns_desc.create("Application")
        app.set_attribute_value("command", "ping -qc1 10.0.0.2")
        app.set_attribute_value("user", user)
        app.connector("node").connect(node1.connector("apps"))
        app.enable_trace("stdout")
        xml = exp_desc.to_xml()

        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        access_config.set_attribute_value("rootDirectory", self._root_dir)
        access_config.set_attribute_value("logLevel", 
                proxy.AccessConfiguration.DEBUG_LEVEL)
        controller = proxy.create_controller(xml, access_config)

        access_config2 = proxy.AccessConfiguration()
        access_config2.set_attribute_value("mode", 
                proxy.AccessConfiguration.MODE_DAEMON)
        inst_root_dir = os.path.join(self._root_dir, "instance")
        os.mkdir(inst_root_dir)
        access_config2.set_attribute_value("rootDirectory", inst_root_dir)
        access_config2.set_attribute_value("logLevel", 
                proxy.AccessConfiguration.DEBUG_LEVEL)
        controller.set_access_configuration(netns_desc.guid, access_config2)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        ping_result = controller.trace(netns_desc.guid, app.guid, "stdout")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(ping_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()

    def tearDown(self):
        shutil.rmtree(self._root_dir)

if __name__ == '__main__':
    unittest.main()

