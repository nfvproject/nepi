#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.util.constants import STATUS_FINISHED, TIME_NOW
from nepi.testbeds import planetlab
import os
import shutil
import tempfile
import time
import unittest
import re
import test_util

class PlanetLabExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.root_dir)

    def make_instance(self):
        testbed_version = "01"
        instance = planetlab.TestbedController(testbed_version)
        slicename = "inria_nepi12"
        pl_user, pl_pwd = test_util.pl_auth()
        
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_configure("slice", slicename)
        instance.defer_configure("sliceSSHKey", "/user/%s/home/.ssh/id_rsa_planetlab" % (getpass.getuser(),))
        instance.defer_configure("authUser", pl_user)
        instance.defer_configure("authPass", pl_pwd)
        
        return instance

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_simple(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", "onelab11.pl.sophia.inria.fr")
        instance.defer_create(3, "Node")
        instance.defer_create_set(3, "hostname", "onelab10.pl.sophia.inria.fr")
        instance.defer_create(4, "NodeInterface")
        instance.defer_connect(2, "devs", 4, "node")
        instance.defer_create(5, "NodeInterface")
        instance.defer_connect(3, "devs", 5, "node")
        instance.defer_create(6, "Internet")
        instance.defer_connect(4, "inet", 6, "devs")
        instance.defer_connect(5, "inet", 6, "devs")
        instance.defer_create(7, "Application")
        instance.defer_create_set(7, "command", "ping -qc1 {#[GUID-5].addr[0].[Address]#}")
        instance.defer_add_trace(7, "stdout")
        instance.defer_connect(7, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        
        # Manually replace netref
        instance.set(TIME_NOW, 7, "command",
            instance.get(TIME_NOW, 7, "command")
                .replace("{#[GUID-5].addr[0].[Address]#}", 
                    instance.get_address(5, 0, "Address") )
        )

        instance.do_configure()
        
        instance.start()
        while instance.status(7) != STATUS_FINISHED:
            time.sleep(0.5)
        ping_result = instance.trace(7, "stdout") or ""
        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time \d*ms.*
"""
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        instance.stop()
        instance.shutdown()
        
    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_depends(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", "onelab11.pl.sophia.inria.fr")
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(5, "Application")
        instance.defer_create_set(5, "command", "gfortran --version")
        instance.defer_create_set(5, "depends", "gcc-gfortran")
        instance.defer_add_trace(5, "stdout")
        instance.defer_connect(5, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        
        instance.start()
        while instance.status(5) != STATUS_FINISHED:
            time.sleep(0.5)
        ping_result = instance.trace(5, "stdout") or ""
        comp_result = r".*GNU Fortran \(GCC\).*"
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        instance.stop()
        instance.shutdown()
        
    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_build(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", "onelab11.pl.sophia.inria.fr")
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(10, "Application")
        instance.defer_create_set(10, "command", "./consts")
        instance.defer_create_set(10, "buildDepends", "gcc")
        instance.defer_create_set(10, "build", "gcc consts.c -o consts")
        instance.defer_create_set(10, "sources", os.path.join(os.path.dirname(planetlab.__file__),'scripts','consts.c'))
        instance.defer_add_trace(10, "stdout")
        instance.defer_connect(10, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        
        instance.start()
        while instance.status(10) != STATUS_FINISHED:
            time.sleep(0.5)
        ping_result = instance.trace(10, "stdout") or ""
        comp_result = \
r""".*ETH_P_ALL = 0x[0-9a-fA-F]{8}
ETH_P_IP = 0x[0-9a-fA-F]{8}
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
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        instance.stop()
        instance.shutdown()
        

if __name__ == '__main__':
    unittest.main()
