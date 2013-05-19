#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceManager, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

from nepi.resources.omf.omf_node import OMFNode
from nepi.resources.omf.omf_application import OMFApplication
from nepi.resources.omf.omf_interface import OMFWifiInterface
from nepi.resources.omf.omf_channel import OMFChannel
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
        self.assertEquals(len(OMFNode._attributes), 7)

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

    def tearDown(self):
        self.ec.shutdown()

    def test_creation_and_configuration_node(self):

        node1 = self.ec.register_resource("OMFNode")
        self.ec.set(node1, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(node1, 'xmppSlice', "nepi")
        self.ec.set(node1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(node1, 'xmppPort', "5222")
        self.ec.set(node1, 'xmppPassword', "1234")

        self.assertEquals(self.ec.get(node1, 'hostname'), 'omf.plexus.wlab17')
        self.assertEquals(self.ec.get(node1, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(node1, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(node1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(node1, 'xmppPassword'), '1234')

    def test_creation_and_configuration_interface(self):

        iface1 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(iface1, 'alias', "w0")
        self.ec.set(iface1, 'mode', "adhoc")
        self.ec.set(iface1, 'type', "g")
        self.ec.set(iface1, 'essid', "vlcexp")
        self.ec.set(iface1, 'ip', "10.0.0.17")
        self.ec.set(iface1, 'xmppSlice', "nepi")
        self.ec.set(iface1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(iface1, 'xmppPort', "5222")
        self.ec.set(iface1, 'xmppPassword', "1234")

        self.assertEquals(self.ec.get(iface1, 'alias'), 'w0')
        self.assertEquals(self.ec.get(iface1, 'mode'), 'adhoc')
        self.assertEquals(self.ec.get(iface1, 'type'), 'g')
        self.assertEquals(self.ec.get(iface1, 'essid'), 'vlcexp')
        self.assertEquals(self.ec.get(iface1, 'ip'), '10.0.0.17')
        self.assertEquals(self.ec.get(iface1, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(iface1, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(iface1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(iface1, 'xmppPassword'), '1234')

    def test_creation_and_configuration_channel(self):

        channel = self.ec.register_resource("OMFChannel")
        self.ec.set(channel, 'channel', "6")
        self.ec.set(channel, 'xmppSlice', "nepi")
        self.ec.set(channel, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(channel, 'xmppPort', "5222")
        self.ec.set(channel, 'xmppPassword', "1234")

        self.assertEquals(self.ec.get(channel, 'channel'), '6')
        self.assertEquals(self.ec.get(channel, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(channel, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(channel, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(channel, 'xmppPassword'), '1234')

    def test_creation_and_configuration_application(self):

        app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(app1, 'appid', 'Vlc#1')
        self.ec.set(app1, 'path', "/opt/vlc-1.1.13/cvlc")
        self.ec.set(app1, 'args', "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.ec.set(app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
        self.ec.set(app1, 'xmppSlice', "nepi")
        self.ec.set(app1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(app1, 'xmppPort', "5222")
        self.ec.set(app1, 'xmppPassword', "1234")

        self.assertEquals(self.ec.get(app1, 'appid'), 'Vlc#1')
        self.assertEquals(self.ec.get(app1, 'path'), '/opt/vlc-1.1.13/cvlc')
        self.assertEquals(self.ec.get(app1, 'args'), "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        self.assertEquals(self.ec.get(app1, 'env'), 'DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority')
        self.assertEquals(self.ec.get(app1, 'xmppSlice'), 'nepi')
        self.assertEquals(self.ec.get(app1, 'xmppHost'), 'xmpp-plexus.onelab.eu')
        self.assertEquals(self.ec.get(app1, 'xmppPort'), '5222')
        self.assertEquals(self.ec.get(app1, 'xmppPassword'), '1234')

    def test_connection(self):

        node1 = self.ec.register_resource("OMFNode")
        iface1 = self.ec.register_resource("OMFWifiInterface")
        channel = self.ec.register_resource("OMFChannel")
        app1 = self.ec.register_resource("OMFApplication")
        app2 = self.ec.register_resource("OMFApplication")

        self.ec.register_connection(app1, node1)
        self.ec.register_connection(app2, node1)
        self.ec.register_connection(node1, iface1)
        self.ec.register_connection(iface1, channel)

        self.assertEquals(len(self.ec.get_resource(node1).connections), 3)
        self.assertEquals(len(self.ec.get_resource(iface1).connections), 2)
        self.assertEquals(len(self.ec.get_resource(channel).connections), 1)
        self.assertEquals(len(self.ec.get_resource(app1).connections), 1)
        self.assertEquals(len(self.ec.get_resource(app2).connections), 1)

    def test_condition(self):

        node1 = self.ec.register_resource("OMFNode")
        iface1 = self.ec.register_resource("OMFWifiInterface")
        channel = self.ec.register_resource("OMFChannel")
        app1 = self.ec.register_resource("OMFApplication")
        app2 = self.ec.register_resource("OMFApplication")

        self.ec.register_connection(app1, node1)
        self.ec.register_connection(app2, node1)
        self.ec.register_connection(node1, iface1)
        self.ec.register_connection(iface1, channel)

        self.ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , "4s")

        self.assertEquals(len(self.ec.get_resource(app2).conditions), 1)

    def test_deploy(self):
        node1 = self.ec.register_resource("OMFNode")
        self.ec.set(node1, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(node1, 'xmppSlice', "nepi")
        self.ec.set(node1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(node1, 'xmppPort', "5222")
        self.ec.set(node1, 'xmppPassword', "1234")
        
        iface1 = self.ec.register_resource("OMFWifiInterface")
        self.ec.set(iface1, 'alias', "w0")
        self.ec.set(iface1, 'mode', "adhoc")
        self.ec.set(iface1, 'type', "g")
        self.ec.set(iface1, 'essid', "vlcexp")
        self.ec.set(iface1, 'ip', "10.0.0.17")
        self.ec.set(iface1, 'xmppSlice', "nepi")
        self.ec.set(iface1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(iface1, 'xmppPort', "5222")
        self.ec.set(iface1, 'xmppPassword', "1234")
        
        channel = self.ec.register_resource("OMFChannel")
        self.ec.set(channel, 'channel', "6")
        self.ec.set(channel, 'xmppSlice', "nepi")
        self.ec.set(channel, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(channel, 'xmppPort', "5222")
        self.ec.set(channel, 'xmppPassword', "1234")
        
        app1 = self.ec.register_resource("OMFApplication")
        self.ec.set(app1, 'xmppSlice', "nepi")
        self.ec.set(app1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(app1, 'xmppPort', "5222")
        self.ec.set(app1, 'xmppPassword', "1234")

        app2 = self.ec.register_resource("OMFApplication")
        self.ec.set(app2, 'xmppSlice', "nepi")
        self.ec.set(app2, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(app2, 'xmppPort', "5222")
        self.ec.set(app2, 'xmppPassword', "1234")

        app3 = self.ec.register_resource("OMFApplication")
        self.ec.set(app3, 'xmppSlice', "nepi")
        self.ec.set(app3, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(app3, 'xmppPort', "5222")
        self.ec.set(app3, 'xmppPassword', "1234")

        app4 = self.ec.register_resource("OMFApplication")
        self.ec.set(app4, 'xmppSlice', "nepi")
        self.ec.set(app4, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(app4, 'xmppPort', "5222")
        self.ec.set(app4, 'xmppPassword', "1234")

        app5 = self.ec.register_resource("OMFApplication")
        self.ec.set(app5, 'xmppSlice', "nepi")
        self.ec.set(app5, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(app5, 'xmppPort', "5222")
        self.ec.set(app5, 'xmppPassword', "1234")

        self.ec.register_connection(app1, node1)
        self.ec.register_connection(app2, node1)
        self.ec.register_connection(app3, node1)
        self.ec.register_connection(app4, node1)
        self.ec.register_connection(app5, node1)
        self.ec.register_connection(node1, iface1)
        self.ec.register_connection(iface1, channel)

        self.ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , "3s")
        self.ec.register_condition(app3, ResourceAction.START, app2, ResourceState.STARTED , "2s")
        self.ec.register_condition(app4, ResourceAction.START, app3, ResourceState.STARTED , "3s")
        self.ec.register_condition(app5, ResourceAction.START, [app3, app2], ResourceState.STARTED , "2s")
        self.ec.register_condition(app5, ResourceAction.START, app1, ResourceState.STARTED , "1m20s")

        self.ec.deploy()
        time.sleep(150)

        self.assertEquals(round(strfdiff(self.ec.get_resource(app2).start_time, self.ec.get_resource(app1).start_time),1), 3.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(app3).start_time, self.ec.get_resource(app2).start_time),1), 2.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(app4).start_time, self.ec.get_resource(app3).start_time),1), 3.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(app5).start_time, self.ec.get_resource(app3).start_time),1), 2.0)
        self.assertEquals(round(strfdiff(self.ec.get_resource(app5).start_time, self.ec.get_resource(app1).start_time),1), 7.0)

        # Precision is at 1/10. So this one returns an error 7.03 != 7.0
        #self.assertEquals(strfdiff(self.ec.get_resource(app5).start_time, self.ec.get_resource(app1).start_time), 7)
    #In order to release everythings
        time.sleep(5)


if __name__ == '__main__':
    unittest.main()



