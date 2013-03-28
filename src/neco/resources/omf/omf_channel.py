#!/usr/bin/env python
from neco.execution.resource import ResourceManager, clsinit
from neco.execution.attribute import Attribute

from neco.resources.omf.omf_api import OMFAPIFactory

import neco
import logging

@clsinit
class OMFChannel(ResourceManager):
    _rtype = "OMFChannel"
    _authorized_connections = ["OMFWifiInterface"]

    @classmethod
    def _register_attributes(cls):
        channel = Attribute("channel", "Name of the application")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = "0x02")
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = "0x02")
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = "0x02")
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = "0x02")
        cls._register_attribute(channel)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)

    def __init__(self, ec, guid, creds):
        super(OMFChannel, self).__init__(ec, guid)
        self.set('xmppSlice', creds['xmppSlice'])
        self.set('xmppHost', creds['xmppHost'])
        self.set('xmppPort', creds['xmppPort'])
        self.set('xmppPassword', creds['xmppPassword'])

        self._nodes_guid = list()

        self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

        self._logger = logging.getLogger("neco.omf.omfChannel")
        self._logger.setLevel(neco.LOGLEVEL)

    def _validate_connection(self, guid):
        rm = self.ec.resource(guid)
        if rm.rtype() in self._authorized_connections:
            self._logger.debug("Connection between %s %s and %s %s accepted" % (self.rtype(), self._guid, rm.rtype(), guid))
            return True
        self._logger.debug("Connection between %s %s and %s %s refused" % (self.rtype(), self._guid, rm.rtype(), guid))
        return False

    def _get_nodes(self, conn_set):
        for elt in conn_set:
            rm_iface = self.ec.resource(elt)
            for conn in rm_iface._connections:
                rm_node = self.ec.resource(conn)
                if rm_node.rtype() == "OMFNode":
                    couple = [rm_node.get('hostname'), rm_iface.get('alias')]
                    #print couple
                    self._nodes_guid.append(couple)
        return self._nodes_guid

    def discover(self):
        pass
     
    def provision(self, credential):
        pass

    def start(self):
        if self.get('channel'):
            set_nodes = self._get_nodes(self._connections) 
            #print set_nodes
            for couple in set_nodes:
                #print "Couple node/alias : " + couple[0] + "  ,  " + couple[1]
                attrval = self.get('channel')
                attrname = "net/%s/%s" % (couple[1], 'channel')
                #print "Send the configure message"
                self._omf_api.configure(couple[0], attrname, attrval)

    def xstart(self):
        try:
            if self.get('channel'):
                node = self.tc.elements.get(self._node_guid)    
                attrval = self.get('channel')
                attrname = "net/%s/%s" % (self._alias, 'channel')
                self._omf_api.configure('omf.plexus.wlab17', attrname, attrval)
        except AttributeError:
            # If the attribute is not yet defined, ignore the error
            pass


