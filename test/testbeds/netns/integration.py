#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC
import os
import shutil
import tempfile
import test_util
import time
import unittest

class NetnsIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def _test_if(self, daemonize_testbed, controller_access_configuration):
        exp_desc = ExperimentDescription()
        testbed_id = "netns"
        user = getpass.getuser()
        netns_provider = FactoriesProvider(testbed_id)
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self.root_dir)
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

        if daemonize_testbed:
            netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
            inst_root_dir = os.path.join(self.root_dir, "instance")
            os.mkdir(inst_root_dir)
            netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
            netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

        xml = exp_desc.to_xml()

        if controller_access_configuration:
            controller = proxy.create_experiment_controller(xml, 
                controller_access_configuration)
        else:
            controller = ExperimentController(xml, self.root_dir)
        
        try:
            controller.start()
            while not controller.is_finished(app.guid):
                time.sleep(0.5)
            ping_result = controller.trace(app.guid, "stdout")
            comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
            self.assertTrue(ping_result.startswith(comp_result))
        finally:
            controller.stop()
            controller.shutdown()

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_local_if(self):
        self._test_if(
            daemonize_testbed = False,
            controller_access_configuration = None)

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_all_daemonized_if(self):
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        
        self._test_if(
            daemonize_testbed = True,
            controller_access_configuration = access_config)

    @test_util.skipUnless(os.getuid() == 0, "Test requires root privileges")
    def test_all_ssh_daemonized_if(self):
        env = test_util.test_environment()
        
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        access_config.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        access_config.set_attribute_value(DC.DEPLOYMENT_PORT, env.port)
        access_config.set_attribute_value(DC.USE_AGENT, True)
        
        self._test_if(
            daemonize_testbed = True,
            controller_access_configuration = access_config)

    def tearDown(self):
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

