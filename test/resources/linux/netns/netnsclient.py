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

from nepi.resources.netns.netnsserver import run_server
from nepi.resources.linux.netns.netnsclient import LinuxNetNSClient

from test_utils import skipIf

import os
import threading
import time
import unittest

class DummyEmulation(object):
    def __init__(self, socket_name):
        self.socket_name = socket_name
        self.node = dict({'hostname': 'localhost'})

    @property
    def remote_socket(self):
        return self.socket_name

class LinuxNetNSClientTest(unittest.TestCase):
    def setUp(self):
        self.socket_name = os.path.join("/", "tmp", "NetNSWrapperServer.sock")
        if os.path.exists(self.socket_name):
            os.remove(self.socket_name) 

    def tearDown(self):
        os.remove(self.socket_name) 

    @skipIf(os.getuid() != 0, "Test requires root privileges")
    def test_run_ping_routing(self):
        thread = threading.Thread(target = run_server,
                args = [self.socket_name])

        thread.setDaemon(True)
        thread.start()

        time.sleep(3)

        # Verify that the communication socket was created
        self.assertTrue(os.path.exists(self.socket_name))

        # Create a dummy simulation object
        emulation = DummyEmulation(self.socket_name) 

        # Instantiate the NS3 client
        client = LinuxNetNSClient(emulation)

        ### create 3 nodes
        #n1 = netns.Node()
        #n2 = netns.Node()
        #n3 = netns.Node()
        n1 = client.create("Node")
        n2 = client.create("Node")
        n3 = client.create("Node")

        ### add interfaces to nodes
        #i1 = n1.add_if()
        #i2a = n2.add_if()
        #i2b = n2.add_if()
        #i3 = n3.add_if()
        i1 = client.invoke(n1, "add_if")
        i2a = client.invoke(n2, "add_if")
        i2b = client.invoke(n2, "add_if")
        i3 = client.invoke(n3, "add_if")

        ### set interfaces up
        # i1.up = i2a.up = i2b.up = i3.up = True
        client.set(i1, "up", True)
        client.set(i2a, "up", True)
        client.set(i2b, "up", True)
        client.set(i3, "up", True)

        ### create 2 switches
        #l1 = netns.Switch()
        #l2 = netns.Switch()
        l1 = client.create("Switch")
        l2 = client.create("Switch")

        ### connect interfaces to switches
        #l1.connect(i1)
        #l1.connect(i2a)
        #l2.connect(i2b)
        #l2.connect(i3)
        client.invoke(l1, "connect", i1)
        client.invoke(l1, "connect", i2a)
        client.invoke(l2, "connect", i2b)
        client.invoke(l2, "connect", i3)

        ### set switched up
        # l1.up = l2.up = True
        client.set(l1, "up", True)
        client.set(l2, "up", True)

        ## add ip addresses to interfaces
        #i1.add_v4_address('10.0.0.1', 24)
        #i2a.add_v4_address('10.0.0.2', 24)
        #i2b.add_v4_address('10.0.1.1', 24)
        #i3.add_v4_address('10.0.1.2', 24)
        client.invoke(i1, "add_v4_address", "10.0.0.1", 24)
        client.invoke(i2a, "add_v4_address", "10.0.0.2", 24)
        client.invoke(i2b, "add_v4_address", "10.0.1.1", 24)
        client.invoke(i3, "add_v4_address", "10.0.1.2", 24)

        ## add routes to nodes
        #n1.add_route(prefix = '10.0.1.0', prefix_len = 24,
        #        nexthop = '10.0.0.2')
        #n3.add_route(prefix = '10.0.0.0', prefix_len = 24,
        #        nexthop = '10.0.1.1')
        client.invoke(n1, "add_route", prefix = "10.0.1.0", prefix_len = 24,
                nexthop = "10.0.0.2")
        client.invoke(n3, "add_route", prefix = "10.0.0.0", prefix_len = 24,
                nexthop = "10.0.1.1")

        ## launch pings
        #a1 = n1.Popen(['ping', '-qc1', '10.0.1.2'], stdout = null)
        #a2 = n3.Popen(['ping', '-qc1', '10.0.0.1'], stdout = null)
        path1 = "/tmp/netns_file1"
        path2 = "/tmp/netns_file2"
        file1 = client.create("open", path1, "w")
        file2 = client.create("open", path2, "w")
        a1 = client.invoke(n1, "Popen", ["ping", "-qc1", "10.0.1.2"], stdout = file1)
        a2 = client.invoke(n3, "Popen", ["ping", "-qc1", "10.0.0.1"], stdout = file2)

        ## get ping status
        p1 = None
        p2 = None
        while p1 is None or p2 is None:
            p1 = client.invoke(a1, "poll")
            p2 = client.invoke(a2, "poll")

        stdout1 = open(path1, "r")
        stdout2 = open(path2, "r")

        s1 = stdout1.read()
        s2 = stdout2.read()

        print s1, s2

        expected = "1 packets transmitted, 1 received, 0% packet loss"
        self.assertTrue(s1.find(expected) > -1)
        self.assertTrue(s2.find(expected) > -1)

        # wait until emulation is over
        client.shutdown()

if __name__ == '__main__':
    unittest.main()

