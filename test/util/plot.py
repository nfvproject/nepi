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


from nepi.design.box import Box 
from nepi.util.plot import Plotter

import subprocess
import unittest

class BoxPlotTestCase(unittest.TestCase):
    def xtest_plot(self):
        """ XXX: This test is interactive, it will open an evince instance,
        so it should not run automatically """
        node1 = Box(label="node1")
        ping1 = Box(label="ping")
        mobility1 = Box(label="mob1")
        node2 = Box(label="node2")
        mobility2 = Box(label="mob2")
        iface1 = Box(label="iface1")
        iface2 = Box(label="iface2")
        channel = Box(label="chan")

        node1.connect(ping1)
        node1.connect(mobility1)
        node1.connect(iface1)
        channel.connect(iface1)
        channel.connect(iface2)
        node2.connect(iface2)
        node2.connect(mobility2)

        plotter = Plotter(node1)
        fname = plotter.plot()
        subprocess.call(["dot", "-Tps", fname, "-o", "%s.ps"%fname])
        subprocess.call(["evince","%s.ps"%fname])
       
if __name__ == '__main__':
    unittest.main()

