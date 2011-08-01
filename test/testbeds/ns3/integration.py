#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC
import os
import re
import shutil
import tempfile
import test_util
import time
import unittest

class Ns3IntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def _test_fd_net_device(self, daemonize_testbed,
            controller_access_configuration):
        exp_desc = ExperimentDescription()
        testbed_id = "ns3"
        ns3_provider = FactoriesProvider(testbed_id)
        ns3_desc1 = exp_desc.add_testbed_description(ns3_provider)
        root_dir1 = os.path.join(self.root_dir, "1")
        ns3_desc1.set_attribute_value("homeDirectory", root_dir1)
        ns3_desc1.set_attribute_value("SimulatorImplementationType",
                "ns3::RealtimeSimulatorImpl")
        ns3_desc1.set_attribute_value("ChecksumEnabled", True)
        ns3_desc2 = exp_desc.add_testbed_description(ns3_provider)
        root_dir2 = os.path.join(self.root_dir, "2")
        ns3_desc2.set_attribute_value("homeDirectory", root_dir2)
        ns3_desc2.set_attribute_value("SimulatorImplementationType",
                "ns3::RealtimeSimulatorImpl")
        ns3_desc2.set_attribute_value("ChecksumEnabled", True)

        node1 = ns3_desc1.create("ns3::Node")
        ipv41 = ns3_desc1.create("ns3::Ipv4L3Protocol")
        arp1  = ns3_desc1.create("ns3::ArpL3Protocol")
        icmp1 = ns3_desc1.create("ns3::Icmpv4L4Protocol")
        node1.connector("protos").connect(ipv41.connector("node"))
        node1.connector("protos").connect(arp1.connector("node"))
        node1.connector("protos").connect(icmp1.connector("node"))
        iface1 = ns3_desc1.create("ns3::FdNetDevice")
        node1.connector("devs").connect(iface1.connector("node"))
        ip1 = iface1.add_address()
        ip1.set_attribute_value("Address", "10.0.0.1")
        tc1 = ns3_desc1.create("ns3::Nepi::TunChannel")
        tc1.connector("fd->").connect(iface1.connector("->fd"))

        node2 = ns3_desc2.create("ns3::Node")
        ipv42 = ns3_desc2.create("ns3::Ipv4L3Protocol")
        arp2  = ns3_desc2.create("ns3::ArpL3Protocol")
        icmp2 = ns3_desc2.create("ns3::Icmpv4L4Protocol")
        node2.connector("protos").connect(ipv42.connector("node"))
        node2.connector("protos").connect(arp2.connector("node"))
        node2.connector("protos").connect(icmp2.connector("node"))
        iface2 = ns3_desc2.create("ns3::FdNetDevice")
        iface2.enable_trace("FdAsciiTrace")
        node2.connector("devs").connect(iface2.connector("node"))
        ip2 = iface2.add_address()
        ip2.set_attribute_value("Address", "10.0.0.2")
        tc2 = ns3_desc2.create("ns3::Nepi::TunChannel")
        tc2.connector("fd->").connect(iface2.connector("->fd"))

        tc2.connector("udp").connect(tc1.connector("udp"))

        app = ns3_desc1.create("ns3::V4Ping")
        app.set_attribute_value("Remote", "10.0.0.2")
        app.set_attribute_value("StartTime", "0s")
        app.set_attribute_value("StopTime", "2s")
        app.connector("node").connect(node1.connector("apps"))

        if daemonize_testbed:
            ns3_desc1.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
            inst_root_dir = os.path.join(root_dir1, "instance")
            os.makedirs(inst_root_dir)
            ns3_desc1.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
            ns3_desc1.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

            ns3_desc2.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
            inst_root_dir = os.path.join(root_dir2, "instance")
            os.makedirs(inst_root_dir)
            ns3_desc2.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
            ns3_desc2.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

        xml = exp_desc.to_xml()
        
        if controller_access_configuration:
            controller = ExperimentController(xml, self.root_dir)
        else:
            controller = proxy.create_experiment_controller(xml, 
                controller_access_configuration)
        
        try:
            controller.start()
            while not controller.is_finished(app.guid):
                time.sleep(0.5)
            ping_result = controller.trace(iface2.guid, "FdAsciiTrace")
            ping_exp_result = r"""r \d+\.\d+ /NodeList/0/DeviceList/0/\$ns3::FdNetDevice/Rx Payload \(size=42\)
r \d+\.\d+ /NodeList/0/DeviceList/0/\$ns3::FdNetDevice/Rx Payload \(size=98\)
r \d+\.\d+ /NodeList/0/DeviceList/0/\$ns3::FdNetDevice/Rx Payload \(size=42\)
r \d+\.\d+ /NodeList/0/DeviceList/0/\$ns3::FdNetDevice/Rx Payload \(size=98\)
"""
            if not re.match(ping_exp_result, ping_result):
                self.fail("Unexpected trace: %s" % (ping_result,))

        finally:
            controller.stop()
            controller.shutdown()
 
    def _test_if(self, daemonize_testbed, controller_access_configuration):
        exp_desc = ExperimentDescription()
        testbed_id = "ns3"
        ns3_provider = FactoriesProvider(testbed_id)
        ns3_desc = exp_desc.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("homeDirectory", self.root_dir)

        node1 = ns3_desc.create("ns3::Node")
        ipv41 = ns3_desc.create("ns3::Ipv4L3Protocol")
        arp1  = ns3_desc.create("ns3::ArpL3Protocol")
        icmp1 = ns3_desc.create("ns3::Icmpv4L4Protocol")
        node1.connector("protos").connect(ipv41.connector("node"))
        node1.connector("protos").connect(arp1.connector("node"))
        node1.connector("protos").connect(icmp1.connector("node"))
        iface1 = ns3_desc.create("ns3::PointToPointNetDevice")
        queue1 = ns3_desc.create("ns3::DropTailQueue")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("queue").connect(queue1.connector("dev"))
        trace1 = iface1.enable_trace("P2PAsciiTrace")
        ip1 = iface1.add_address()
        ip1.set_attribute_value("Address", "10.0.0.1")

        node2 = ns3_desc.create("ns3::Node")
        ipv42 = ns3_desc.create("ns3::Ipv4L3Protocol")
        arp2  = ns3_desc.create("ns3::ArpL3Protocol")
        icmp2 = ns3_desc.create("ns3::Icmpv4L4Protocol")
        node2.connector("protos").connect(ipv42.connector("node"))
        node2.connector("protos").connect(arp2.connector("node"))
        node2.connector("protos").connect(icmp2.connector("node"))
        iface2 = ns3_desc.create("ns3::PointToPointNetDevice")
        queue2 = ns3_desc.create("ns3::DropTailQueue")
        node2.connector("devs").connect(iface2.connector("node"))
        iface2.connector("queue").connect(queue2.connector("dev"))
        trace2 = iface2.enable_trace("P2PAsciiTrace")
        ip2 = iface2.add_address()
        ip2.set_attribute_value("Address", "10.0.0.2")

        chan = ns3_desc.create("ns3::PointToPointChannel")
        iface1.connector("chan").connect(chan.connector("dev2"))
        iface2.connector("chan").connect(chan.connector("dev2"))

        app = ns3_desc.create("ns3::V4Ping")
        app.set_attribute_value("Remote", "10.0.0.2")
        app.set_attribute_value("StartTime", "0s")
        app.set_attribute_value("StopTime", "20s")
        app.connector("node").connect(node1.connector("apps"))

        if daemonize_testbed:
            ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
            inst_root_dir = os.path.join(self.root_dir, "instance")
            os.mkdir(inst_root_dir)
            ns3_desc.set_attribute_value(DC.ROOT_DIRECTORY, inst_root_dir)
            ns3_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

        xml = exp_desc.to_xml()
        
        if controller_access_configuration:
            controller = ExperimentController(xml, self.root_dir)
        else:
            controller = proxy.create_experiment_controller(xml, 
                controller_access_configuration)
        
        try:
            controller.start()
            while not controller.is_finished(app.guid):
                time.sleep(0.5)
            ping_result = controller.trace(iface2.guid, "P2PAsciiTrace")
            comp_result = "- 19.021 /NodeList/1/DeviceList/0/$ns3::PointToPointNetDevice/TxQueue/Dequeue ns3::PppHeader (Point-to-Point Protocol: IP (0x0021)) ns3::Ipv4Header (tos 0x0 ttl 64 id 19 protocol 1 offset 0 flags [none] length: 84 10.0.0.2 > 10.0.0.1) ns3::Icmpv4Header (type=0, code=0) ns3::Icmpv4Echo (identifier=0, sequence=19)"
            if ping_result.find(comp_result) == -1:
                self.fail("Unexpected trace: %s" % (ping_result,))
        finally:
            controller.stop()
            controller.shutdown()

    @test_util.skipUnless(test_util.ns3_usable(), 
           "Test requires working ns-3 bindings")
    def test_all_daemonized_fd_net_device(self):
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

        self._test_fd_net_device(
            daemonize_testbed = True,
            controller_access_configuration = access_config)

    @test_util.skipUnless(test_util.ns3_usable(), 
           "Test requires working ns-3 bindings")
    def test_all_ssh_daemonized_fd_net_device(self):
        env = test_util.test_environment()

        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        access_config.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        access_config.set_attribute_value(DC.DEPLOYMENT_PORT, env.port)
        access_config.set_attribute_value(DC.USE_AGENT, True)
        
        self._test_fd_net_device(
            daemonize_testbed = True,
            controller_access_configuration = access_config)

    @test_util.skipUnless(test_util.ns3_usable(), 
           "Test requires working ns-3 bindings")
    def test_local_if(self):
        self._test_if(
            daemonize_testbed = False,
            controller_access_configuration = None)

    @test_util.skipUnless(test_util.ns3_usable(), 
           "Test requires working ns-3 bindings")
    def test_all_daemonized_if(self):
        access_config = proxy.AccessConfiguration()
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, self.root_dir)
        access_config.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

        self._test_if(
            daemonize_testbed = True,
            controller_access_configuration = access_config)

    @test_util.skipUnless(test_util.ns3_usable(), 
           "Test requires working ns-3 bindings")
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

