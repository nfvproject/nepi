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
    testbed_id = "planetlab"
    testbed_version = "01"
    slicename = "inria_nepi"
    plchost = "nepiplc.pl.sophia.inria.fr"
    
    host1 = "nepi1.pl.sophia.inria.fr"
    host2 = "nepi2.pl.sophia.inria.fr"

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
        slicename = self.slicename
        plchost = self.plchost
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
        pl_desc.set_attribute_value("plcHost", plchost)
        
        return pl_desc, exp_desc
    
    def make_pl_tapnode(self, pl):
        node1 = pl.create("Node")
        node1.set_attribute_value("hostname", self.host1)
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
    

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_ns3_in_pl(self):
        ns3_testbed_id = "ns3"
        ns3_testbed_version = "3_9_RC3"
        
        pl, exp = self.make_experiment_desc()
        
        node1 = pl.create("Node")
        node1.set_attribute_value("hostname", self.host1)
        node1.set_attribute_value("label", "node1")
        iface1 = pl.create("NodeInterface")
        iface1.set_attribute_value("label", "node1iface")
        inet = pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        # Add NS3 support in node1
        ns3_desc = self.make_ns_in_pl(pl, exp, node1, iface1, "tb-ns3-1")

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
        pl, exp = self.make_experiment_desc()
        
        # Create PL node, ifaces, assign addresses
        node1, iface1, tap1, tap1ip, inet = self.make_pl_tapnode(pl)
        
        # Add NS3 support in node1
        ns3_desc = self.make_ns_in_pl(pl, exp, node1, iface1, "tb-ns3-2")
        
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
        ns1if.enable_trace("FileDescriptorPcapTrace")
        ns1if.set_attribute_value("label", "ns1if")
        ns1.connector("devs").connect(ns1if.connector("node"))
        tap1.connector("fd->").connect(ns1if.connector("->fd"))
        ip1 = ns1if.add_address()
        ip1.set_attribute_value("Address", "192.168.2.3")
        ip1.set_attribute_value("NetPrefix", 24)
        ip1.set_attribute_value("Broadcast", False)

        # Create PlanetLab ping application, pinging the NS3 node
        ping = pl.create("Application")
        ping.set_attribute_value("command", "ping -qc10 {#[ns1if].addr[0].[Address]#}")
        ping.enable_trace("stdout")
        ping.enable_trace("stderr")
        ping.connector("node").connect(node1.connector("apps"))

        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
10 packets transmitted, 10 received, 0% packet loss, time \d*ms.*
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

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_ns3_in_pl_snat(self):
        pl, exp = self.make_experiment_desc()
        
        # Create PL node, ifaces, assign addresses
        node1, iface1, tap1, tap1ip, inet = self.make_pl_tapnode(pl)
        
        # Add NS3 support in node1
        ns3_desc = self.make_ns_in_pl(pl, exp, node1, iface1, "tb-ns3-3")
        
        # Enable SNAT
        tap1.set_attribute_value("snat", True)
        
        # Add second PL node (ping target)
        node2 = pl.create("Node")
        node2.set_attribute_value("hostname", self.host2)
        node2.set_attribute_value("label", "node2")
        iface2 = pl.create("NodeInterface")
        iface2.set_attribute_value("label", "node2iface")
        node2.connector("devs").connect(iface2.connector("node"))
        iface2.connector("inet").connect(inet.connector("devs"))
        
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
        ns1if.enable_trace("FileDescriptorPcapTrace")
        ns1if.set_attribute_value("label", "ns1if")
        ns1.connector("devs").connect(ns1if.connector("node"))
        tap1.connector("fd->").connect(ns1if.connector("->fd"))
        ip1 = ns1if.add_address()
        ip1.set_attribute_value("Address", "192.168.2.3")
        ip1.set_attribute_value("NetPrefix", 24)
        ip1.set_attribute_value("Broadcast", False)
        
        # Add default route to the PL node
        r1 = ns1.add_route()
        r1.set_attribute_value("Destination", "0.0.0.0")
        r1.set_attribute_value("NetPrefix", 0)
        r1.set_attribute_value("NextHop", "192.168.2.2")

        # Create NS3 ping application, pinging the PL node
        ping = ns3_desc.create("ns3::V4Ping")
        ping.set_attribute_value("Remote", "{#[node2iface].addr[0].[Address]#}")
        ping.set_attribute_value("StartTime", "0s")
        ping.set_attribute_value("StopTime", "10s")
        ping.connector("node").connect(ns1.connector("apps"))

        xml = exp.to_xml()

        controller = ExperimentController(xml, self.root_dir)
        controller.start()

        while not controller.is_finished(ping.guid):
            time.sleep(0.5)
          
        tap_trace = controller.trace(pl.guid, tap1.guid, "packets")

        controller.stop()
        controller.shutdown()
        
        # asserts at the end, to make sure there's proper cleanup
        sent = 0
        replied = 0
        for seq in xrange(10):
            re_send = r""".*
[0-9.:]* IP 192.168.2.3 > (\d*\.){3}\d*: ICMP echo request, id 0, seq %(seq)d, length \d*
.*""" % dict(seq=seq)

            re_reply = r""".*
[0-9.:]* IP 192.168.2.3 > (\d*\.){3}\d*: ICMP echo request, id 0, seq %(seq)d, length \d*.*
[0-9.:]* IP (\d*\.){3}\d* > 192.168.2.3: ICMP echo reply, id 0, seq %(seq)d, length \d*
.*""" % dict(seq=seq)

            sent += bool(re.match(re_send, tap_trace, re.MULTILINE|re.DOTALL))
            replied += bool(re.match(re_reply, tap_trace, re.MULTILINE|re.DOTALL))

        self.assertTrue(sent == replied and sent > 5,
            "Unexpected trace:\n%s\n" % (
                tap_trace,) )

if __name__ == '__main__':
    unittest.main()

