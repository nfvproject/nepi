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

class OMFVLCWrongCaseAllCritical(unittest.TestCase):

    id = 1000

    def setUp(self):
        self.ec = ExperimentController(exp_id = str(OMFVLCWrongCaseAllCritical.id))
        OMFVLCWrongCaseAllCritical.id += 1

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

        self.app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app1, 'appid', 'Vlc#1')
        self.ec.set(self.app1, 'command', "/opt/vlc-1.1.13/cvlc /opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.ec.set(self.app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
        self.ec.set(self.app1, 'version', "5")

        self.ec.register_connection(self.app1, self.node1)
        self.ec.register_connection(self.node1, self.iface1)

    def test_deploy_wo_node(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.37/24")
        self.ec.set(self.iface2, 'version', "5")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "2s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_wo_hostname(self):

        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.37/24")
        self.ec.set(self.iface2, 'version', "5")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "2s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_wo_iface(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'version', "5")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "2s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_wo_ip(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'version', "5")

        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "2s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_wo_channel(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'version', "5")

        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "2s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_wo_app(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")   
        self.ec.set(self.iface2, 'ip', "10.0.0.37/24")
        self.ec.set(self.iface2, 'version', "5")

        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.app2, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "2s")
        self.ec.register_condition([self.app1, self.app2], ResourceAction.STOP, self.app1, ResourceState.STARTED , "4s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2])

        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.RELEASED)

    def test_deploy_wo_app_path(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")
        self.ec.set(self.node2, 'version', "5")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")   
        self.ec.set(self.iface2, 'ip', "10.0.0.37/24")
        self.ec.set(self.iface2, 'version', "5")

        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppUser', "nepi")
        self.ec.set(self.channel, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        self.ec.set(self.channel, 'version', "5")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, 'appid', 'Vlc#2')
        self.ec.set(self.app2, 'version', "5")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.app2, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "2s")
        self.ec.register_condition([self.app1, self.app2], ResourceAction.STOP, self.app1, ResourceState.STARTED , "4s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2])

        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.RELEASED)


if __name__ == '__main__':
    unittest.main()



