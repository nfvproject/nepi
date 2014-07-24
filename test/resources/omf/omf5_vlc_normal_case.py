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

import time
import unittest

class OMFResourceFactoryTestCase(unittest.TestCase):
    def test_creation_phase(self):

        self.assertEquals(OMFNode.get_rtype(), "OMFNode")
        self.assertEquals(len(OMFNode._attributes), 8)

        self.assertEquals(OMFWifiInterface.get_rtype(), "OMFWifiInterface")
        self.assertEquals(len(OMFWifiInterface._attributes), 12)

        self.assertEquals(OMFChannel.get_rtype(), "OMFChannel")
        self.assertEquals(len(OMFChannel._attributes), 8)

        self.assertEquals(OMFApplication.get_rtype(), "OMFApplication")
        self.assertEquals(len(OMFApplication._attributes), 14)

class OMFEachTestCase(unittest.TestCase):
    def setUp(self):
        self.ec = ExperimentController(exp_id = "99999")

        self.node1 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node1, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node1, 'xmppUser', "nepi")
        self.ec.set(self.node1, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node1, 'xmppPort', "5222")
        self.ec.set(self.node1, 'xmppPassword', "1234")
        self.ec.set(self.node1, 'version', "5")
        
        self.iface1 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface1, 'name', "wlan0")
        self.ec.set(self.iface1, 'mode', "adhoc")
        self.ec.set(self.iface1, 'hw_mode', "g")
        self.ec.set(self.iface1, 'essid', "vlcexp")
        self.ec.set(self.iface1, 'ip', "10.0.0.17/24")
        self.ec.set(self.iface1, 'version', "5")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")
        
        self.app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app1, 'appid', 'Vlc#1')
        self.ec.set(self.app1, 'command', "/opt/vlc-1.1.13/cvlc /opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.ec.set(self.app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
        self.ec.set(self.app1, 'version', "5")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, 'version', "5")

        self.app3 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app3, 'version', "5")

        self.app4 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app4, 'version', "5")

        self.app5 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app5, 'version', "5")

        self.ec.register_connection(self.app1, self.node1)
        self.ec.register_connection(self.app2, self.node1)
        self.ec.register_connection(self.app3, self.node1)
        self.ec.register_connection(self.app4, self.node1)
        self.ec.register_connection(self.app5, self.node1)
        self.ec.register_connection(self.node1, self.iface1)
        self.ec.register_connection(self.iface1, self.channel)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "3s")
        self.ec.register_condition(self.app3, ResourceAction.START, self.app2, ResourceState.STARTED , "2s")
        self.ec.register_condition(self.app4, ResourceAction.START, self.app3, ResourceState.STARTED , "3s")
        self.ec.register_condition(self.app5, ResourceAction.START, [self.app3, self.app2], ResourceState.STARTED , "2s")
        self.ec.register_condition(self.app5, ResourceAction.START, self.app1, ResourceState.STARTED , "25s")

        self.ec.register_condition([self.app1, self.app2, self.app3,self.app4, self.app5], ResourceAction.STOP, self.app5, ResourceState.STARTED , "1s")

    def tearDown(self):
        self.ec.shutdown()

    def test_creation_and_configuration_node(self):
        self.assertEquals(self.ec.get(self.node1, 'hostname'), 'omf.plexus.wlab17')
        self.assertEquals(self.ec.get(self.node1, 'xmppUser'), 'nepi')
        self.assertEquals(self.ec.get(self.node1, 'xmppServer'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(self.node1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(self.node1, 'xmppPassword'), '1234')
        self.assertEquals(self.ec.get(self.node1, 'version'), '5')


    def test_creation_and_configuration_interface(self):
        self.assertEquals(self.ec.get(self.iface1, 'name'), 'wlan0')
        self.assertEquals(self.ec.get(self.iface1, 'mode'), 'adhoc')
        self.assertEquals(self.ec.get(self.iface1, 'hw_mode'), 'g')
        self.assertEquals(self.ec.get(self.iface1, 'essid'), 'vlcexp')
        self.assertEquals(self.ec.get(self.iface1, 'ip'), '10.0.0.17/24')
        self.assertEquals(self.ec.get(self.iface1, 'version'), '5')

    def test_creation_and_configuration_channel(self):
        self.assertEquals(self.ec.get(self.channel, 'channel'), '6')
        self.assertEquals(self.ec.get(self.channel, 'xmppUser'), 'nepi')
        self.assertEquals(self.ec.get(self.channel, 'xmppServer'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(self.channel, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(self.channel, 'xmppPassword'), '1234')
        self.assertEquals(self.ec.get(self.channel, 'version'), '5')


    def test_creation_and_configuration_application(self):
        self.assertEquals(self.ec.get(self.app1, 'appid'), 'Vlc#1')
        self.assertEquals(self.ec.get(self.app1, 'command'), "/opt/vlc-1.1.13/cvlc /opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.assertEquals(self.ec.get(self.app1, 'env'), 'DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority')
        self.assertEquals(self.ec.get(self.app1, 'version'), '5')

    def test_connection(self):
        self.assertEquals(len(self.ec.get_resource(self.node1).connections), 6)
        self.assertEquals(len(self.ec.get_resource(self.iface1).connections), 2)
        self.assertEquals(len(self.ec.get_resource(self.channel).connections), 1)
        self.assertEquals(len(self.ec.get_resource(self.app1).connections), 1)
        self.assertEquals(len(self.ec.get_resource(self.app2).connections), 1)

    def test_condition(self):
        self.assertEquals(len(self.ec.get_resource(self.app1).conditions[ResourceAction.STOP]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app2).conditions[ResourceAction.START]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app3).conditions[ResourceAction.START]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app4).conditions[ResourceAction.STOP]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app5).conditions[ResourceAction.START]), 2)

class OMFVLCNormalCase(unittest.TestCase):
    def test_deploy(self):
        ec = ExperimentController(exp_id = "5421" )

        self.node1 = ec.register_resource("OMFNode")
        ec.set(self.node1, 'hostname', 'omf.plexus.wlab17')
        ec.set(self.node1, 'xmppUser', "nepi")
        ec.set(self.node1, 'xmppServer', "xmpp-plexus.onelab.eu")
        ec.set(self.node1, 'xmppPort', "5222")
        ec.set(self.node1, 'xmppPassword', "1234")
        ec.set(self.node1, 'version', "5")
        
        self.iface1 = ec.register_resource("OMFWifiInterface")
        ec.set(self.iface1, 'name', "wlan0")
        ec.set(self.iface1, 'mode', "adhoc")
        ec.set(self.iface1, 'hw_mode', "g")
        ec.set(self.iface1, 'essid', "vlcexp")
        ec.set(self.iface1, 'ip', "10.0.0.17/24")
        ec.set(self.iface1, 'version', "5")
        
        self.channel = ec.register_resource("OMFChannel")
        ec.set(self.channel, 'channel', "6")
        ec.set(self.channel, 'xmppUser', "nepi")
        ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        ec.set(self.channel, 'xmppPort', "5222")
        ec.set(self.channel, 'xmppPassword', "1234")
        ec.set(self.channel, 'version', "5")
        
        self.app1 = ec.register_resource("OMFApplication")
        ec.set(self.app1, 'appid', 'Vlc#1')
        ec.set(self.app1, 'command', "/opt/vlc-1.1.13/cvlc /opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        ec.set(self.app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
        ec.set(self.app1, 'version', "5")

        self.app2 = ec.register_resource("OMFApplication")
        ec.set(self.app2, 'appid', 'Test#1')
        ec.set(self.app2, 'command', "/usr/bin/test -1")
        ec.set(self.app2, 'env', " ")
        ec.set(self.app2, 'version', "5")

        self.app3 = ec.register_resource("OMFApplication")
        ec.set(self.app3, 'appid', 'Test#2')
        ec.set(self.app3, 'command', "/usr/bin/test -2")
        ec.set(self.app3, 'env', " ")
        ec.set(self.app3, 'version', "5")

        self.app4 = ec.register_resource("OMFApplication")
        ec.set(self.app4, 'appid', 'Test#3')
        ec.set(self.app4, 'command', "/usr/bin/test -3")
        ec.set(self.app4, 'env', " ")
        ec.set(self.app4, 'version', "5")

        self.app5 = ec.register_resource("OMFApplication")
        ec.set(self.app5, 'appid', 'Kill#2')
        ec.set(self.app5, 'command', "/usr/bin/killall vlc")
        ec.set(self.app5, 'env', " ")
        ec.set(self.app5, 'version', "5")

        ec.register_connection(self.app1, self.node1)
        ec.register_connection(self.app2, self.node1)
        ec.register_connection(self.app3, self.node1)
        ec.register_connection(self.app4, self.node1)
        ec.register_connection(self.app5, self.node1)
        ec.register_connection(self.node1, self.iface1)
        ec.register_connection(self.iface1, self.channel)

        ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "3s")
        ec.register_condition(self.app3, ResourceAction.START, self.app2, ResourceState.STARTED , "2s")
        ec.register_condition(self.app4, ResourceAction.START, self.app3, ResourceState.STARTED , "3s")
        ec.register_condition(self.app5, ResourceAction.START, [self.app3, self.app2], ResourceState.STARTED , "2s")
        ec.register_condition(self.app5, ResourceAction.START, self.app1, ResourceState.STARTED , "25s")

        ec.register_condition([self.app1, self.app2, self.app3,self.app4, self.app5], ResourceAction.STOP, self.app5, ResourceState.STARTED , "1s")

        ec.deploy()

        ec.wait_finished([self.app1, self.app2, self.app3,self.app4, self.app5])

        self.assertEquals(round(tdiffsec(ec.get_resource(self.app2).start_time, ec.get_resource(self.app1).start_time),0), 3.0)
        self.assertEquals(round(tdiffsec(ec.get_resource(self.app3).start_time, ec.get_resource(self.app2).start_time),0), 2.0)
        self.assertEquals(round(tdiffsec(ec.get_resource(self.app4).start_time, ec.get_resource(self.app3).start_time),0), 3.0)
        self.assertEquals(round(tdiffsec(ec.get_resource(self.app5).start_time, ec.get_resource(self.app3).start_time),0), 20.0)
        self.assertEquals(round(tdiffsec(ec.get_resource(self.app5).start_time, ec.get_resource(self.app1).start_time),0), 25.0)

        self.assertEquals(ec.get_resource(self.node1).state, ResourceState.STARTED)
        self.assertEquals(ec.get_resource(self.iface1).state, ResourceState.STARTED)
        self.assertEquals(ec.get_resource(self.channel).state, ResourceState.STARTED)
        self.assertEquals(ec.get_resource(self.app1).state, ResourceState.STOPPED)
        self.assertEquals(ec.get_resource(self.app2).state, ResourceState.STOPPED)
        self.assertEquals(ec.get_resource(self.app3).state, ResourceState.STOPPED)
        self.assertEquals(ec.get_resource(self.app4).state, ResourceState.STOPPED)
        self.assertEquals(ec.get_resource(self.app5).state, ResourceState.STOPPED)

        ec.shutdown()

        self.assertEquals(ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.app2).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.app3).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.app4).state, ResourceState.RELEASED)
        self.assertEquals(ec.get_resource(self.app5).state, ResourceState.RELEASED)


if __name__ == '__main__':
    unittest.main()



