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

class OMFVLCWrongCaseWithNonCritical(unittest.TestCase):

    id = 2000

    def setUp(self):
        self.ec = ExperimentController(exp_id = str(OMFVLCWrongCaseWithNonCritical.id))
        OMFVLCWrongCaseWithNonCritical.id += 1

        self.node1 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node1, 'hostname', 'wlab12')
        self.ec.set(self.node1, 'xmppUser', "nepi")
        self.ec.set(self.node1, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node1, 'xmppPort', "5222")
        self.ec.set(self.node1, 'xmppPassword', "1234")
        
        self.iface1 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface1, 'name', "wlan0")
        self.ec.set(self.iface1, 'mode', "adhoc")
        self.ec.set(self.iface1, 'hw_mode', "g")
        self.ec.set(self.iface1, 'essid', "vlcexp")
        self.ec.set(self.iface1, 'ip', "10.0.0.12/24")

        self.app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app1, 'appid', 'Kill#1')
        self.ec.set(self.app1, 'command', "/usr/bin/test -1")
        self.ec.set(self.app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        self.ec.register_connection(self.app1, self.node1)
        self.ec.register_connection(self.node1, self.iface1)

    def test_deploy_with_node_nc(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, "critical", False)

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "5s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_with_node_and_iface_nc(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, "critical", False)

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.node2, "critical", False)
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "5s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_with_node_iface_channel_nc(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, "critical", False)
        self.ec.set(self.node2, 'hostname', 'wlab49')

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.node2, "critical", False)
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, "critical", False)

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

        self.ec.register_condition([self.app1], ResourceAction.STOP, self.app1, ResourceState.STARTED , "10s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1])

        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)

    def test_deploy_with_app_nc(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'wlab49')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, "critical", False)
        self.ec.set(self.app2, 'appid', 'Kill#22')

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.app2, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "6s")
        self.ec.register_condition([self.app1, self.app2], ResourceAction.STOP, self.app1, ResourceState.STARTED , "10s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2])

        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.STOPPED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.RELEASED)

    def test_deploy_with_all_nc_and_app_critical(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, "critical", False)
        self.ec.set(self.node2, 'hostname', 'wlab49')

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, "critical", False)
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, "critical", False)
        self.ec.set(self.channel, 'channel', "6")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, 'appid', 'Kill#22')

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.app2, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "6s")
        self.ec.register_condition([self.app1, self.app2], ResourceAction.STOP, self.app1, ResourceState.STARTED , "10s")

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


