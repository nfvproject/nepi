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

class PlanetLabIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
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

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_simple(self):
        pl, exp = self.make_experiment_desc()
        
        node1 = pl.create("Node")
        node2 = pl.create("Node")
        node1.set_attribute_value("hostname", "onelab11.pl.sophia.inria.fr")
        node2.set_attribute_value("hostname", "onelab10.pl.sophia.inria.fr")
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
        controller.start()
        while not controller.is_finished(app.guid):
            time.sleep(0.5)
        ping_result = controller.trace(pl.guid, app.guid, "stdout")
        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time \d*ms.*
"""
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        controller.stop()
        controller.shutdown()

if __name__ == '__main__':
    unittest.main()

