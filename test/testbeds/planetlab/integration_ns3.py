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
        ns3_desc.set_attribute_value("homeDirectory", "tb-ns3")
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

if __name__ == '__main__':
    unittest.main()

