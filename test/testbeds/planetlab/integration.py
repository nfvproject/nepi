#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
import os
import shutil
import tempfile
import test_util
import time
import unittest
import re
import sys

class PlanetLabIntegrationTestCase(unittest.TestCase):
    testbed_id = "planetlab"
    slicename = "inria_nepi"
    plchost = "nepiplc.pl.sophia.inria.fr"
    
    host1 = "nepi1.pl.sophia.inria.fr"
    host2 = "nepi2.pl.sophia.inria.fr"
    host3 = "nepi3.pl.sophia.inria.fr"
    host4 = "nepi5.pl.sophia.inria.fr"

    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
        return
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def make_experiment_desc(self):
        testbed_id = self.testbed_id
        slicename = self.slicename
        plchost = self.plchost
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = test_util.pl_auth()

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id)
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", slicename)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        pl_desc.set_attribute_value("plcHost", plchost)
        
        return pl_desc, exp_desc

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_simple(self):
        pl, exp = self.make_experiment_desc()
        
        node1 = pl.create("Node")
        node2 = pl.create("Node")
        node1.set_attribute_value("hostname", self.host1)
        node2.set_attribute_value("hostname", self.host2)
        iface1 = pl.create("NodeInterface")
        iface2 = pl.create("NodeInterface")
        iface2.set_attribute_value("label", "node2iface")
        inet = pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        node2.connector("devs").connect(iface2.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        iface2.connector("inet").connect(inet.connector("devs"))
        app = pl.create("Application")
        app.set_attribute_value("command", "ping -qc1 {#[node2iface].addr[0].[Address]#}")
        app.enable_trace("stdout")
        app.connector("node").connect(node1.connector("apps"))

        xml = exp.to_xml()

        controller = ExperimentController(xml, self.root_dir)
        try:
            controller.start()
            while not controller.is_finished(app.guid):
                time.sleep(0.5)
            ping_result = controller.trace(app.guid, "stdout")
            comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time \d*ms.*
"""
            self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
                "Unexpected trace:\n" + ping_result)
        
        finally:
            controller.stop()
            controller.shutdown()


    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_spanning_deployment(self):
        pl, exp = self.make_experiment_desc()
        
        from nepi.testbeds import planetlab as plpackage
        
        nodes = [ pl.create("Node") for i in xrange(4) ]
        ifaces = [ pl.create("NodeInterface") for node in nodes ]
        inet = pl.create("Internet")
        for node, iface in zip(nodes,ifaces):
            node.connector("devs").connect(iface.connector("node"))
            iface.connector("inet").connect(inet.connector("devs"))
        
        apps = []
        for node in nodes:
            app = pl.create("Application")
            app.set_attribute_value("command", "./consts")
            app.set_attribute_value("buildDepends", "gcc")
            app.set_attribute_value("build", "gcc ${SOURCES}/consts.c -o consts")
            app.set_attribute_value("install", "cp consts ${SOURCES}/consts")
            app.set_attribute_value("sources", os.path.join(
                os.path.dirname(plpackage.__file__),'scripts','consts.c'))
            app.enable_trace("stdout")
            app.enable_trace("stderr")
            app.enable_trace("buildlog")
            node.connector("apps").connect(app.connector("node"))
            apps.append(app)

        comp_result = \
r""".*ETH_P_ALL = 0x[0-9a-fA-F]{8}
ETH_P_IP = 0x[0-9a-fA-F]{8}
TUNGETIFF = 0x[0-9a-fA-F]{8}
TUNSETIFF = 0x[0-9a-fA-F]{8}
IFF_NO_PI = 0x[0-9a-fA-F]{8}
IFF_TAP = 0x[0-9a-fA-F]{8}
IFF_TUN = 0x[0-9a-fA-F]{8}
IFF_VNET_HDR = 0x[0-9a-fA-F]{8}
TUN_PKT_STRIP = 0x[0-9a-fA-F]{8}
IFHWADDRLEN = 0x[0-9a-fA-F]{8}
IFNAMSIZ = 0x[0-9a-fA-F]{8}
IFREQ_SZ = 0x[0-9a-fA-F]{8}
FIONREAD = 0x[0-9a-fA-F]{8}.*
"""

        comp_build = r".*(Identity added|gcc).*"

        xml = exp.to_xml()

        controller = ExperimentController(xml, self.root_dir)
        try:
            controller.start()
            while not all(controller.is_finished(app.guid) for app in apps):
                time.sleep(0.5)
            
            for app in apps:
                app_result = controller.trace(app.guid, "stdout") or ""
                self.assertTrue(re.match(comp_result, app_result, re.MULTILINE),
                    "Unexpected trace:\n" + app_result)

                build_result = controller.trace(app.guid, "buildlog") or ""
                self.assertTrue(re.match(comp_build, build_result, re.MULTILINE | re.DOTALL),
                    "Unexpected trace:\n" + build_result)
        
        finally:
            controller.stop()
            controller.shutdown()
        

if __name__ == '__main__':
    unittest.main()

