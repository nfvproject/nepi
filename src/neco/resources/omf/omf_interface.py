#!/usr/bin/env python
from neco.execution.resource import Resource, clsinit
from neco.execution.attribute import Attribute

from neco.resources.omf.omf_api import OMFAPIFactory

import neco
import logging

@clsinit
class OMFWifiInterface(Resource):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

    .. note::

       This class is used only by the Experiment Controller through the Resource Factory

    """
    _rtype = "OMFWifiInterface"
    _authorized_connections = ["OMFNode" , "OMFChannel"]

    #alias2name = dict({'w0':'wlan0', 'w1':'wlan1'})

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF interface 
        """
        alias = Attribute("alias","Alias of the interface", default_value = "w0")  
        mode = Attribute("mode","Mode of the interface")
        type = Attribute("type","Type of the interface")
        essid = Attribute("essid","Essid of the interface")
        ip = Attribute("ip","IP of the interface")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = "0x02")
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = "0x02")
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = "0x02")
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = "0x02")
        cls._register_attribute(alias)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)
        cls._register_attribute(mode)
        cls._register_attribute(type)
        cls._register_attribute(essid)
        cls._register_attribute(ip)

    def __init__(self, ec, guid, creds):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

        """
        super(OMFWifiInterface, self).__init__(ec, guid)
        self.set('xmppSlice', creds['xmppSlice'])
        self.set('xmppHost', creds['xmppHost'])
        self.set('xmppPort', creds['xmppPort'])
        self.set('xmppPassword', creds['xmppPassword'])

        self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))
        self._alias = self.get('alias')

        self._logger = logging.getLogger("neco.omf.omfIface  ")
        self._logger.setLevel(neco.LOGLEVEL)

    def _validate_connection(self, guid):
        """Check if the connection is available.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.resource(guid)
        if rm.rtype() in self._authorized_connections:
            self._logger.debug("Connection between %s %s and %s %s accepted" % (self.rtype(), self._guid, rm.rtype(), guid))
            return True
        self._logger.debug("Connection between %s %s and %s %s refused" % (self.rtype(), self._guid, rm.rtype(), guid))
        return False

    def _get_nodes(self, conn_set):
        """
        Get the RM of the node to which the application is connected

        :param conn_set: Connections of the current Guid
        :type conn_set: set
        :rtype: ResourceManager
        """
        for elt in conn_set:
            rm = self.ec.resource(elt)
            if rm.rtype() == "OMFNode":
                return rm
        return None


    def start(self):
        """Send Xmpp Messages Using OMF protocol to configure Interface

        """
        self._logger.debug(self.rtype() + " ( Guid : " + str(self._guid) +") : " + self.get('mode') + " : " + self.get('type') + " : " + self.get('essid') + " : " + self.get('ip'))
        #try:
        if self.get('mode') and self.get('type') and self.get('essid') and self.get('ip'):
            rm_node = self._get_nodes(self._connections)    
            for attrname in ["mode", "type", "essid", "ip"]:
                attrval = self.get(attrname)
                attrname = "net/%s/%s" % (self._alias, attrname)
                #print "Send the configure message"
                self._omf_api.configure(rm_node.get('hostname'), attrname, attrval)

    def stop(self):
        """Send Xmpp Message Using OMF protocol to put down the interface

        """
        self._omf_api.disconnect()



