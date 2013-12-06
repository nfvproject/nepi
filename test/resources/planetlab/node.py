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

from nepi.resources.planetlab.node import PlanetlabNode
from nepi.resources.planetlab.plcapi import PLCAPI, PLCAPIFactory

from test_utils import skipIfNotPLCredentials

import os
import time
import unittest
import multiprocessing

class DummyEC(ExperimentController):
    pass

def create_node(ec, username, pl_user=None, pl_password=None, pl_url=None, 
                hostname=None, country=None, operatingSystem=None, 
                minBandwidth=None, minCpu=None,
                architecture=None, city=None):

    node = ec.register_resource("PlanetlabNode")

    if username:
        ec.set(node, "username", username)
    if pl_user:
        ec.set(node, "pluser", pl_user)
    if pl_password:
        ec.set(node, "plpassword", pl_password)
    if pl_url:
        ec.set(node, "plcApiUrl", pl_url)
    
    if hostname:
        ec.set(node, "hostname", hostname)
    if country:
        ec.set(node, "country", country)
    if operatingSystem:
        ec.set(node, "operatingSystem", operatingSystem)
    if minBandwidth:
        iec.set(node, "minBandwidth", minBandwidth)
    if minCpu:
        ec.set(node, "minCpu", minCpu)
    if architecture:
        ec.set(node, "architecture", architecture)
    if city:
        ec.set(node, "city", city)

    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    
    return node

class PLNodeFactoryTestCase(unittest.TestCase):

    def test_creation_phase(self):
        self.assertEquals(PlanetlabNode._rtype, "PlanetlabNode")
        self.assertEquals(len(PlanetlabNode._attributes), 30)

