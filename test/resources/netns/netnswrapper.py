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


# Test based on netns test/test_core.py file test_run_ping_routing test
#

from nepi.resources.netns.netnswrapper import NetNSWrapper

from test_utils import skipIf

import os
import subprocess
import sys
import time
import unittest

class NetNSWrapperTest(unittest.TestCase):
    def setUp(self):
        pass

    @skipIf(os.getuid() != 0, "Test requires root privileges")
    def test_run_ping_routing(self):
        wrapper = NetNSWrapper()

        ### create 3 nodes
        #n1 = netns.Node()
        #n2 = netns.Node()
        #n3 = netns.Node()
        n1 = wrapper.create("Node")
        n2 = wrapper.create("Node")
        n3 = wrapper.create("Node")

        ### add interfaces to nodes
        #i1 = n1.add_if()
        #i2a = n2.add_if()
        #i2b = n2.add_if()
        #i3 = n3.add_if()
        i1 = wrapper.invoke(n1, "add_if")
        i2a = wrapper.invoke(n2, "add_if")
        i2b = wrapper.invoke(n2, "add_if")
        i3 = wrapper.invoke(n3, "add_if")

        ### set interfaces up
        # i1.up = i2a.up = i2b.up = i3.up = True
        wrapper.set(i1, "up", True)
        wrapper.set(i2a, "up", True)
        wrapper.set(i2b, "up", True)
        wrapper.set(i3, "up", True)

        ### create 2 switches
        #l1 = netns.Switch()
        #l2 = netns.Switch()
        l1 = wrapper.create("Switch")
        l2 = wrapper.create("Switch")

        ### connect interfaces to switches
        #l1.connect(i1)
        #l1.connect(i2a)
        #l2.connect(i2b)
        #l2.connect(i3)
        wrapper.invoke(l1, "connect", i1)
        wrapper.invoke(l1, "connect", i2a)
        wrapper.invoke(l2, "connect", i2b)
        wrapper.invoke(l2, "connect", i3)

        ### set switched up
        # l1.up = l2.up = True
        wrapper.set(l1, "up", True)
        wrapper.set(l2, "up", True)

        ## add ip addresses to interfaces
        #i1.add_v4_address('10.0.0.1', 24)
        #i2a.add_v4_address('10.0.0.2', 24)
        #i2b.add_v4_address('10.0.1.1', 24)
        #i3.add_v4_address('10.0.1.2', 24)
        wrapper.invoke(i1, "add_v4_address", "10.0.0.1", 24)
        wrapper.invoke(i2a, "add_v4_address", "10.0.0.2", 24)
        wrapper.invoke(i2b, "add_v4_address", "10.0.1.1", 24)
        wrapper.invoke(i3, "add_v4_address", "10.0.1.2", 24)

        ## add routes to nodes
        #n1.add_route(prefix = '10.0.1.0', prefix_len = 24,
        #        nexthop = '10.0.0.2')
        #n3.add_route(prefix = '10.0.0.0', prefix_len = 24,
        #        nexthop = '10.0.1.1')
        wrapper.invoke(n1, "add_route", prefix = "10.0.1.0", prefix_len = 24,
                nexthop = "10.0.0.2")
        wrapper.invoke(n3, "add_route", prefix = "10.0.0.0", prefix_len = 24,
                nexthop = "10.0.1.1")

        ## launch pings
        #a1 = n1.Popen(['ping', '-qc1', '10.0.1.2'], stdout = null)
        #a2 = n3.Popen(['ping', '-qc1', '10.0.0.1'], stdout = null)
        path1 = "/tmp/netns_file1"
        path2 = "/tmp/netns_file2"
        file1 = wrapper.create("open", path1, "w")
        file2 = wrapper.create("open", path2, "w")
        a1 = wrapper.invoke(n1, "Popen", ["ping", "-qc1", "10.0.1.2"], stdout = file1)
        a2 = wrapper.invoke(n3, "Popen", ["ping", "-qc1", "10.0.0.1"], stdout = file2)

        ## get ping status
        p1 = None
        p2 = None
        while p1 is None or p2 is None:
            p1 = wrapper.invoke(a1, "poll")
            p2 = wrapper.invoke(a2, "poll")

        stdout1 = open(path1, "r")
        stdout2 = open(path2, "r")

        s1 = stdout1.read()
        s2 = stdout2.read()

        expected = "1 packets transmitted, 1 received, 0% packet loss"
        self.assertTrue(s1.find(expected) > -1)
        self.assertTrue(s2.find(expected) > -1)
        
        wrapper.shutdown()

if __name__ == '__main__':
    unittest.main()

