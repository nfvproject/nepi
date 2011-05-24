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

class PlanetLabMultiIntegrationTestCase(unittest.TestCase):
    testbed_id = "planetlab"
    testbed_version = "01"
    
    slicename1 = "inria_nepi"
    plchost1 = "nepiplc.pl.sophia.inria.fr"

    slicename2 = "inria_nepi12"
    plchost2 = "www.planet-lab.eu"
    
    host1pl1 = "nepi1.pl.sophia.inria.fr"
    host2pl1 = "nepi2.pl.sophia.inria.fr"

    host1pl2 = "onelab11.pl.sophia.inria.fr"
    host2pl2 = "onelab10.pl.sophia.inria.fr"

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
        testbed_id = self.testbed_id
        testbed_version = self.testbed_version
        
        slicename1 = self.slicename1
        plchost1 = self.plchost1
        
        slicename2 = self.slicename2
        plchost2 = self.plchost2
        
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = test_util.pl_auth()

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id, testbed_version)
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", slicename1)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        pl_desc.set_attribute_value("plcHost", plchost1)

        pl_desc2 = exp_desc.add_testbed_description(pl_provider)
        pl_desc2.set_attribute_value("homeDirectory", self.root_dir+"v2")
        pl_desc2.set_attribute_value("slice", slicename2)
        pl_desc2.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc2.set_attribute_value("authUser", pl_user)
        pl_desc2.set_attribute_value("authPass", pl_pwd)
        pl_desc2.set_attribute_value("plcHost", plchost2)
        
        return pl_desc, pl_desc2, exp_desc
    
    def make_pl_tapnode(self, pl, tapip, hostname, label_prefix):
        node1 = pl.create("Node")
        node1.set_attribute_value("hostname", hostname)
        node1.set_attribute_value("label", label_prefix)
        node1.set_attribute_value("emulation", True) # require emulation
        iface1 = pl.create("NodeInterface")
        iface1.set_attribute_value("label", label_prefix+"iface")
        if tapip:
            tap1 = pl.create("TapInterface")
            tap1.enable_trace("packets") # for error output
            tap1.set_attribute_value("label", label_prefix+"tap")
            
            node1.connector("devs").connect(tap1.connector("node"))
            
            tap1ip = tap1.add_address()
            tap1ip.set_attribute_value("Address", tapip)
            tap1ip.set_attribute_value("NetPrefix", 24)
            tap1ip.set_attribute_value("Broadcast", False)
        else:
            tap1 = None
            tap1ip = None
        inet = pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        return node1, iface1, tap1, tap1ip, inet

    def make_ns_in_pl(self, pl, exp, node1, iface1, root):
        ns3_testbed_id = "ns3"
        ns3_testbed_version = "3_9_RC3"
        
        # Add NS3 support in node1
        plnepi = pl.create("NepiDependency")
        plns3 = pl.create("NS3Dependency")
        plnepi.connector("node").connect(node1.connector("deps"))
        plns3.connector("node").connect(node1.connector("deps"))

        # Create NS3 testbed running in node1
        ns3_provider = FactoriesProvider(ns3_testbed_id, ns3_testbed_version)
        ns3_desc = exp.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("rootDirectory", root)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[%s].addr[0].[Address]#}" % (
            iface1.get_attribute_value("label"),))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "{#[%s].[%s]#}" % (
                node1.get_attribute_value("label"),
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))
        ns3_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        
        return ns3_desc
    
    
    def _test_plns3_crossconnect(self, proto):
        pl, pl2, exp = self.make_experiment_desc()
        
        # Create PL node, ifaces, assign addresses
        node1, iface1, _, _, inet1 = self.make_pl_tapnode(pl, 
            None, self.host1pl1, "node1")
        node2, iface2, tap2, tap2ip, inet2 = self.make_pl_tapnode(pl2, 
            "192.168.2.3", self.host1pl2, "node2")

        # Create NS3 instance in node1
        # With a node and all required protocols to be pinged
        ns3 = self.make_ns_in_pl(pl, exp, node1, iface1, "tb-ns-rcross-1")

        ns1 = ns3.create("ns3::Node")
        ipv41 = ns3.create("ns3::Ipv4L3Protocol")
        arp1  = ns3.create("ns3::ArpL3Protocol")
        icmp1 = ns3.create("ns3::Icmpv4L4Protocol")
        ns1.connector("protos").connect(ipv41.connector("node"))
        ns1.connector("protos").connect(arp1.connector("node"))
        ns1.connector("protos").connect(icmp1.connector("node"))
        ns1if = ns3.create("ns3::FileDescriptorNetDevice")
        ns1if.enable_trace("FileDescriptorPcapTrace")
        ns1if.set_attribute_value("label", "ns1if")
        ns1tc = ns3.create("ns3::Nepi::TunChannel")
        ns1.connector("devs").connect(ns1if.connector("node"))
        ns1tc.connector("fd->").connect(ns1if.connector("->fd"))
        ip1 = ns1if.add_address()
        ip1.set_attribute_value("Address", "192.168.2.2")
        ip1.set_attribute_value("NetPrefix", 24)
        ip1.set_attribute_value("Broadcast", False)
            
        # Connect the two
        tap2.connector(proto).connect(ns1tc.connector(proto))
        
        # Create PlanetLab ping application, pinging the from one PL to another
        ping = pl2.create("Application")
        ping.set_attribute_value("command", "ping -qc10 {#[ns1if].addr[0].[Address]#}")
        ping.enable_trace("stdout")
        ping.enable_trace("stderr")
        ping.connector("node").connect(node2.connector("apps"))

        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
10 packets transmitted, 10 received, 0% packet loss, time \d*ms.*
"""

        xml = exp.to_xml()

        controller = ExperimentController(xml, self.root_dir)
        
        try:
            controller.start()

            while not controller.is_finished(ping.guid):
                time.sleep(0.5)
              
            ping_result = controller.trace(ping.guid, "stdout")
            tap2_trace = controller.trace(tap2.guid, "packets")
        finally:
            controller.stop()
            controller.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n%s\nTap trace:\n%s\n" % (
                ping_result,
                tap2_trace) )

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_plns3_crossconnect_udp(self):
        self._test_plns3_crossconnect("udp")

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_plns3_crossconnect_tcp(self):
        self._test_plns3_crossconnect("tcp")


if __name__ == '__main__':
    unittest.main()

