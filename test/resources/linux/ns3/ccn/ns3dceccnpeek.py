#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>


from nepi.execution.ec import ExperimentController 

from test_utils import skipIfNotAlive

import os
import time
import unittest

def add_ns3_node(ec, simu):
    node = ec.register_resource("ns3::Node")
    ec.register_connection(node, simu)

    ipv4 = ec.register_resource("ns3::Ipv4L3Protocol")
    ec.register_connection(node, ipv4)
    
    arp = ec.register_resource("ns3::ArpL3Protocol")
    ec.register_connection(node, arp)
    
    icmp = ec.register_resource("ns3::Icmpv4L4Protocol")
    ec.register_connection(node, icmp)

    udp = ec.register_resource("ns3::UdpL4Protocol")
    ec.register_connection(node, udp)

    tcp = ec.register_resource("ns3::TcpL4Protocol")
    ec.register_connection(node, tcp)

    return node

class LinuxNS3CCNPeekDceApplicationTest(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_nepi"
        self.fedora_identity = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])

    @skipIfNotAlive
    def t_dce_ccnpeek(self, host, user = None, identity = None):
        ec = ExperimentController(exp_id = "test-dce-ccnpeek")

        node = ec.register_resource("LinuxNode")
        if host == "localhost":
            ec.set(node, "hostname", host)
        else:
            ec.set(node, "hostname", host)
            ec.set(node, "username", user)
            ec.set(node, "identity", identity)
        
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.set(simu, "nsLog", "DceApplication")
        ec.register_connection(simu, node)

        nsnode = add_ns3_node(ec, simu)

        ### create applications
        ccnd = ec.register_resource("ns3::LinuxDceCCND")
        ec.set (ccnd, "stackSize", 1<<20)
        ec.set (ccnd, "StartTime", "1s")
        ec.register_connection(ccnd, nsnode)

        ccnpoke = ec.register_resource("ns3::LinuxDceCCNPoke")
        ec.set (ccnpoke, "contentName", "ccnx:/chunk0")
        ec.set (ccnpoke, "content", "DATA")
        ec.set (ccnpoke, "stackSize", 1<<20)
        ec.set (ccnpoke, "StartTime", "2s")
        ec.register_connection(ccnpoke, nsnode)

        ccnpeek = ec.register_resource("ns3::LinuxDceCCNPeek")
        ec.set (ccnpeek, "contentName", "ccnx:/chunk0")
        ec.set (ccnpeek, "stackSize", 1<<20)
        ec.set (ccnpeek, "StartTime", "4s")
        ec.set (ccnpeek, "StopTime", "20s")
        ec.register_connection(ccnpeek, nsnode)

        ec.deploy()

        ec.wait_finished([ccnpeek])

        expected = "ccnpeek ccnx:/chunk0"
        cmdline = ec.trace(ccnpeek, "cmdline")
        self.assertTrue(cmdline.find(expected) > -1, cmdline)

        expected = "Start Time: NS3 Time:          4s ("
        status = ec.trace(ccnpeek, "status")
        self.assertTrue(status.find(expected) > -1, status)

        expected = "DATA"
        stdout = ec.trace(ccnpeek, "stdout")
        self.assertTrue(stdout.find(expected) > -1, stdout)

        ec.shutdown()

    @skipIfNotAlive
    def t_dce_ccnpeek_with_stack(self, host, user = None, identity = None):
        ec = ExperimentController(exp_id = "test-dce-peek-lostack")
        
        node = ec.register_resource("LinuxNode")
        if host == "localhost":
            ec.set(node, "hostname", host)
        else:
            ec.set(node, "hostname", host)
            ec.set(node, "username", user)
            ec.set(node, "identity", identity)
        
        ec.set(node, "cleanProcesses", True)
        #ec.set(node, "cleanHome", True)

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.set(simu, "verbose", True)
        ec.register_connection(simu, node)

        nsnode = ec.register_resource("ns3::Node")
        ec.set(nsnode, "enableStack", True)
        ec.register_connection(nsnode, simu)

        ### create applications
        ccnd = ec.register_resource("ns3::LinuxDceCCND")
        ec.set (ccnd, "stackSize", 1<<20)
        ec.set (ccnd, "StartTime", "1s")
        ec.register_connection(ccnd, nsnode)

        ccnpoke = ec.register_resource("ns3::LinuxDceCCNPoke")
        ec.set (ccnpoke, "contentName", "ccnx:/chunk0")
        ec.set (ccnpoke, "content", "DATA")
        ec.set (ccnpoke, "stackSize", 1<<20)
        ec.set (ccnpoke, "StartTime", "2s")
        ec.register_connection(ccnpoke, nsnode)

        ccnpeek = ec.register_resource("ns3::LinuxDceCCNPeek")
        ec.set (ccnpeek, "contentName", "ccnx:/chunk0")
        ec.set (ccnpeek, "stackSize", 1<<20)
        ec.set (ccnpeek, "StartTime", "4s")
        ec.set (ccnpeek, "StopTime", "20s")
        ec.register_connection(ccnpeek, nsnode)

        ec.deploy()

        ec.wait_finished([ccnpeek])

        expected = "ccnpeek ccnx:/chunk0"
        cmdline = ec.trace(ccnpeek, "cmdline")
        self.assertTrue(cmdline.find(expected) > -1, cmdline)

        expected = "Start Time: NS3 Time:          4s ("
        status = ec.trace(ccnpeek, "status")
        self.assertTrue(status.find(expected) > -1, status)

        expected = "DATA"
        stdout = ec.trace(ccnpeek, "stdout")
        self.assertTrue(stdout.find(expected) > -1, stdout)

        ec.shutdown()

    def test_dce_ccnpeek_fedora(self):
        self.t_dce_ccnpeek(self.fedora_host, self.fedora_user, self.fedora_identity)

    def test_dce_ccnpeek_local(self):
        self.t_dce_ccnpeek("localhost")

    def test_dce_ccnpeek_with_stack_fedora(self):
        self.t_dce_ccnpeek_with_stack(self.fedora_host, 
                self.fedora_user, self.fedora_identity)

    def test_dce_ccnpeek_with_stack_local(self):
        self.t_dce_ccnpeek_with_stack("localhost")


if __name__ == '__main__':
    unittest.main()
