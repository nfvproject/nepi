#!/usr/bin/env python
from neco.execution.resource import ResourceFactory, ResourceManager, ResourceAction, ResourceState
from neco.execution.ec import ExperimentController

from neco.resources.omf.omf_node import OMFNode
from neco.resources.omf.omf_application import OMFApplication
from neco.resources.omf.omf_interface import OMFWifiInterface
from neco.resources.omf.omf_channel import OMFChannel
from neco.resources.omf.omf_api import OMFAPIFactory

from neco.util import guid

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

        # For the moment
        self.ec.register_condition([iface1, channel], ResourceAction.START, node1, ResourceState.STARTED , 2)
        self.ec.register_condition(channel, ResourceAction.START, iface1, ResourceState.STARTED , 1)
        self.ec.register_condition(app1, ResourceAction.START, channel, ResourceState.STARTED , 1)

        # Real test
        self.ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , 4)

        self.assertEquals(len(self.ec.get_resource(node1).conditions), 0)
        self.assertEquals(len(self.ec.get_resource(iface1).conditions), 1)
        self.assertEquals(len(self.ec.get_resource(channel).conditions), 1)
        self.assertEquals(len(self.ec.get_resource(app1).conditions), 1)


    def xtest_deploy(self):
        ec.deploy()

    #In order to release everythings
        time.sleep(45)
        ec.shutdown()


if __name__ == '__main__':
    unittest.main()



