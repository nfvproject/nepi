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

class NetnsExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.root_dir)

    def test_simple(self):
        testbed_version = "01"
        instance = planetlab.TestbedController(testbed_version)
        slicename = "inria_nepi12"
        
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_configure("slice", slicename)
        instance.defer_configure("sliceSSHKey", "/user/%s/home/.ssh/id_rsa_planetlab" % (getpass.getuser(),))
        instance.defer_configure("authUser", "claudio-daniel.freire@inria.fr")
        instance.defer_configure("authPass", getpass.getpass())
        
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
        instance.defer_create_set(7, "command", "ping -qc1 {#GUID-5.addr[0].[Address]#}")
        instance.defer_add_trace(7, "stdout")
        instance.defer_connect(7, "node", 2, "apps")

        instance.do_setup()
        instance.do_create()
        instance.do_connect()
        instance.do_preconfigure()
        instance.do_configure()
        
        # Manually replace netref
        instance.set(TIME_NOW, 7, "command",
            instance.get(TIME_NOW, 7, "command")
                .replace("{#GUID-5.addr[0].[Address]#}", 
                    instance.get_address(5, 0, "Address") )
        )
        
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
        

if __name__ == '__main__':
    unittest.main()

