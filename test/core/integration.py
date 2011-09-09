#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC
import getpass
import mock
import mock.metadata
import mock2
import mock2.metadata
import os
import shutil
import sys
import tempfile
import test_util
import time
import unittest

class ExecuteTestCase(unittest.TestCase):
    def setUp(self):
        sys.modules["nepi.testbeds.mock.metadata"] = mock.metadata
        sys.modules["nepi.testbeds.mock"] = mock
        sys.modules["nepi.testbeds.mock2.metadata"] = mock2.metadata
        sys.modules["nepi.testbeds.mock2"] = mock2
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def make_testbed(self, exp_desc, testbed_id):
        provider = FactoriesProvider(testbed_id)
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
        testbed_id = "mock"
        return self.make_testbed(exp_desc, testbed_id)

    def make_cross_test_experiment(self):
        exp_desc = ExperimentDescription()
        testbed_id1 = "mock"
        testbed_id2 = "mock2"
        exp_desc, desc1, app1, node11, node12, iface11, iface12 = \
                self.make_testbed(exp_desc, testbed_id1)
        exp_desc, desc2, app2, node21, node22, iface21, iface22 = \
                 self.make_testbed(exp_desc, testbed_id2)
        iface12.connector("cross").connect(iface21.connector("cross"))

        return exp_desc, desc1, desc2, iface12, iface21

    def test_single_process_cross_integration(self):
        exp_desc, desc1, desc2, iface12, iface21 = \
                self.make_cross_test_experiment()
        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_experiment_controller(xml, access_config)

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
        controller = proxy.create_experiment_controller(xml, access_config)

        controller.start()
        started_time = controller.started_time
        self.assertTrue(started_time < time.time())
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))

        self.assertEquals(controller.get_testbed_id(node1.guid), "mock")
        self.assertEquals(controller.get_testbed_version(node1.guid), "0.1")
        self.assertEquals(controller.get_factory_id(node1.guid), "Node")

        controller.stop()
        stopped_time = controller.stopped_time
        self.assertTrue(stopped_time < time.time())
        controller.shutdown()

    def test_daemonized_controller_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        xml = exp_desc.to_xml()
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))

        controller = proxy.create_experiment_controller(xml, access_config)

        controller.start()
        started_time = controller.started_time
        self.assertTrue(started_time < time.time())
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))

        self.assertEquals(controller.get_testbed_id(node1.guid), "mock")
        self.assertEquals(controller.get_testbed_version(node1.guid), "0.1")
        self.assertEquals(controller.get_factory_id(node1.guid), "Node")

        controller.stop()
        stopped_time = controller.stopped_time
        self.assertTrue(stopped_time < time.time())
        controller.shutdown()

    def test_daemonized_testbed_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))

        xml = exp_desc.to_xml()
        
        controller = proxy.create_experiment_controller(xml, access_config = None)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))

        self.assertEquals(controller.get_testbed_id(node1.guid), "mock")
        self.assertEquals(controller.get_testbed_version(node1.guid), "0.1")
        self.assertEquals(controller.get_factory_id(node1.guid), "Node")

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
        access_config.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))
        controller = proxy.create_experiment_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))

        self.assertEquals(controller.get_testbed_id(node1.guid), "mock")
        self.assertEquals(controller.get_testbed_version(node1.guid), "0.1")
        self.assertEquals(controller.get_factory_id(node1.guid), "Node")

        traces_info = controller.traces_info()
        expected_traces_info = dict({
            1: dict({ # testbed guid
                6: dict({ # element guid
                    'fake': dict({ # trace_id
                        'host': 'localhost', 
                        'user': getpass.getuser(), 
                        'filepath': '<test>'
                        })
                    })
                })
            })
        self.assertEquals(traces_info, expected_traces_info)

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
        access_config.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))
        controller = proxy.create_experiment_controller(xml, access_config)

        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        fake_result = controller.trace(app.guid, "fake")
        comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        self.assertTrue(fake_result.startswith(comp_result))

        self.assertEquals(controller.get_testbed_id(node1.guid), "mock")
        self.assertEquals(controller.get_testbed_version(node1.guid), "0.1")
        self.assertEquals(controller.get_factory_id(node1.guid), "Node")

        # controller dies
        del controller
        
        # recover
        access_config.set_attribute_value(DC.RECOVER,True)
        controller = proxy.create_experiment_controller(xml, access_config)
        
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
        controller = proxy.create_experiment_controller(xml, access_config)
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
            FactoriesProvider("mock2") )
        desc2.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[some].addr[0].[Address]#}")
        # DC.DEPLOYMENT_HOST should be ignored if DC.DEPLOYMENT_CONNECTION is not set
        # But it should be resolved anyway
        
        xml = exp_desc.to_xml()
        access_config = None
        controller = proxy.create_experiment_controller(xml, access_config)
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

    def test_ssh_daemonized_integration(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        env = test_util.test_environment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        inst_root_dir = os.path.join(self.root_dir, "instance")
        os.mkdir(inst_root_dir)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
        xml = exp_desc.to_xml()
        
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        access_config.set_attribute_value(DC.DEPLOYMENT_PORT, env.port)
        access_config.set_attribute_value(DC.USE_AGENT, True)
        access_config.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))
        controller = proxy.create_experiment_controller(xml, access_config)

        try:
            controller.start()
            while not controller.is_finished(app.guid):
                time.sleep(0.5)
            fake_result = controller.trace(app.guid, "fake")
            comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
            self.assertTrue(fake_result.startswith(comp_result))
        finally:
            controller.stop()
            controller.shutdown()

    def ptest_experiment_suite(self):
        exp_desc, desc, app, node1, node2, iface1, iface2 = self.make_test_experiment()
        
        desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        desc.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))

        xml = exp_desc.to_xml()

        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "export PYTHONPATH=%r:%r:$PYTHONPATH "
            "export NEPI_TESTBEDS='mock:mock mock2:mock2' " % (
                os.path.dirname(os.path.dirname(mock.__file__)),
                os.path.dirname(os.path.dirname(mock2.__file__)),))
       
        exp_suite = proxy.create_experiment_suite(xml, access_config)
        exp_suite.start()
        while not exp_suite.is_finished:
            time.sleep(0.5)

        for access_config in exp_suite.access_configurations:
            access_config.set_attribute_value(DC.RECOVER, True)
            controller = proxy.create_experiment_controller(None, access_config)

            fake_result = controller.trace(app.guid, "fake")
            comp_result = """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
            self.assertTrue(fake_result.startswith(comp_result))

            self.assertEquals(controller.get_testbed_id(node1.guid), "mock")
            self.assertEquals(controller.get_testbed_version(node1.guid), "0.1")
            self.assertEquals(controller.get_factory_id(node1.guid), "Node")

        exp_suite.shutdown()

if __name__ == '__main__':
    unittest.main()

