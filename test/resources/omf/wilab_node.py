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
# Author: Lucia Guevgeozian <lucia.guevgeozian_odizzio@inria.fr>

from nepi.execution.ec import ExperimentController
from nepi.resources.omf.wilabt_node import WilabtSfaNode
from nepi.util.sfaapi import SFAAPI, SFAAPIFactory

from test_utils import skipIfNotSfi

import os
import time
import unittest
import multiprocessing

class DummyEC(ExperimentController):
    pass

class WilabtSfaNodeFactoryTestCase(unittest.TestCase):

    def test_creation_phase(self):
        self.assertEquals(WilabtSfaNode._rtype, "WilabtSfaNode")
        self.assertEquals(len(WilabtSfaNode._attributes), 17)

class WilabtSfaNodeTestCase(unittest.TestCase):
    """
    This tests use inria_nepi slice, from the test instance of MyPLC
    nepiplc.pl.sophia.inria.fr. This test can fail if the user running
    the test does not have a user in this instance of MyPLC or is not
    added to the inria_nepi slice.
    """

    def setUp(self):
        self.ec = DummyEC()
        #slicepl = os.environ.get('SFA_SLICE')
        #slicename = ['ple'] + slicepl.split('_')
        #self.slicename = '.'.join(slicename)
        self.slicename = os.environ.get('SFA_SLICE')
        self.sfauser = os.environ.get('SFA_USER')
        self.sfaPrivateKey = os.environ.get('SFA_PK')
        
    @skipIfNotSfi
    def test_a_sfaapi(self):
        """
        Check that the api to discover and reserve resources is well
        instanciated, and is an instance of SFAAPI. Check that using
        the same credentials, the same object of the api is used.
        """
        node1 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node1, "host", "zotacE5")
        self.ec.set(node1, "slicename", self.slicename)
        self.ec.set(node1, "sfauser", self.sfauser)
        self.ec.set(node1, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node1, "gatewayUser", "nepi")
        self.ec.set(node1, "gateway", "bastion.test.iminds.be")

        wnode_rm1 = self.ec.get_resource(node1)

        self.assertIsNone(wnode_rm1._node_to_provision)

        api1 = wnode_rm1.sfaapi
        self.assertIsInstance(api1, SFAAPI)
        self.assertEquals(len(api1._reserved), 0)
        self.assertEquals(len(api1._blacklist), 0)

        node2 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node2, "host", "zotacM20")
        self.ec.set(node2, "slicename", self.slicename)
        self.ec.set(node2, "sfauser", self.sfauser)
        self.ec.set(node2, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node1, "gatewayUser", "nepi")
        self.ec.set(node1, "gateway", "bastion.test.iminds.be")

        wnode_rm2 = self.ec.get_resource(node2)
        api2 = wnode_rm2.sfaapi
        self.assertEquals(api1, api2)

        wnode_rm1.sfaapi._reserved = set()
        wnode_rm1.sfaapi._blacklist = set()
    
    @skipIfNotSfi
    def test_discover(self):
        """
        Check that the method do_discover reserve the right node.
        """
        node1 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node1, "host", "zotacE5")
        self.ec.set(node1, "slicename", self.slicename)
        self.ec.set(node1, "sfauser", self.sfauser)
        self.ec.set(node1, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node1, "gatewayUser", "nepi")
        self.ec.set(node1, "gateway", "bastion.test.iminds.be")

        wnode_rm = self.ec.get_resource(node1)
       
        host = wnode_rm.get("host")
        self.assertIsNotNone(host)

        self.assertEquals(wnode_rm.sfaapi._reserved, set())

        wnode_rm.do_discover()
        self.assertEquals(len(wnode_rm.sfaapi._reserved), 1)
        self.assertEquals(wnode_rm._node_to_provision, 'wilab2.ilabt.iminds.be.zotacE5')

        wnode_rm.sfaapi._reserved = set()
        wnode_rm.sfaapi._blacklist = set()

    @skipIfNotSfi
    def test_provision(self):
        """
        This test checks that the method do_provision add the node in the slice and check
        its well functioning.
        """
        node = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node, "host", "zotacE5")
        self.ec.set(node, "slicename", self.slicename)
        self.ec.set(node, "sfauser", self.sfauser)
        self.ec.set(node, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node, "gatewayUser", "nepi")
        self.ec.set(node, "gateway", "bastion.test.iminds.be")

        wnode_rm = self.ec.get_resource(node)

        self.assertEquals(wnode_rm.sfaapi._reserved, set())
        self.assertIsNone(wnode_rm._node_to_provision)

        wnode_rm.do_discover()
        #with self.assertRaises(RuntimeError):
        #    wnode_rm.do_provision()
        wnode_rm.do_provision()

        if not self.ec.abort and self.ec.state(node) > 2:
            cmd = 'echo "IT WORKED"'
            ((out, err), proc) = wnode_rm.execute(cmd)
            self.assertEquals(out.strip(), "IT WORKED")

        #wnode_rm.sfaapi._reserved = set()
        #wnode_rm.sfaapi._blacklist = set()

        self.ec.shutdown()

    @skipIfNotSfi
    def test_xdeploy1(self):
        """
        Test deploy 1 node.
        """
        node = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node, "host", "zotacM20")
        self.ec.set(node, "slicename", self.slicename)
        self.ec.set(node, "sfauser", self.sfauser)
        self.ec.set(node, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node, "gatewayUser", "nepi")
        self.ec.set(node, "gateway", "bastion.test.iminds.be")

        self.ec.deploy()
        self.ec.wait_deployed(node)
        state = self.ec.state(node)
        if not self.ec.abort:
            self.assertIn(state, (3, 4))

        wnode_rm = self.ec.get_resource(node)
        wnode_rm.sfaapi._reserved = set()
        wnode_rm.sfaapi._blacklist = set()

        self.ec.shutdown()

    @skipIfNotSfi
    def test_xdeploy2(self):
        """
        Test deploy 2 nodes.
        """
        node1 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node1, "host", "zotacE3")
        self.ec.set(node1, "slicename", self.slicename)
        self.ec.set(node1, "sfauser", self.sfauser)
        self.ec.set(node1, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node1, "gatewayUser", "nepi")
        self.ec.set(node1, "gateway", "bastion.test.iminds.be")

        node2 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node2, "host", "zotacM20")
        self.ec.set(node2, "slicename", self.slicename)
        self.ec.set(node2, "sfauser", self.sfauser)
        self.ec.set(node2, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node2, "gatewayUser", "nepi")
        self.ec.set(node2, "gateway", "bastion.test.iminds.be")

        self.ec.deploy()
        self.ec.wait_deployed([node1, node2])
        state1 = self.ec.state(node1)
        state2 = self.ec.state(node2)
        if not self.ec.abort:
            self.assertIn(state1, (3, 4))
            self.assertIn(state2, (3, 4))

        wnode_rm = self.ec.get_resource(node1)
        wnode_rm.sfaapi._reserved = set()
        wnode_rm.sfaapi._blacklist = set()

        self.ec.shutdown()

    @skipIfNotSfi
    def test_xdeploy3(self):
        """
        Test deploy 2 nodes, already in the slice.
        """
        node1 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node1, "host", "zotacM20")
        self.ec.set(node1, "slicename", self.slicename)
        self.ec.set(node1, "sfauser", self.sfauser)
        self.ec.set(node1, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node1, "gatewayUser", "nepi")
        self.ec.set(node1, "gateway", "bastion.test.iminds.be")

        node2 = self.ec.register_resource("WilabtSfaNode")
        self.ec.set(node2, "host", "zotacE3")
        self.ec.set(node2, "slicename", self.slicename)
        self.ec.set(node2, "sfauser", self.sfauser)
        self.ec.set(node2, "sfaPrivateKey", self.sfaPrivateKey)
        self.ec.set(node2, "gatewayUser", "nepi")
        self.ec.set(node2, "gateway", "bastion.test.iminds.be")

        self.ec.deploy()
        self.ec.wait_deployed([node1, node2])
        state1 = self.ec.state(node1)
        state2 = self.ec.state(node2)
        if not self.ec.abort:
            self.assertEquals(state1, (3, 4))
            self.assertEquals(state2, (3, 4))

        self.ec.shutdown() 

    def tearDown(self):
        pass
        #self.ec.shutdown()


if __name__ == '__main__':
    unittest.main()



