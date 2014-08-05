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
# Author: Julien Tribino <julien.tribino@inria.fr>


from nepi.execution.resource import ResourceFactory, ResourceManager, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

from nepi.resources.omf.node import OMFNode
from nepi.resources.omf.application import OMFApplication
from nepi.resources.omf.interface import OMFWifiInterface
from nepi.resources.omf.channel import OMFChannel
from nepi.resources.omf.omf_api_factory import OMFAPIFactory

from nepi.util.timefuncs import *

import os
import time
import unittest

class OMFPingNormalCase(unittest.TestCase):
    def test_deploy(self):
        ec = ExperimentController(exp_id = "5421" )

        self.node1 = ec.register_resource("OMFNode")
        ec.set(self.node1, 'hostname', 'wlab12')
        ec.set(self.node1, 'xmppUser', "nepi")
        ec.set(self.node1, 'xmppServer', "xmpp-plexus.onelab.eu")
        ec.set(self.node1, 'xmppPort', "5222")
        ec.set(self.node1, 'xmppPassword', "1234")
        
        self.iface1 = ec.register_resource("OMFWifiInterface")
        ec.set(self.iface1, 'name', "wlan0")
        ec.set(self.iface1, 'mode', "adhoc")
        ec.set(self.iface1, 'hw_mode', "g")
        ec.set(self.iface1, 'essid', "vlcexp")
        ec.set(self.iface1, 'ip', "10.0.0.17/24")
        
        self.channel = ec.register_resource("OMFChannel")
        ec.set(self.channel, 'channel', "6")
        ec.set(self.channel, 'xmppUser', "nepi")
        ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        ec.set(self.channel, 'xmppPort', "5222")
        ec.set(self.channel, 'xmppPassword', "1234")
        
        self.app1 = ec.register_resource("OMFApplication")
        ec.set(self.app1, 'appid', 'Vlc#1')
        ec.set(self.app1, 'command', "ping -c5 10.0.0.17")

        ec.register_connection(self.app1, self.node1)
        ec.register_connection(self.node1, self.iface1)
        ec.register_connection(self.iface1, self.channel)

        ec.register_condition(self.app1, ResourceAction.STOP, self.app1, ResourceState.STARTED , "10s")

        ec.deploy()

        ec.wait_finished(self.app1)

        stdout_1 = ec.trace(self.app1, "stdout")
        stderr_1 = ec.trace(self.app1, "stderr")

        if stdout_1:
            f = open("app1_out.txt", "w")
            f.write(stdout_1)
            f.close()

        if stderr_1:
            f = open("app1_err.txt", "w")
            f.write(stderr_1)
            f.close()

        self.assertEquals(ec.get_resource(self.node1).state, ResourceState.STARTED)
        self.assertEquals(ec.get_resource(self.iface1).state, ResourceState.STARTED)
        self.assertEquals(ec.get_resource(self.channel).state, ResourceState.STARTED)
        self.assertEquals(ec.get_resource(self.app1).state, ResourceState.STOPPED)

        ec.shutdown()

        self.assertEquals(ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.app1).state, ResourceState.RELEASED)

        t = open("app1_out.txt", "r")
        l = t.readlines()
        self.assertEquals(l[0], "PING 10.0.0.17 (10.0.0.17) 56(84) bytes of data.\n")
        self.assertIn("5 packets transmitted, 5 received, 0% packet loss, time", l[-2])
        self.assertIn("rtt min/avg/max/mdev = ", l[-1])
        
        t.close()
        os.remove("app1_out.txt")
        


if __name__ == '__main__':
    unittest.main()



