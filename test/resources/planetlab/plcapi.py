"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

#!/usr/bin/env python
from nepi.resources.planetlab.plcapi import PLCAPIFactory
from nepi.util.sshfuncs import RUNNING, FINISHED

import os
import unittest

class PlanetlabAPITestCase(unittest.TestCase):
    def setUp(self):
        self.slicename = 'inria_nepi'
        self.host1 = 'nepi2.pl.sophia.inria.fr'
        self.host2 = 'nepi5.pl.sophia.inria.fr'


    def test_list_hosts(self):
        slicename = os.environ.get('PL_USER')
        pl_pass = os.environ.get('PL_PASS')
        pl_url = "nepiplc.pl.sophia.inria.fr"

        plapi =  PLCAPIFactory.get_api(slicename, pl_pass, pl_url)

        plapi.test()

        nodes = plapi.get_nodes()
        self.assertTrue(len(nodes)>0)


if __name__ == '__main__':
    unittest.main()

