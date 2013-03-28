#!/usr/bin/env python
from neco.execution.resource import ResourceFactory
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

class OMFVLCTestCase(unittest.TestCase):

    def setUp(self):
        #self.guid_generator = guid.GuidGenerator()
        self._creds = {'xmppSlice' : 'nepi' , 'xmppHost' : 'xmpp-plexus.onelab.eu' , 'xmppPort' : '5222', 'xmppPassword' : '1234'  }

    def tearDown(self):
        pass

    def test_creation_phase(self):
        ec = DummyEC()

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

    #def xtest_creation_and_configuration_node(self):
        guid = ec.register_resource("OMFNode", creds =  self._creds)
        node1 = ec._resources[guid]
        node1.set('hostname', 'omf.plexus.wlab17')

        guid = ec.register_resource("OMFNode", creds =  self._creds)
        node2 = ec._resources[guid]
        node2.set('hostname', "omf.plexus.wlab37")

    #def xtest_creation_and_configuration_interface(self):
        guid = ec.register_resource("OMFWifiInterface", creds =  self._creds)
        iface1 = ec._resources[guid]
        iface1.set('alias', "w0")
        iface1.set('mode', "adhoc")
        iface1.set('type', "g")
        iface1.set('essid', "helloworld")
        iface1.set('ip', "10.0.0.17")

        guid = ec.register_resource("OMFWifiInterface", creds =  self._creds)
        iface2 = ec._resources[guid]
        iface2.set('alias', "w0")
        iface2.set('mode', "adhoc")
        iface2.set('type', 'g')
        iface2.set('essid', "helloworld")
        iface2.set('ip', "10.0.0.37")  

    #def xtest_creation_and_configuration_channel(self):
        guid = ec.register_resource("OMFChannel", creds =  self._creds)
        channel = ec._resources[guid]
        channel.set('channel', "6")

    #def xtest_creation_and_configuration_application(self):
        guid = ec.register_resource("OMFApplication", creds =  self._creds)
        app1 = ec._resources[guid]
        app1.set('appid', 'Vlc#1')
        app1.set('path', "/opt/vlc-1.1.13/cvlc")
        app1.set('args', "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
        app1.set('env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")

        guid = ec.register_resource("OMFApplication", creds =  self._creds)
        app2 = ec._resources[guid]
        app2.set('appid', 'Vlc#2')
        app2.set('path', "/opt/vlc-1.1.13/cvlc")
        app2.set('args', "rtp://10.0.0.37:1234")
        app2.set('env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
        self.assertEquals(len(OMFAPIFactory._Api), 1)   

    #def test_connection(self):
        app1.connect(node1._guid)
        node1.connect(app1._guid)

        node1.connect(iface1._guid)
        iface1.connect(node1._guid)

        iface1.connect(channel._guid)
        channel.connect(iface1._guid)

        channel.connect(iface2._guid)
        iface2.connect(channel._guid)

        iface2.connect(node2._guid)
        node2.connect(iface2._guid)

        node2.connect(app2._guid)
        app2.connect(node2._guid)

    #def test_start_node(self):
        node1.start()
        node2.start()
        time.sleep(1)
        #pass

    #def test_start_interface(self):
        iface1.start()
        iface2.start()

    #def test_start_channel(self):
        channel.start()
        time.sleep(1)

    #def test_start_application(self):
        app1.start()
        time.sleep(2)
        app2.start()

        time.sleep(10)
    
    #def test_stop_application(self):
        app1.stop()
        app2.stop()
        time.sleep(2)


    #def test_stop_nodes(self):
        node1.stop()
        #node2.stop()


if __name__ == '__main__':
    unittest.main()