class PLNodeTestCase(unittest.TestCase):
    """
    This tests use inria_nepi slice, and  already added to
    the slice, and ONLY this one in order for the test not to fail.
    """

    def setUp(self):
        self.ec = DummyEC()
        self.username = 'inria_nepi'
        self.pl_user = os.environ.get("PL_USER")
        self.pl_password = os.environ.get("PL_PASS")
        self.pl_url = "nepiplc.pl.sophia.inria.fr"

    @skipIfNotPLCredentials
    def test_plapi(self):
        """
        Check that the api to discover and reserve resources is well
        instanciated, and is an instance of PLCAPI. Ignore error while
        executing the ec.shutdown method, the error is due to the name
        of the host not being defined yet for this test.
        """
        node1 = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, 
            architecture="x86_64")

        plnode_rm1 = self.ec.get_resource(node1)
        hostname = plnode_rm1.get("hostname")
        self.assertIsNone(hostname)

        self.assertIsNone(plnode_rm1._node_to_provision)

        api1 = plnode_rm1.plapi
        self.assertIsInstance(api1, PLCAPI)
        self.assertEquals(len(api1.reserved()), 0)
        self.assertEquals(len(api1.blacklisted()), 0)

        node2 = create_node(self.ec, self.username, pl_user=self.pl_user,   
            pl_password=self.pl_password, pl_url=self.pl_url, 
            architecture="x86_64")
        
        plnode_rm2 = self.ec.get_resource(node2)
        api2 = plnode_rm2.plapi
        self.assertEquals(api1, api2)
    
        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm1._set_hostname_attr(3)
        plnode_rm2._set_hostname_attr(3)

    def test_no_plcredentials(self):
        """
        Check that if no PL credentials are set, the PlanetlabNode skip the 
        discover and provision for the node.
        """
        node = create_node(self.ec, self.username, hostname='nepi2.pl.sophia.inria.fr')
        plnode_rm = self.ec.get_resource(node)
        
        plnode_rm.do_discover()
        plnode_rm.do_provision()
        
        self.assertIsNone(plnode_rm._node_to_provision)

    @skipIfNotPLCredentials
    def test_discover_inslice(self):
        """
        This test uses the fact that the node nepi2.pl.sophia.inria.fr is already in 
        the slice and match the constraints OS Fedora12 and arch x86_64.
        Check nepi2.pl.sophia.inria.fr is alive if the test fails.
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, architecture="x86_64", 
            operatingSystem="f12")

        plnode_rm = self.ec.get_resource(node)
       
        hostname = plnode_rm.get("hostname")
        self.assertIsNone(hostname)

        api = plnode_rm.plapi
        api.add_slice_nodes(self.username, ['nepi2.pl.sophia.inria.fr'])        

        plnode_rm.do_discover()
        self.assertEquals(plnode_rm._node_to_provision, 3)

       # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm._set_hostname_attr(plnode_rm._node_to_provision)        

    @skipIfNotPLCredentials
    def test_discover_not_inslice(self):
        """
        This test checks that if the node is not in the slice, anyway the
        discover method picks one that match constraints outside from the
        slice.
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, country="France",
            operatingSystem="f12")

        plnode_rm = self.ec.get_resource(node)
        plnode_rm.do_discover()
    
        result = [4] 
        self.assertIn(plnode_rm._node_to_provision, result)     
        self.assertIsNot(plnode_rm.plapi.reserved(), set())

        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm._set_hostname_attr(plnode_rm._node_to_provision)        

    @skipIfNotPLCredentials
    def test_discover_hostname(self):
        """
        This test checks that if the user specify the hostname, only that node
        is discovered.
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, 
            hostname="nepi2.pl.sophia.inria.fr")

        plnode_rm = self.ec.get_resource(node)
        plnode_rm.do_discover()

        self.assertEquals(plnode_rm._node_to_provision, 3)
        self.assertEquals(plnode_rm.plapi.reserved(), set([3]))

    @skipIfNotPLCredentials
    def test_discover_with_ranges(self):
        """
        Checks that defining max or min attributes, the discover method works.
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, minCpu=50)

        plnode_rm = self.ec.get_resource(node)
        plnode_rm.do_discover()

        result = [6]
        self.assertIn(plnode_rm._node_to_provision, result)
        self.assertIsNot(plnode_rm.plapi.reserved(), set())

        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm._set_hostname_attr(plnode_rm._node_to_provision)        

    @skipIfNotPLCredentials        
    def test_blacklist_nodes(self):
        """
        Test that if the node is malfunctioning it gets blacklisted, the node
        nepi1.pl.sophia.inria.fr is used, if the test fails, check that the 
        result of the plcapi query is actually empty.
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
                pl_password=self.pl_password, pl_url=self.pl_url, 
                hostname="nepi1.pl.sophia.inria.fr")

        plnode_rm = self.ec.get_resource(node)
        self.assertEquals(plnode_rm.plapi.blacklisted(), set())

        # check that the node is actually malfunctioning
        api = plnode_rm.plapi
        filters = {'boot_state': 'boot', 'node_type': 'regular', 
            'hostname': 'nepi1.pl.sophia.inria.fr', 'run_level': 'boot',
            '>last_contact': int(time.time()) - 2*3600}
        node_id = api.get_nodes(filters, fields=['node_id'])

        if not node_id:
            with self.assertRaises(RuntimeError):
                plnode_rm.do_discover()
                self.assertEquals(plnode_rm.plapi.blacklisted(), set([1]))

    @skipIfNotPLCredentials
    def test_provision_node_inslice(self):
        """
        Check provision of the node nepi2.pl.sophia.inria.fr.
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, 
            architecture="x86_64", operatingSystem="f12")

        plnode_rm = self.ec.get_resource(node)
        self.assertEquals(len(plnode_rm.plapi.blacklisted()), 0)
        self.assertEquals(len(plnode_rm.plapi.reserved()), 0)

        api = plnode_rm.plapi
        api.add_slice_nodes(self.username, ['nepi2.pl.sophia.inria.fr'])

        plnode_rm.do_discover()
        plnode_rm.do_provision()
        ip = plnode_rm.get("ip")
        self.assertEquals(ip, "138.96.116.32")
        self.assertEquals(len(plnode_rm.plapi.reserved()), 1)

    @skipIfNotPLCredentials
    def test_provision_node_not_inslice(self):
        """
        Check provision of one of the nodes f12, nodes:
        'nepi3.pl.sophia.inria.fr'
        'nepi5.pl.sophia.inria.fr'
        """
        node = create_node(self.ec, self.username, pl_user=self.pl_user,
            pl_password=self.pl_password, pl_url=self.pl_url, operatingSystem="f12",
            city='Paris')

        plnode_rm = self.ec.get_resource(node)
        self.assertEquals(plnode_rm.plapi.blacklisted(), set())
        self.assertEquals(plnode_rm.plapi.reserved(), set())

        api = plnode_rm.plapi
        api.add_slice_nodes(self.username, ['nepi2.pl.sophia.inria.fr'])

        plnode_rm.do_discover()
        plnode_rm.do_provision()
        ip = plnode_rm.get("ip")       

        result = ["138.96.116.33","138.96.116.35"] 
        self.assertIn(ip, result)
       