class OMFVLCWrongCaseWithNonCriticalDep(unittest.TestCase):

    id = 3000

    def setUp(self):
        self.ec = ExperimentController(exp_id = str(OMFVLCWrongCaseWithNonCriticalDep.id))
        OMFVLCWrongCaseWithNonCriticalDep.id += 1

        self.node1 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node1, 'hostname', 'wlab12')
        self.ec.set(self.node1, 'xmppUser', "nepi")
        self.ec.set(self.node1, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node1, 'xmppPort', "5222")
        self.ec.set(self.node1, 'xmppPassword', "1234")
        
        self.iface1 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface1, 'name', "wlan0")
        self.ec.set(self.iface1, 'mode', "adhoc")
        self.ec.set(self.iface1, 'hw_mode', "g")
        self.ec.set(self.iface1, 'essid', "vlcexp")
        self.ec.set(self.iface1, 'ip', "10.0.0.12/24")

        self.app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app1, 'appid', 'Kill#1')
        self.ec.set(self.app1, 'command', "/usr/bin/test -1")
        self.ec.set(self.app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        self.ec.register_connection(self.app1, self.node1)
        self.ec.register_connection(self.node1, self.iface1)

    def test_deploy_with_app_nc_and_critical_wrong(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'wlab49')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, "critical", False)
        self.ec.set(self.app2, 'appid', 'Kill#32')

        self.app3 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app3, 'appid', 'Kill#33')

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.app2, self.node2)
        self.ec.register_connection(self.app3, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "5s")
        self.ec.register_condition(self.app3, ResourceAction.START, self.app2, ResourceState.STARTED , "5s")
        self.ec.register_condition([self.app1, self.app2, self.app3], ResourceAction.STOP, self.app1, ResourceState.STARTED , "15s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2, self.app3])

        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.app3).state, ResourceState.FAILED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app3).state, ResourceState.RELEASED)

    def test_deploy_with_app_nc_and_critical_right(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'wlab49')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, "critical", False)
        self.ec.set(self.app2, 'appid', 'Kill#32')

        self.app3 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app3, 'appid', 'Kill#3')
        self.ec.set(self.app3, 'command', "/usr/bin/test -3")
        self.ec.set(self.app3, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.app2, self.node2)
        self.ec.register_connection(self.app3, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "5s")
        self.ec.register_condition(self.app3, ResourceAction.START, self.app2, ResourceState.STARTED , "5s")
        self.ec.register_condition([self.app1, self.app2, self.app3], ResourceAction.STOP, self.app1, ResourceState.STARTED , "15s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2, self.app3])

        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.app3).state, ResourceState.STOPPED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app3).state, ResourceState.RELEASED)


    def test_deploy_with_many_app_nc_and_critical(self):
        self.node2 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node2, 'hostname', 'wlab49')
        self.ec.set(self.node2, 'xmppUser', "nepi")
        self.ec.set(self.node2, 'xmppServer', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node2, 'xmppPort', "5222")
        self.ec.set(self.node2, 'xmppPassword', "1234")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface2, 'name', "wlan0")
        self.ec.set(self.iface2, 'mode', "adhoc")
        self.ec.set(self.iface2, 'hw_mode', "g")
        self.ec.set(self.iface2, 'essid', "vlcexp")
        self.ec.set(self.iface2, 'ip', "10.0.0.49/24")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, "critical", False)
        self.ec.set(self.app2, 'appid', 'Kill#32')

        self.app3 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app3, "critical", False)
        self.ec.set(self.app3, 'appid', 'Kill#3')
        self.ec.set(self.app3, 'command', "/usr/bin/test -3")
        self.ec.set(self.app3, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        self.app4 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app4, 'appid', 'Kill#4')
        self.ec.set(self.app4, 'command', "/usr/bin/test -4")
        self.ec.set(self.app4, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        self.app5 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app5, "critical", False)
        self.ec.set(self.app5, 'appid', 'Kill#32')

        self.app6 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app6, 'appid', 'Kill#6')
        self.ec.set(self.app6, 'command', "/usr/bin/test -6")
        self.ec.set(self.app6, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)
        self.ec.register_connection(self.app2, self.node1)
        self.ec.register_connection(self.app3, self.node1)
        self.ec.register_connection(self.app4, self.node2)
        self.ec.register_connection(self.app5, self.node2)
        self.ec.register_connection(self.app6, self.node2)

        self.ec.register_condition(self.app2, ResourceAction.START, self.app1, ResourceState.STARTED , "4s")
        self.ec.register_condition(self.app3, ResourceAction.START, self.app2, ResourceState.STARTED , "4s")
        self.ec.register_condition(self.app4, ResourceAction.START, self.app1, ResourceState.STARTED , "4s")
        self.ec.register_condition(self.app5, ResourceAction.START, self.app4, ResourceState.STARTED , "4s")
        self.ec.register_condition(self.app6, ResourceAction.START, self.app5, ResourceState.STARTED , "4s")
        self.ec.register_condition([self.app1, self.app2, self.app3, self.app4, self.app5, self.app6 ], ResourceAction.STOP, [self.app1, self.app2, self.app3, self.app4, self.app5, self.app6 ], ResourceState.STARTED , "5s")

        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2, self.app3, self.app4, self.app5, self.app6])

        self.assertEquals(self.ec.get_resource(self.app3).state, ResourceState.STOPPED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.app4).state, ResourceState.STOPPED)
        self.assertEquals(self.ec.get_resource(self.app5).state, ResourceState.FAILED)
        self.assertEquals(self.ec.get_resource(self.app6).state, ResourceState.STOPPED)

        self.ec.shutdown()

        self.assertEquals(self.ec.get_resource(self.node1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.node2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.iface2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.channel).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app1).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app2).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app3).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app4).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app5).state, ResourceState.RELEASED)
        self.assertEquals(self.ec.get_resource(self.app6).state, ResourceState.RELEASED)


if __name__ == '__main__':
    unittest.main()



