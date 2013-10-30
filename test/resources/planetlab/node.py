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

import os
import time
import unittest
import multiprocessing

def create_node(ec, username, pl_user, pl_password, hostname = None, 
        country = None, operatingSystem = None, minBandwidth = None, 
        minCpu = None):

    node = ec.register_resource("PlanetlabNode")

    if username:
        ec.set(node, "username", username)
    if pl_user:
        ec.set(node, "pluser", pl_user)
    if pl_password:
        ec.set(node, "plpassword", pl_password)

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

    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    
    return node

class PLNodeFactoryTestCase(unittest.TestCase):
    def test_creation_phase(self):
        self.assertEquals(PlanetlabNode.rtype(), "PlanetlabNode")
        self.assertEquals(len(PlanetlabNode._attributes), 29)


class PLNodeTestCase(unittest.TestCase):
    """
    This tests use inria_sfatest slice, and planetlab2.utt.fr already added to
    the slice, and ONLY this one in order for the test not to fail.
    """

    def setUp(self):
        self.ec = ExperimentController()
        self.username = "inria_sfatest"
        self.pl_user = os.environ.get("PL_USER")
        self.pl_password = os.environ.get("PL_PASS")
        self.pl_url = "www.planet-lab.eu"
        self.pl_ptn = "https://%(hostname)s:443/PLCAPI/"

    def test_plapi(self):
        """
        Check that the api to discover and reserve resources is well
        instanciated, and is an instance of PLCAPI. Ignore error while
        executing the ec.shutdown method, the error is due to the name
        of the host not being defined yet for this test.
       """
        node1 = create_node(self.ec, self.username, self.pl_user, 
            self.pl_password, country="France")

        plnode_rm1 = self.ec.get_resource(node1)
        hostname = plnode_rm1.get("hostname")
        self.assertIsNone(hostname)

        self.assertIsNone(plnode_rm1._node_to_provision)

        api1 = plnode_rm1.plapi
        self.assertIsInstance(api1, PLCAPI)
        self.assertEquals(len(api1.reserved()), 0)
        self.assertEquals(len(api1.blacklisted()), 0)

        node2 = create_node(self.ec, self.username, self.pl_user,   
            self.pl_password, country="France")
        
        plnode_rm2 = self.ec.get_resource(node2)
        api2 = plnode_rm2.plapi
        self.assertEquals(api1, api2)

        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm1._set_hostname_attr(7057)
        plnode_rm2._set_hostname_attr(7057)

    def test_discover_inslice(self):
        """
        This test uses the fact that the node planetlab2.utt.fr is already in 
        the slice and match the constraints OS Fedora12 and country France.
        Check planetlab2.utt.fr is alive if the test fails.
        """
        node = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f12")

        plnode_rm = self.ec.get_resource(node)
        
        hostname = plnode_rm.get("hostname")
        self.assertIsNone(hostname)

        plnode_rm.discover()
        self.assertEquals(plnode_rm._node_to_provision, 7057)

        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm._set_hostname_attr(plnode_rm._node_to_provision)        

    def test_discover_not_inslice(self):
        """
        This test checks that if the node is not in the slice, anyway the
        discover method picks one that match constraints outside from the
        slice.
        """
        node = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        plnode_rm = self.ec.get_resource(node)
        plnode_rm.discover()
    
        result = [14281, 1034, 7035] # nodes matching f14 and France
        self.assertIn(plnode_rm._node_to_provision, result)     
        self.assertIsNot(plnode_rm.plapi.reserved(), set())

        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm._set_hostname_attr(plnode_rm._node_to_provision)        

    def test_discover_hostname(self):
        """
        This test checks that if the user specify the hostname, only that node
        is discovered.
        """
        node = create_node(self.ec, self.username, self.pl_user,
                self.pl_password, hostname="planetlab1.sics.se")

        plnode_rm = self.ec.get_resource(node)
        plnode_rm.discover()

        self.assertEquals(plnode_rm._node_to_provision, 14871)
        self.assertEquals(plnode_rm.plapi.reserved(), set([14871]))

    def test_discover_with_ranges(self):
        """
        Checks that defining max or min attributes, the discover method works.
        """
        node = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, minCpu=50) #minBandwidth=500)

        plnode_rm = self.ec.get_resource(node)
        plnode_rm.discover()

        #result = [15815, 15814, 425, 417, 1054, 1102, 1107, 505, 1031] 
        result = [425, 15815, 15814, 14842, 427, 41, 14466]
        self.assertIn(plnode_rm._node_to_provision, result)
        self.assertIsNot(plnode_rm.plapi.reserved(), set())

        # Set hostname attribute in order for the shutdown method not to fail
        plnode_rm._set_hostname_attr(plnode_rm._node_to_provision)        
        
    def test_blacklist_nodes(self):
        """
        Test that if the node is malfunctioning it gets blacklisted, the node
        planetlab-1a.ics.uci.edu is used, if the test fails, check that the 
        result of the plcapi query is actually empty.
        """
        node = create_node(self.ec, self.username, self.pl_user,
                self.pl_password, hostname="planetlab-1a.ics.uci.edu")

        plnode_rm = self.ec.get_resource(node)
        self.assertEquals(plnode_rm.plapi.blacklisted(), set())

        # check that the node is actually malfunctioning
        api = plnode_rm.plapi
        filters = {'boot_state': 'boot', '>last_contact': 1378299413, 
            'node_type': 'regular', 'hostname': 'planetlab-1a.ics.uci.edu', 
            'run_level': 'boot'}
        node_id = api.get_nodes(filters, fields=['node_id'])

        if not node_id:
            with self.assertRaises(RuntimeError):
                plnode_rm.discover()
                self.assertEquals(plnode_rm.plapi.blacklisted(), set([14871]))

    def test_provision_node_inslice(self):
        """
        Check provision of the node planetlab2.utt.fr.
        """
        node = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f12")

        plnode_rm = self.ec.get_resource(node)
        self.assertEquals(len(plnode_rm.plapi.blacklisted()), 0)
        self.assertEquals(len(plnode_rm.plapi.reserved()), 0)

        plnode_rm.discover()
        plnode_rm.provision()
        ip = plnode_rm.get("ip")
        self.assertEquals(ip, "194.254.215.12")
        self.assertEquals(len(plnode_rm.plapi.reserved()), 1)

    def test_provision_node_not_inslice(self):
        """
        Check provision of one of the nodes f14 France, nodes:
        node1pl.planet-lab.telecom-lille1.eu
        ple5.ipv6.lip6.fr
        node2pl.planet-lab.telecom-lille1.eu
        """
        node = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        plnode_rm = self.ec.get_resource(node)
        self.assertEquals(plnode_rm.plapi.blacklisted(), set())
        self.assertEquals(plnode_rm.plapi.reserved(), set())

        plnode_rm.discover()
        plnode_rm.provision()
        ip = plnode_rm.get("ip")       

        result = ["194.167.254.18","132.227.62.123","194.167.254.19"] 
        self.assertIn(ip, result)

    def test_provision_more_than_available(self):
        """
        Check that if the user wants to provision 4 nodes with fedora 14, he
        gets RuntimeError, there are only 3 nodes f14.
        """
        node1 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        plnode_rm1 = self.ec.get_resource(node1)
        plnode_rm1.discover()
        plnode_rm1.provision()

        node2 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        plnode_rm2 = self.ec.get_resource(node2)
        plnode_rm2.discover()
        plnode_rm2.provision()

        node3 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        plnode_rm3 = self.ec.get_resource(node3)
        with self.assertRaises(RuntimeError):
            plnode_rm3.discover()
            with self.assertRaises(RuntimeError):
                plnode_rm3.provision()
        
        node4 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        plnode_rm4 = self.ec.get_resource(node4)
        with self.assertRaises(RuntimeError):
            plnode_rm4.discover()

        host1 = plnode_rm1.get('hostname')

        plnode_rm3._set_hostname_attr(host1)
        plnode_rm4._set_hostname_attr(host1)

    def test_concurrence(self):
        """
        Test with the nodes being discover and provision at the same time.
        """
        node1 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        node2 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        node3 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        node4 = create_node(self.ec, self.username, self.pl_user,
            self.pl_password, country="France", operatingSystem="f14")

        self.ec.deploy()
        self.ec.wait_finished([node1, node2, node3, node4])
        state = self.ec.ecstate
        self.assertEquals(state, 2)

    def tearDown(self):
        commonapi=PLCAPIFactory.get_api(self.pl_user, self.pl_password,
            self.pl_url, self.pl_ptn)
        commonapi._reserved = set()
        commonapi._blacklist = set()
        self.ec.shutdown()


if __name__ == '__main__':
    unittest.main()



