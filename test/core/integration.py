#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.util import proxy, tags
from nepi.util.constants import STATUS_FINISHED, DeploymentConfiguration as DC
import mock
import mock.metadata_v01
import mock2
import mock2.metadata_v01
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
        sys.modules["nepi.testbeds.mock2.metadata_v01"] = mock2.metadata_v01
        sys.modules["nepi.testbeds.mock2"] = mock2
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def make_testbed(self, exp_desc, testbed_id, testbed_version):
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
        
        return exp_desc, desc, app, node1, node2, iface1, iface2

    def make_test_experiment(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id = "mock"
        return self.make_testbed(exp_desc, testbed_id, testbed_version)

    def make_cross_test_experiment(self):
        exp_desc = ExperimentDescription()
        testbed_version = "01"
        testbed_id1 = "mock"
        testbed_id2 = "mock2"
        exp_desc, desc1, app1, node11, node12, iface11, iface12 = \
                self.make_testbed(exp_desc, testbed_id1, testbed_version)
        exp_desc, desc2, app2, node21, node22, iface21, iface22 = \
                 self.make_testbed(exp_desc, testbed_id2, testbed_version)
        iface12.connector("cross").connect(iface21.connector("cross"))

        return exp_desc, desc1, desc2, iface12, iface21

    def test_single_process_cross_integration(self):
        exp_desc, desc1, desc2, iface12, iface21 = \
                self.make_cross_test_experiment()
        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        cross1 = controller.get(iface12.guid, "cross")
        cross2 = controller.get(iface21.guid, "cross")
        self.assertTrue(cross1 == cross2 == True)
        controller.stop()
        controller.shutdown()

    def test_single_process_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        self.assertEquals(controller.get_tags(node1.guid), [tags.MOBILE])

        controller.stop()
        controller.shutdown()

    def test_daemonized_controller_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        xml = exp_desc.to_xml()
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        self.assertEquals(controller.get_tags(node1.guid), [tags.MOBILE])

        controller.stop()
        controller.shutdown()

    def test_daemonized_testbed_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)

        xml = exp_desc.to_xml()
        
        controller = proxy.create_controller(xml, access_config = None)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        self.assertEquals(controller.get_tags(node1.guid), [tags.MOBILE])

        controller.stop()
        controller.shutdown()

    def test_daemonized_all_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        inst_root_dir = os.path.join(self.root_dir, "instance")
        os.mkdir(inst_root_dir)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
        
        xml = exp_desc.to_xml()
        
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        self.assertEquals(controller.get_tags(node1.guid), [tags.MOBILE])

        controller.stop()
        controller.shutdown()

    def test_daemonized_all_integration_recovery(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        inst_root_dir = os.path.join(self.root_dir, "instance")
        os.mkdir(inst_root_dir)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
        
        xml = exp_desc.to_xml()
        
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        self.assertEquals(controller.get_tags(node1.guid), [tags.MOBILE])

        # controller dies
        del controller
        
        # recover
        access_config.set_attribute_value(DC.RECOVER,True)
        controller = proxy.create_controller(xml, access_config)
        
        # test recovery
        self.assertTrue(controller.is_finished(app.guid))
        fake_result = controller.trace(app.guid, "fake")
        self.assertTrue(fake_result.startswith(comp_result))
        
        controller.stop()
        controller.shutdown()

    def test_reference_expressions(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        iface1.set_attribute_value("label", "some")
        addr = iface1.add_address()
        addr.set_attribute_value("Address", "10.0.0.2")
        iface2.set_attribute_value("test", "{#[some].addr[0].[Address]#}")
        
        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_controller(xml, access_config)
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        
        self.assertTrue(fake_result.startswith(comp_result))
        
        self.assertEqual(
            controller._testbeds[desc.guid].get(iface2.guid, "test"),
            addr.get_attribute_value("Address") )
        
        controller.stop()
        controller.shutdown()

    def test_testbed_reference_expressions(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        iface1.set_attribute_value("label", "some")
        addr = iface1.add_address()
        addr.set_attribute_value("Address", "10.0.0.2")

        desc2 = exp_desc.add_testbed_description(
            FactoriesProvider("mock2", "01") )
        desc2.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[some].addr[0].[Address]#}")
        # DC.DEPLOYMENT_HOST should be ignored if DC.DEPLOYMENT_CONNECTION is not set
        # But it should be resolved anyway
        
        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_controller(xml, access_config)
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))

        self.assertEqual(
            controller._deployment_config[desc2.guid]
                .get_attribute_value(DC.DEPLOYMENT_HOST),
            addr.get_attribute_value("Address") )
        
        controller.stop()
        controller.shutdown()

    def TODO_test_ssh_daemonized_all_integration(self):
        # TODO: This test doesn't run because
        # sys.modules["nepi.testbeds.mock"] = mock
        # is not set in the ssh process
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        env = test_util.test_environment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        inst_root_dir = os.path.join(self.root_dir, "instance")
        os.mkdir(inst_root_dir)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
        desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        desc.set_attribute_value(DC.DEPLOYMENT_PORT, env.port)
        desc.set_attribute_value(DC.USE_AGENT, True)
        
        xml = exp_desc.to_xml()
        
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        access_config.set_attribute_value(DC.DEPLOYMENT_PORT, env.port)
        access_config.set_attribute_value(DC.USE_AGENT, True)
        controller = proxy.create_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))
        controller.stop()
        controller.shutdown()
 
if __name__ == '__main__':
    unittest.main()