#    @skipIfNotPLCredentials
#    def test_provision_more_than_available(self):
#        """
#        Check that if the user wants to provision 3 nodes in Paris, he
#        gets RuntimeError, there are only 2 nodes with city=Paris.
#        """
#        node1 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url, 
#            city="Paris", operatingSystem="f12")
#
#        plnode_rm1 = self.ec.get_resource(node1)
#
#        api = plnode_rm.plapi
#        api.add_slice_nodes(self.username, ['nepi2.pl.sophia.inria.fr'])
#
#        plnode_rm1.do_discover()
#        plnode_rm1.do_provision()
#
#        node2 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url, 
#            city="Paris", operatingSystem="f12")
#
#        plnode_rm2 = self.ec.get_resource(node2)
#        plnode_rm2.do_discover()
#        plnode_rm2.do_provision()
#
#        node3 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url, 
#            city="Paris", operatingSystem="f12")
#
#        plnode_rm3 = self.ec.get_resource(node3)
#        with self.assertRaises(RuntimeError):
#            plnode_rm3.do_discover()
#            with self.assertRaises(RuntimeError):
#                plnode_rm3.do_provision()
#        
#        host1 = plnode_rm1.get('hostname')
#
#        plnode_rm3._set_hostname_attr(host1)
#
#    @skipIfNotPLCredentials
#    def test_concurrence(self):
#        """
#        Test with the nodes being discover and provision at the same time.
#        It should fail as the test before.
#        """
#        node1 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url,
#            architecture="x86_64", operatingSystem="f12")
#
#        node2 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url,
#            architecture="x86_64", operatingSystem="f12")
#
#        node3 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url, 
#            architecture="x86_64", operatingSystem="f12")
#
#        node4 = create_node(self.ec, self.username, pl_user=self.pl_user,
#            pl_password=self.pl_password, pl_url=self.pl_url, 
#            architecture="x86_64", operatingSystem="f12")
#
#        self.ec.deploy()
#        self.ec.wait_finished([node1, node2, node3, node4])
#        state = self.ec.state(node1, hr=True)
#        self.assertIn(state, ['READY', 'FAILED'])
#        state = self.ec.state(node2, hr=True)
#        self.assertIn(state, ['READY', 'FAILED'])
#        state = self.ec.state(node3, hr=True)
#        self.assertIn(state, ['READY', 'FAILED'])
#        state = self.ec.state(node4, hr=True)
#        self.assertIn(state, ['READY', 'FAILED'])

    def tearDown(self):
        commonapi=PLCAPIFactory.get_api(self.pl_user, self.pl_password,
            self.pl_url)
        #commonapi.add_slice_nodes(self.username, ['nepi2.pl.sophia.inria.fr'])
        commonapi._reserved = set()
        commonapi._blacklist = set()
             
        self.ec.shutdown()


if __name__ == '__main__':
    unittest.main()



