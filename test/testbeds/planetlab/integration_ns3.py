#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP
import os
import shutil
import tempfile
import test_util
import time
import unittest
import re

class PlanetLabCrossIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def make_experiment_desc(self):
        testbed_id = "planetlab"
        testbed_version = "01"
        slicename = "inria_nepi12"
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = test_util.pl_auth()

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id, testbed_version)
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", slicename)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        
        return pl_desc, exp_desc

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_ns3_in_pl(self):
        ns3_testbed_id = "ns3"
        ns3_testbed_version = "3_9_RC3"
        
        pl, exp = self.make_experiment_desc()
        
        node1 = pl.create("Node")
        node1.set_attribute_value("hostname", "onelab11.pl.sophia.inria.fr")
        node1.set_attribute_value("label", "node1")
        iface1 = pl.create("NodeInterface")
        iface1.set_attribute_value("label", "node1iface")
        inet = pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        plnepi = pl.create("NepiDependency")
        plns3 = pl.create("NS3Dependency")
        plnepi.connector("node").connect(node1.connector("deps"))
        plns3.connector("node").connect(node1.connector("deps"))

        ns3_provider = FactoriesProvider(ns3_testbed_id, ns3_testbed_version)
        ns3_desc = exp.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("rootDirectory", "tb-ns3")
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[node1iface].addr[0].[Address]#}")
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "{#[node1].[%s]#}" % (ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))

        xml = exp.to_xml()

        controller = ExperimentController(xml, self.root_dir)
        controller.start()
        # just test that it starts...
        controller.stop()
        controller.shutdown()

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_ns3_in_pl_crossconnect(self):
        ns3_testbed_id = "ns3"
        ns3_testbed_version = "3_9_RC3"
        
        pl, exp = self.make_experiment_desc()
        
        # Create PL node, ifaces, assign addresses
        node1 = pl.create("Node")
        node1.set_attribute_value("hostname", "onelab11.pl.sophia.inria.fr")
        node1.set_attribute_value("label", "node1")
        node1.set_attribute_value("emulation", True) # require emulation
        iface1 = pl.create("NodeInterface")
        iface1.set_attribute_value("label", "node1iface")
        tap1 = pl.create("TapInterface")
        tap1.enable_trace("packets") # for error output
        tap1.set_attribute_value("label", "node1tap")
        inet = pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        node1.connector("devs").connect(tap1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        tap1ip = tap1.add_address()
        tap1ip.set_attribute_value("Address", "192.168.2.2")
        tap1ip.set_attribute_value("NetPrefix", 24)
        tap1ip.set_attribute_value("Broadcast", False)
        
        # Add NS3 support in node1
        plnepi = pl.create("NepiDependency")
        plns3 = pl.create("NS3Dependency")
        plnepi.connector("node").connect(node1.connector("deps"))
        plns3.connector("node").connect(node1.connector("deps"))

        # Create NS3 testbed running in node1
        ns3_provider = FactoriesProvider(ns3_testbed_id, ns3_testbed_version)
        ns3_desc = exp.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("rootDirectory", "tb-ns3")
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[node1iface].addr[0].[Address]#}")
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP, 
            "{#[node1].[%s]#}" % (ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))

        
        # Create NS3 node that is responsive to pings, connected
        # to node1 through the Tap interface
        ns1 = ns3_desc.create("ns3::Node")
        ipv41 = ns3_desc.create("ns3::Ipv4L3Protocol")
        arp1  = ns3_desc.create("ns3::ArpL3Protocol")
        icmp1 = ns3_desc.create("ns3::Icmpv4L4Protocol")
        ns1.connector("protos").connect(ipv41.connector("node"))
        ns1.connector("protos").connect(arp1.connector("node"))
        ns1.connector("protos").connect(icmp1.connector("node"))
        ns1if = ns3_desc.create("ns3::FileDescriptorNetDevice")
        ns1if.set_attribute_value("label", "ns1if")
        ns1.connector("devs").connect(ns1if.connector("node"))
        tap1.connector("fd->").connect(ns1if.connector("->fd"))
        ip1 = ns1if.add_address()
        ip1.set_attribute_value("Address", "192.168.2.3")
        ip1.set_attribute_value("NetPrefix", 24)
        ip1.set_attribute_value("Broadcast", False)

        # Create PlanetLab ping application, pinging the NS3 node
        ping = pl.create("Application")
        ping.set_attribute_value("command", "ping -qc1 {#[GUID-8].addr[0].[Address]#}")
        ping.enable_trace("stdout")
        ping.enable_trace("stderr")
        ping.connector("node").connect(node1.connector("apps"))

        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time \d*ms.*
"""

        xml = exp.to_xml()

        controller = ExperimentController(xml, self.root_dir)
        controller.start()

        while not controller.is_finished(ping.guid):
            time.sleep(0.5)
          
        ping_result = controller.trace(pl.guid, ping.guid, "stdout")
        tap_trace = controller.trace(pl.guid, tap1.guid, "packets")

        controller.stop()
        controller.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n%s\nTap trace:\n%s\n" % (
                ping_result,
                tap_trace) )

if __name__ == '__main__':
    unittest.main()

