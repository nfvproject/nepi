
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
from nepi.resources.omf.omf_api import OMFAPIFactory

from nepi.util import guid
from nepi.util.timefuncs import *

import time
import unittest
import logging

logging.basicConfig()


class DummyEC(ExperimentController):
    pass

class DummyRM(ResourceManager):
    pass


class OMFResourceFactoryTestCase(unittest.TestCase):

    def test_creation_phase(self):
        ResourceFactory.register_type(OMFNode)
        ResourceFactory.register_type(OMFWifiInterface)
        ResourceFactory.register_type(OMFChannel)
        ResourceFactory.register_type(OMFApplication)

        self.assertEquals(OMFNode.rtype(), "OMFNode")
        self.assertEquals(len(OMFNode._attributes), 11)

        self.assertEquals(OMFWifiInterface.rtype(), "OMFWifiInterface")
        self.assertEquals(len(OMFWifiInterface._attributes), 9)

        self.assertEquals(OMFChannel.rtype(), "OMFChannel")
        self.assertEquals(len(OMFChannel._attributes), 5)

        self.assertEquals(OMFApplication.rtype(), "OMFApplication")
        self.assertEquals(len(OMFApplication._attributes), 8)

        self.assertEquals(len(ResourceFactory.resource_types()), 4)


class OMFVLCTestCase(unittest.TestCase):

    def setUp(self):
        self.ec = DummyEC()
        ResourceFactory.register_type(OMFNode)
        ResourceFactory.register_type(OMFWifiInterface)
        ResourceFactory.register_type(OMFChannel)
        ResourceFactory.register_type(OMFApplication)

        self.node1 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node1, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node1, 'xmppSlice', "nepi")
        self.ec.set(self.node1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node1, 'xmppPort', "5222")
        self.ec.set(self.node1, 'xmppPassword', "1234")

        self.node2 = self.ec.register_resource("OMFNode")
        
        self.iface1 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(self.iface1, 'alias', "w0")
        self.ec.set(self.iface1, 'mode', "adhoc")
        self.ec.set(self.iface1, 'type', "g")
        self.ec.set(self.iface1, 'essid', "vlcexp")
        self.ec.set(self.iface1, 'ip', "10.0.0.17")
        self.ec.set(self.iface1, 'xmppSlice', "nepi")
        self.ec.set(self.iface1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.iface1, 'xmppPort', "5222")
        self.ec.set(self.iface1, 'xmppPassword', "1234")

        self.iface2 = self.ec.register_resource("OMFWifiInterface")
        
        self.channel = self.ec.register_resource("OMFChannel")
        self.ec.set(self.channel, 'channel', "6")
        self.ec.set(self.channel, 'xmppSlice', "nepi")
        self.ec.set(self.channel, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.channel, 'xmppPort', "5222")
        self.ec.set(self.channel, 'xmppPassword', "1234")
        
        self.app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app1, 'appid', 'Vlc#1')
        self.ec.set(self.app1, 'path', "/opt/vlc-1.1.13/cvlc")
        self.ec.set(self.app1, 'args', "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.ec.set(self.app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
        self.ec.set(self.app1, 'xmppSlice', "nepi")
        self.ec.set(self.app1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.app1, 'xmppPort', "5222")
        self.ec.set(self.app1, 'xmppPassword', "1234")

        self.app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app2, 'xmppSlice', "nepi")
        self.ec.set(self.app2, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.app2, 'xmppPort', "5222")
        self.ec.set(self.app2, 'xmppPassword', "1234")

        self.app3 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app3, 'appid', 'Kill#2')
        self.ec.set(self.app3, 'path', "/usr/bin/killall")
        self.ec.set(self.app3, 'args', "vlc")
        self.ec.set(self.app3, 'env', " ")

        self.app4 = self.ec.register_resource("OMFApplication")

        self.app5 = self.ec.register_resource("OMFApplication")
        self.ec.set(self.app5, 'appid', 'Kill#2')
        self.ec.set(self.app5, 'path', "/usr/bin/killall")
        self.ec.set(self.app5, 'args', "vlc")
        self.ec.set(self.app5, 'env', " ")
        self.ec.set(self.app5, 'xmppSlice', "nepi")
        self.ec.set(self.app5, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.app5, 'xmppPort', "5222")
        self.ec.set(self.app5, 'xmppPassword', "1234")

        self.ec.register_connection(self.app1, self.node1)
        self.ec.register_connection(self.app2, self.node1)
        self.ec.register_connection(self.app3, self.node1)
        self.ec.register_connection(self.app4, self.node1)
        self.ec.register_connection(self.app5, self.node1)
        self.ec.register_connection(self.node1, self.iface1)
        self.ec.register_connection(self.iface1, self.channel)
        self.ec.register_connection(self.node2, self.iface2)
        self.ec.register_connection(self.iface2, self.channel)

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
        self.assertEquals(self.ec.get(self.node1, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(self.node1, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(self.node1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(self.node1, 'xmppPassword'), '1234')

    def test_creation_and_configuration_interface(self):
        self.assertEquals(self.ec.get(self.iface1, 'alias'), 'w0')
        self.assertEquals(self.ec.get(self.iface1, 'mode'), 'adhoc')
        self.assertEquals(self.ec.get(self.iface1, 'type'), 'g')
        self.assertEquals(self.ec.get(self.iface1, 'essid'), 'vlcexp')
        self.assertEquals(self.ec.get(self.iface1, 'ip'), '10.0.0.17')
        self.assertEquals(self.ec.get(self.iface1, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(self.iface1, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(self.iface1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(self.iface1, 'xmppPassword'), '1234')

    def test_creation_and_configuration_channel(self):
        self.assertEquals(self.ec.get(self.channel, 'channel'), '6')
        self.assertEquals(self.ec.get(self.channel, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(self.channel, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(self.channel, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(self.channel, 'xmppPassword'), '1234')

    def test_creation_and_configuration_application(self):
        self.assertEquals(self.ec.get(self.app1, 'appid'), 'Vlc#1')
        self.assertEquals(self.ec.get(self.app1, 'path'), '/opt/vlc-1.1.13/cvlc')
        self.assertEquals(self.ec.get(self.app1, 'args'), "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.assertEquals(self.ec.get(self.app1, 'env'), 'DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority')
        self.assertEquals(self.ec.get(self.app1, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(self.app1, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(self.app1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(self.app1, 'xmppPassword'), '1234')

    def test_connection(self):
        self.assertEquals(len(self.ec.get_resource(self.node1).connections), 6)
        self.assertEquals(len(self.ec.get_resource(self.iface1).connections), 2)
        self.assertEquals(len(self.ec.get_resource(self.channel).connections), 2)
        self.assertEquals(len(self.ec.get_resource(self.app1).connections), 1)
        self.assertEquals(len(self.ec.get_resource(self.app2).connections), 1)

    def test_condition(self):
        self.assertEquals(len(self.ec.get_resource(self.app1).conditions[ResourceAction.STOP]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app2).conditions[ResourceAction.START]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app3).conditions[ResourceAction.START]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app4).conditions[ResourceAction.STOP]), 1)
        self.assertEquals(len(self.ec.get_resource(self.app5).conditions[ResourceAction.START]), 2)

    def test_deploy(self):
        
        self.ec.deploy()

        self.ec.wait_finished([self.app1, self.app2, self.app3,self.app4, self.app5])

        self.assertEquals(round(strfdiff(self.ec.get_resource(self.app2).start_time, self.ec.get_resource(self.app1).start_time),1), 3.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(self.app3).start_time, self.ec.get_resource(self.app2).start_time),1), 2.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(self.app4).start_time, self.ec.get_resource(self.app3).start_time),1), 3.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(self.app5).start_time, self.ec.get_resource(self.app3).start_time),1), 20.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(self.app5).start_time, self.ec.get_resource(self.app1).start_time),1), 25.0)
        # Precision is at 1/10. So this one returns an error 7.03 != 7.0
        #self.assertEquals(strfdiff(self.ec.get_resource(self.app5).start_time, self.ec.get_resource(self.app1).start_time), 7)
    #In order to release everythings
        time.sleep(1)


if __name__ == '__main__':
    unittest.main()



