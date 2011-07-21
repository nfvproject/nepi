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
    
    slicename1 = "inria_nepi"
    plchost1 = "nepiplc.pl.sophia.inria.fr"

    slicename2 = "inria_nepi12"
    plchost2 = "www.planet-lab.eu"
    
    host1pl1 = "nepi1.pl.sophia.inria.fr"
    host2pl1 = "nepi2.pl.sophia.inria.fr"

    host1pl2 = "planetlab1.utt.fr"
    host2pl2 = "planetlab2.utt.fr"

    port_base = 2000 + (os.getpid() % 1000) * 13
    
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        self.port_base = self.port_base + 100

    def tearDown(self):
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def make_experiment_desc(self):
        testbed_id = self.testbed_id
        
        slicename1 = self.slicename1
        plchost1 = self.plchost1
        
        slicename2 = self.slicename2
        plchost2 = self.plchost2
        
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = test_util.pl_auth()

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id)
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
        iface1 = pl.create("NodeInterface")
        iface1.set_attribute_value("label", label_prefix+"iface")
        tap1 = pl.create("TapInterface")
        tap1.enable_trace("packets") # for error output
        tap1.set_attribute_value("label", label_prefix+"tap")
        inet = pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        node1.connector("devs").connect(tap1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        tap1ip = tap1.add_address()
        tap1ip.set_attribute_value("Address", tapip)
        tap1ip.set_attribute_value("NetPrefix", 24)
        tap1ip.set_attribute_value("Broadcast", False)
        
        return node1, iface1, tap1, tap1ip, inet
    
    def _test_plpl_crossconnect(self, proto):
        pl, pl2, exp = self.make_experiment_desc()
        
        # Create PL node, ifaces, assign addresses
        node1, iface1, tap1, tap1ip, inet1 = self.make_pl_tapnode(pl, 
            "192.168.2.2", self.host1pl1, "node1")
        node2, iface2, tap2, tap2ip, inet2 = self.make_pl_tapnode(pl2, 
            "192.168.2.3", self.host1pl2, "node2")
            
        # Connect the two
        tap1.connector(proto).connect(tap2.connector(proto))
        
        # Create PlanetLab ping application, pinging the from one PL to another
        ping = pl.create("Application")
        ping.set_attribute_value("command", "ping -qc10 {#[node2tap].addr[0].[Address]#}")
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
          
        ping_result = controller.trace(ping.guid, "stdout")
        tap_trace = controller.trace(tap1.guid, "packets")
        tap2_trace = controller.trace(tap2.guid, "packets")

        controller.stop()
        controller.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n%s\nTap trace at origin:\n%s\nTap trace at destination:\n%s\n" % (
                ping_result,
                tap_trace,
                tap2_trace) )

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_plpl_crossconnect_udp(self):
        self._test_plpl_crossconnect("udp")

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_plpl_crossconnect_tcp(self):
        self._test_plpl_crossconnect("tcp")


if __name__ == '__main__':
    unittest.main()

