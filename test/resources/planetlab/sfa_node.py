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

from nepi.resources.planetlab.sfa_node import PlanetlabSfaNode
from nepi.util.sfaapi import SFAAPI, SFAAPIFactory

from test_utils import skipIfNotSfaCredentials

import os
import time
import unittest
import multiprocessing


class DummyEC(ExperimentController):
    pass

class PLSfaNodeFactoryTestCase(unittest.TestCase):

    def test_creation_phase(self):
        self.assertEquals(PlanetlabSfaNode._rtype, "PlanetlabSfaNode")
        self.assertEquals(len(PlanetlabSfaNode._attributes), 29)

class PLSfaNodeTestCase(unittest.TestCase):
    """
    This tests use inria_nepi slice, from the test instance of MyPLC
    nepiplc.pl.sophia.inria.fr. This test can fail if the user running
    the test does not have a user in this instance of MyPLC or is not
    added to the inria_nepi slice.
    """

    def setUp(self):
        self.ec = DummyEC()
        self.username = os.environ.get('SFA_SLICE')
        self.sfauser = os.environ.get('SFA_USER')
        self.sfaPrivateKey = os.environ.get('SFA_PK')
        
    @skipIfNotSfaCredentials
    def test_a_sfaapi(self):
        """
        Check that the api to discover and reserve resources is well
        instanciated, and is an instance of SFAAPI. Check that using
        the same credentials, the same object of the api is used.
        """
        node1 = self.ec.register_resource("PlanetlabSfaNode")
        self.ec.set(node1, "hostname", "planetlab2.ionio.gr")
        self.ec.set(node1, "username", self.username)
        self.ec.set(node1, "sfauser", self.sfauser)
        self.ec.set(node1, "sfaPrivateKey", self.sfaPrivateKey)

        plnode_rm1 = self.ec.get_resource(node1)

        self.assertIsNone(plnode_rm1._node_to_provision)

        api1 = plnode_rm1.sfaapi
        self.assertIsInstance(api1, SFAAPI)
        self.assertEquals(len(api1.reserved()), 0)
        self.assertEquals(len(api1.blacklisted()), 0)

        node2 = self.ec.register_resource("PlanetlabSfaNode")
        self.ec.set(node2, "hostname", "planetlab2.ionio.gr")
        self.ec.set(node2, "username", self.username)
        self.ec.set(node2, "sfauser", self.sfauser)
        self.ec.set(node2, "sfaPrivateKey", self.sfaPrivateKey)

        plnode_rm2 = self.ec.get_resource(node2)
        api2 = plnode_rm2.sfaapi
        self.assertEquals(api1, api2)
    
    @skipIfNotSfaCredentials
    def test_discover(self):
        """
        Check that the method do_discover reserve the right node.
        """
        node = self.ec.register_resource("PlanetlabSfaNode")
        self.ec.set(node, "hostname", "planetlab2.ionio.gr")
        self.ec.set(node, "username", self.username)
        self.ec.set(node, "sfauser", self.sfauser)
        self.ec.set(node, "sfaPrivateKey", self.sfaPrivateKey)

        plnode_rm = self.ec.get_resource(node)
       
        hostname = plnode_rm.get("hostname")
        self.assertIsNotNone(hostname)

        self.assertEquals(plnode_rm.sfaapi.reserved(), set())

        plnode_rm.do_discover()
        self.assertEquals(plnode_rm.sfaapi.reserved().pop(), 'ple.dbislab.planetlab2.ionio.gr')
        self.assertEquals(plnode_rm._node_to_provision, 'ple.dbislab.planetlab2.ionio.gr')

    @skipIfNotSfaCredentials
    def test_provision(self):
        """
        This test checks that the method do_provision add the node in the slice and check
        its well functioning.
        """
        node = self.ec.register_resource("PlanetlabSfaNode")
        self.ec.set(node, "hostname", "planetlab2.ionio.gr")
        self.ec.set(node, "username", self.username)
        self.ec.set(node, "sfauser", self.sfauser)
        self.ec.set(node, "sfaPrivateKey", self.sfaPrivateKey)

        plnode_rm = self.ec.get_resource(node)

        self.assertEquals(plnode_rm.sfaapi.reserved(), set())
        self.assertIsNone(plnode_rm._node_to_provision)

        slicename = 'ple.' + self.username.replace('_', '.')

        plnode_rm.do_discover()
        plnode_rm.do_provision()    

        cmd = 'echo "IT WORKED"'
        ((out, err), proc) = plnode_rm.execute(cmd)
        self.assertEquals(out.strip(), "IT WORKED")

        urn_to_delete = 'urn:publicid:IDN+ple:dbislab+node+planetlab2.ionio.gr'
        plnode_rm.sfaapi.remove_resource_from_slice(slicename, urn_to_delete)

        slice_resources = plnode_rm.sfaapi.get_slice_resources(slicename)['resource']
        if slice_resources:
            slice_resources_hrn = plnode_rm.sfaapi.get_resources_hrn(slice_resources)
            self.assertNotIn('planetlab2.ionio.gr', slice_resources_hrn.keys())           

    @skipIfNotSfaCredentials
    def test_xdeploy(self):
        """
        Test with the nodes being discover and provision at the same time.
        The deploy should fail as the test before, there aren't 4 nodes of 
        that carachteristics.
        """
        node = self.ec.register_resource("PlanetlabSfaNode")
        self.ec.set(node, "hostname", "planetlab2.ionio.gr")
        self.ec.set(node, "username", self.username)
        self.ec.set(node, "sfauser", self.sfauser)
        self.ec.set(node, "sfaPrivateKey", self.sfaPrivateKey)

        self.ec.deploy()
        self.ec.wait_deployed(node)
        state = self.ec.state(node)
        self.assertEquals(state, 3)

    def tearDown(self):
        self.ec.shutdown()


if __name__ == '__main__':
    unittest.main()



