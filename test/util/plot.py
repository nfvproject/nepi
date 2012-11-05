#!/usr/bin/env python

from neco.design.box import Box 
from neco.util.plot import Plotter

import subprocess
import unittest

class BoxPlotTestCase(unittest.TestCase):
    def xtest_plot(self):
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

