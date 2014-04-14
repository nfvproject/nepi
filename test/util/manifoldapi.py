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

# NOTE: Manifold API can not be tested yet with OMF nodes because there
# no OMF platforms connected currently.

from nepi.util.manifoldapi import MANIFOLDAPIFactory
from nepi.util.manifoldapi import MANIFOLDAPI 

import unittest
from multiprocessing import Process

class MFAPIFactoryTestCase(unittest.TestCase):
    """
    Test for the Manifold API Factory. Check that the same instance is used
    when credentials match.
    """

    def test_factory(self):
        """
        Check that the same API instance is used when the credentials match.
        """
        username="lucia.guevgeozian_odizzio@inria.fr"
        password="demo"
        api1 = MANIFOLDAPIFactory.get_api(username, password)
        api2 = MANIFOLDAPIFactory.get_api(username, password)

        self.assertIsInstance(api1, MANIFOLDAPI)
        self.assertIsInstance(api2, MANIFOLDAPI)
        self.assertEquals(api1, api2)
        

class MANIFOLDAPITestCase(unittest.TestCase):

    def setUp(self):
        self.username="lucia.guevgeozian_odizzio@inria.fr"
        self.password="demo"
        self.slicename = "ple.inria.sfatest"
        self.api = MANIFOLDAPIFactory.get_api(self.username, self.password)

    def test_get_resource_info(self):
        """
        Check that the API retrieves the right set of info acoridng to the
        filters and fields defined.
        """

        filters = dict()
        filters['hostname'] = 'planetlab2.tlm.unavarra.es'

        r_info = self.api.get_resource_info(filters=filters)
        hostname = r_info[0]['hostname']
        self.assertEquals(hostname, 'planetlab2.tlm.unavarra.es')

        # query with 2 filters
        filters['network'] = 'ple'
                
        r_info = self.api.get_resource_info(filters=filters)
        hostname = r_info[0]['hostname']
        self.assertEquals(hostname, 'planetlab2.tlm.unavarra.es')

        # query with fields only, without filters
        fields = ['latitude','longitude']

        r_info = self.api.get_resource_info(fields=fields)
        value = r_info[10]
        self.assertEquals(value.keys(), fields)

        # query with 2 filters and 2 fields
        r_info = self.api.get_resource_info(filters, fields)
        value = r_info[0]
        result = {'latitude': '42.7993', 'longitude': '-1.63544'}
        self.assertEquals(value, result)

        # query with filters where the AND should be zero resources
        filters['network'] = 'omf'
        
        r_info = self.api.get_resource_info(filters, fields)
        self.assertEquals(r_info, [])

    def test_fail_if_invalid_field(self):
        """
        Check that the invalid field is not used for the query
        """
        filters = dict()
        filters['network'] = 'omf'
        filters['component_id'] = 'urn:publicid:IDN+omf:nitos+node+node001'
        fields = ['arch']

        r_info = self.api.get_resource_info(filters, fields)
        value = r_info[0]
        self.assertNotEqual(len(value), 1)
    
    def test_get_slice_resources(self):
        """
        Test that the API retrives the resources in the user's slice.
        The slice used is ple.inria.sfatest, change slice and nodes in order 
        for the test not to fail.
        """
        resources = self.api.get_slice_resources(self.slicename)
        
        result = ['urn:publicid:IDN+ple:lilleple+node+node2pl.planet-lab.telecom-lille1.eu', 
        'urn:publicid:IDN+ple:uttple+node+planetlab2.utt.fr', 
        'urn:publicid:IDN+ple:lilleple+node+node1pl.planet-lab.telecom-lille1.eu']
       
        self.assertEquals(resources, result)
    
    def test_update_resources_from_slice(self):
        """
        Test that the nodes are correctly added to the user's slice.
        Test that the nodes are correctly removed from the user's slice.
        """
        new_resource = 'urn:publicid:IDN+ple:unavarraple+node+planetlab2.tlm.unavarra.es'
        self.api.add_resource_to_slice(self.slicename, new_resource)

        resources = self.api.get_slice_resources(self.slicename)
        self.assertIn(new_resource, resources)

        resource_to_remove = 'urn:publicid:IDN+ple:unavarraple+node+planetlab2.tlm.unavarra.es'
        self.api.remove_resource_from_slice(self.slicename, resource_to_remove)

        resources = self.api.get_slice_resources(self.slicename)
        self.assertNotIn(resource_to_remove, resources)

    def test_concurrence(self):
        resources = ['urn:publicid:IDN+ple:itaveirople+node+planet2.servers.ua.pt',
            'urn:publicid:IDN+ple:quantavisple+node+marie.iet.unipi.it',
            'urn:publicid:IDN+ple:elteple+node+planet1.elte.hu',
            'urn:publicid:IDN+ple:inria+node+wlab39.pl.sophia.inria.fr',
            'urn:publicid:IDN+ple:poznanple+node+planetlab-2.man.poznan.pl',
            'urn:publicid:IDN+ple:tmsp+node+planetlab-node3.it-sudparis.eu',
            'urn:publicid:IDN+ple:colbudple+node+evghu6.colbud.hu',
            'urn:publicid:IDN+ple:erlangenple+node+planetlab1.informatik.uni-erlangen.de',
            'urn:publicid:IDN+ple:kitple+node+iraplab1.iralab.uni-karlsruhe.de',
            'urn:publicid:IDN+ple:polimiple+node+planetlab1.elet.polimi.it',
            'urn:publicid:IDN+ple:colbudple+node+evghu12.colbud.hu',
            'urn:publicid:IDN+ple:ccsr+node+pl2.ccsrfi.net',
            'urn:publicid:IDN+ple:modenaple+node+planetlab-1.ing.unimo.it',
            'urn:publicid:IDN+ple:cambridgeple+node+planetlab1.xeno.cl.cam.ac.uk',
            'urn:publicid:IDN+ple:lig+node+planetlab-1.imag.fr',
            'urn:publicid:IDN+ple:polslple+node+plab3.ple.silweb.pl',
            'urn:publicid:IDN+ple:uc3mple+node+planetlab1.uc3m.es',
            'urn:publicid:IDN+ple:colbudple+node+evghu4.colbud.hu',
            'urn:publicid:IDN+ple:hiitple+node+planetlab3.hiit.fi',
            'urn:publicid:IDN+ple:l3sple+node+planet1.l3s.uni-hannover.de',
            'urn:publicid:IDN+ple:colbudple+node+evghu5.colbud.hu',
            'urn:publicid:IDN+ple:dbislab+node+planetlab2.ionio.gr',
            'urn:publicid:IDN+ple:forthple+node+planetlab2.ics.forth.gr',
            'urn:publicid:IDN+ple:netmodeple+node+vicky.planetlab.ntua.gr',
            'urn:publicid:IDN+ple:colbudple+node+evghu1.colbud.hu',
            'urn:publicid:IDN+ple:cyprusple+node+planetlab-3.cs.ucy.ac.cy',
            'urn:publicid:IDN+ple:darmstadtple+node+host1.planetlab.informatik.tu-darmstadt.de',
            'urn:publicid:IDN+ple:cnetple+node+plab2.create-net.org',
            'urn:publicid:IDN+ple:unictple+node+gschembra3.diit.unict.it',
            'urn:publicid:IDN+ple:sevillaple+node+ait05.us.es']

        def add_resource(new_resource):
            self.api.add_resource_to_slice(self.slicename, new_resource)

        def runInParallel(fns):
            for fn in fns:
                p = Process(target=fn)
                p.start()
                p.join()

        funcs = list()
        for r in resources:
            funcs.append(add_resource(r))  

        runInParallel(funcs)

        slice_res = self.api.get_slice_resources(self.slicename)
        for r in resources:
            self.assertIn(r, slice_res)

        for r in resources:
            self.api.remove_resource_from_slice(self.slicename, r)
        
if __name__ == '__main__':
    unittest.main()



