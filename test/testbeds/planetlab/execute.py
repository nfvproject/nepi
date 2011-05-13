#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.util.constants import STATUS_FINISHED
from nepi.testbeds import planetlab
import os
import shutil
import tempfile
import time
import unittest
import re
import test_util
import sys

class PlanetLabExecuteTestCase(unittest.TestCase):
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

    def make_instance(self):
        testbed_id = self.testbed_id
        testbed_version = self.testbed_version
        slicename = self.slicename
        plchost = self.plchost
        
        instance = planetlab.TestbedController(testbed_version)
        pl_ssh_key = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
        pl_user, pl_pwd = test_util.pl_auth()
        
        instance.defer_configure("homeDirectory", self.root_dir)
        instance.defer_configure("slice", slicename)
        instance.defer_configure("sliceSSHKey", pl_ssh_key)
        instance.defer_configure("authUser", pl_user)
        instance.defer_configure("authPass", pl_pwd)
        instance.defer_configure("plcHost", plchost)
        
        return instance

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_simple(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create(3, "Node")
        instance.defer_create_set(3, "hostname", self.host2)
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
        instance.defer_add_trace(7, "stderr")
        instance.defer_connect(7, "node", 2, "apps")

        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time \d*ms.*
"""

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            
            # Manually replace netref
            instance.set(7, "command",
                instance.get(7, "command")
                    .replace("{#[GUID-5].addr[0].[Address]#}", 
                        instance.get_address(5, 0, "Address") )
            )

            instance.do_configure()
            
            instance.start()
            while instance.status(7) != STATUS_FINISHED:
                time.sleep(0.5)
            ping_result = instance.trace(7, "stdout") or ""
            instance.stop()
        finally:
            instance.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        
    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_depends(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(5, "Application")
        instance.defer_create_set(5, "command", "gfortran --version")
        instance.defer_create_set(5, "depends", "gcc-gfortran")
        instance.defer_add_trace(5, "stdout")
        instance.defer_add_trace(5, "stderr")
        instance.defer_connect(5, "node", 2, "apps")

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            
            instance.start()
            while instance.status(5) != STATUS_FINISHED:
                time.sleep(0.5)
            ping_result = instance.trace(5, "stdout") or ""
            comp_result = r".*GNU Fortran \(GCC\).*"
            instance.stop()
        finally:
            instance.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        
    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_build(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(10, "Application")
        instance.defer_create_set(10, "command", "./consts")
        instance.defer_create_set(10, "buildDepends", "gcc")
        instance.defer_create_set(10, "build", "gcc ${SOURCES}/consts.c -o consts")
        instance.defer_create_set(10, "install", "cp consts ${SOURCES}/consts")
        instance.defer_create_set(10, "sources", os.path.join(os.path.dirname(planetlab.__file__),'scripts','consts.c'))
        instance.defer_add_trace(10, "stdout")
        instance.defer_add_trace(10, "stderr")
        instance.defer_connect(10, "node", 2, "apps")

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

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            
            instance.start()
            while instance.status(10) != STATUS_FINISHED:
                time.sleep(0.5)
            ping_result = instance.trace(10, "stdout") or ""
            instance.stop()
        finally:
            instance.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n" + ping_result)
        
    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_simple_vsys(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create_set(2, "emulation", True) # require emulation
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(5, "TunInterface")
        instance.defer_add_address(5, "192.168.2.2", 24, False)
        instance.defer_connect(2, "devs", 5, "node")
        instance.defer_create(6, "Application")
        instance.defer_create_set(6, "command", """
set -e
netconfig help > /dev/null
test -e /vsys/vif_up.in > /dev/null
test -e /vsys/vif_up.out > /dev/null
test -e /vsys/fd_tuntap.control > /dev/null
echo 'OKIDOKI'
""")
        instance.defer_create_set(6, "sudo", True) # only sudo has access to /vsys
        instance.defer_add_trace(6, "stdout")
        instance.defer_add_trace(6, "stderr")
        instance.defer_connect(6, "node", 2, "apps")

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            
            instance.start()
            while instance.status(6) != STATUS_FINISHED:
                time.sleep(0.5)
            test_result = (instance.trace(6, "stdout") or "").strip()
            comp_result = "OKIDOKI"
            instance.stop()
        finally:
            instance.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertEqual(comp_result, test_result)

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_emulation(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create_set(2, "emulation", True) # require emulation
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(7, "NetPipe")
        instance.defer_create_set(7, "mode", "CLIENT")
        instance.defer_create_set(7, "portList", "80")
        instance.defer_create_set(7, "bwOut", 12.0/1024.0) # 12kbps
        instance.defer_create_set(7, "bwIn", 64.0/1024.0) # 64kbps
        instance.defer_create_set(7, "plrOut", 0.01) # 1% plr outbound - high loss
        instance.defer_create_set(7, "plrIn", 0.001) # 0.1% plr inbound - regular loss
        instance.defer_create_set(7, "delayOut", int(1500 * 8 / (12.0/1024.0) / 1000)) # tx delay at 12kbps in ms
        instance.defer_create_set(7, "delayIn", int(1500 * 8 / (64.0/1024.0) / 1000)) # rx delay at 64kbps in ms
        instance.defer_add_trace(7, "netpipeStats")
        instance.defer_connect(2, "pipes", 7, "node")
        instance.defer_create(8, "Application")
        instance.defer_create_set(8, "command", "time wget -q -O /dev/null http://www.google.com/") # Fetch ~10kb
        instance.defer_add_trace(8, "stdout")
        instance.defer_add_trace(8, "stderr")
        instance.defer_connect(8, "node", 2, "apps")

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            
            instance.start()
            while instance.status(8) != STATUS_FINISHED:
                time.sleep(0.5)
            test_result = (instance.trace(8, "stderr") or "").strip()
            comp_result = r".*real\s*(?P<min>[0-9]+)m(?P<sec>[0-9]+[.][0-9]+)s.*"
            netpipe_stats = instance.trace(7, "netpipeStats")
            
            instance.stop()
        finally:
            instance.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        match = re.match(comp_result, test_result, re.MULTILINE)
        self.assertTrue(match, "Unexpected output: %s" % (test_result,))
        
        minutes = int(match.group("min"))
        seconds = float(match.group("sec"))
        self.assertTrue((minutes * 60 + seconds) > 1.0, "Emulation not effective: %s" % (test_result,))

        self.assertTrue(netpipe_stats, "Unavailable netpipe stats")

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_tun_emulation_requirement(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(5, "TunInterface")
        instance.defer_add_address(5, "192.168.2.2", 24, False)
        instance.defer_connect(2, "devs", 5, "node")
        instance.defer_create(6, "Application")
        instance.defer_create_set(6, "command", "false")
        instance.defer_add_trace(6, "stdout")
        instance.defer_add_trace(6, "stderr")
        instance.defer_connect(6, "node", 2, "apps")

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            self.fail("Usage of TUN without emulation should fail")
        except Exception,e:
            pass

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def _pingtest(self, TunClass, ConnectionProto):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create_set(2, "emulation", True) # require emulation
        instance.defer_create(3, "Node")
        instance.defer_create_set(3, "hostname", self.host2)
        instance.defer_create_set(3, "emulation", True) # require emulation
        instance.defer_create(4, "NodeInterface")
        instance.defer_connect(2, "devs", 4, "node")
        instance.defer_create(5, "Internet")
        instance.defer_connect(4, "inet", 5, "devs")
        instance.defer_create(6, "NodeInterface")
        instance.defer_connect(3, "devs", 6, "node")
        instance.defer_connect(6, "inet", 5, "devs")
        instance.defer_create(7, TunClass)
        instance.defer_add_trace(7, "packets")
        instance.defer_add_address(7, "192.168.2.2", 24, False)
        instance.defer_connect(2, "devs", 7, "node")
        instance.defer_create(8, TunClass)
        instance.defer_add_trace(8, "packets")
        instance.defer_add_address(8, "192.168.2.3", 24, False)
        instance.defer_connect(3, "devs", 8, "node")
        instance.defer_connect(7, ConnectionProto, 8, ConnectionProto)
        instance.defer_create(9, "Application")
        instance.defer_create_set(9, "command", "ping -qc1 {#[GUID-8].addr[0].[Address]#}")
        instance.defer_add_trace(9, "stdout")
        instance.defer_add_trace(9, "stderr")
        instance.defer_connect(9, "node", 2, "apps")

        comp_result = r"""PING .* \(.*\) \d*\(\d*\) bytes of data.

--- .* ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time \d*ms.*
"""

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            
            # Manually replace netref
            instance.set(9, "command",
                instance.get(9, "command")
                    .replace("{#[GUID-8].addr[0].[Address]#}", 
                        instance.get_address(8, 0, "Address") )
            )
            
            instance.do_configure()
            
            instance.start()
            while instance.status(9) != STATUS_FINISHED:
                time.sleep(0.5)
            ping_result = instance.trace(9, "stdout") or ""
            packets1 = instance.trace(7, "packets") or ""
            packets2 = instance.trace(8, "packets") or ""
            instance.stop()
        finally:
            instance.shutdown()

        # asserts at the end, to make sure there's proper cleanup
        self.assertTrue(re.match(comp_result, ping_result, re.MULTILINE),
            "Unexpected trace:\n%s\nPackets @ source:\n%s\nPackets @ target:\n%s" % (
                ping_result,
                packets1,
                packets2))

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_tun_ping(self):
        self._pingtest("TunInterface", "tcp")

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_tun_ping_udp(self):
        self._pingtest("TunInterface", "udp")

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_tap_ping(self):
        self._pingtest("TapInterface", "tcp")

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_tap_ping_udp(self):
        self._pingtest("TapInterface", "udp")

    @test_util.skipUnless(test_util.pl_auth() is not None, "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    def test_nepi_depends(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(5, "NepiDependency")
        instance.defer_connect(5, "node", 2, "deps")
        instance.defer_create(12, "Application")
        instance.defer_connect(12, "node", 2, "apps")
        instance.defer_create_set(12, "command", "python -c 'import nepi'")
        instance.defer_add_trace(12, "stderr")

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            
            instance.start()
            while instance.status(12) != STATUS_FINISHED:
                time.sleep(0.5)
            ping_result = (instance.trace(12, "stderr") or "").strip()
            instance.stop()
        finally:
            instance.shutdown()
        
        # asserts at the end, to make sure there's proper cleanup
        self.assertEqual(ping_result, "")

    @test_util.skipUnless(test_util.pl_auth() is not None, 
        "Test requires PlanetLab authentication info (PL_USER and PL_PASS environment variables)")
    @test_util.skipUnless(os.environ.get('NEPI_FULL_TESTS','').lower() in ('1','yes','true','on'),
        "Test is expensive, requires NEPI_FULL_TESTS=yes")
    def test_ns3_depends(self):
        instance = self.make_instance()
        
        instance.defer_create(2, "Node")
        instance.defer_create_set(2, "hostname", self.host1)
        instance.defer_create(3, "NodeInterface")
        instance.defer_connect(2, "devs", 3, "node")
        instance.defer_create(4, "Internet")
        instance.defer_connect(3, "inet", 4, "devs")
        instance.defer_create(5, "NepiDependency")
        instance.defer_connect(5, "node", 2, "deps")
        instance.defer_create(6, "NS3Dependency")
        instance.defer_connect(6, "node", 2, "deps")
        instance.defer_create(12, "Application")
        instance.defer_connect(12, "node", 2, "apps")
        instance.defer_create_set(12, "command", "python -c 'import nepi.testbeds.ns3.execute ; tb = nepi.testbeds.ns3.execute.TestbedController(\"3_9_RC3\") ; mod = tb._load_ns3_module()'")
        instance.defer_add_trace(12, "stderr")

        try:
            instance.do_setup()
            instance.do_create()
            instance.do_connect_init()
            instance.do_connect_compl()
            instance.do_preconfigure()
            instance.do_configure()
            
            instance.start()
            while instance.status(12) != STATUS_FINISHED:
                time.sleep(0.5)
            ping_result = (instance.trace(12, "stderr") or "").strip()
            instance.stop()
        finally:
            instance.shutdown()
        
        # asserts at the end, to make sure there's proper cleanup
        self.assertEqual(ping_result, "")
        

if __name__ == '__main__':
    unittest.main()

