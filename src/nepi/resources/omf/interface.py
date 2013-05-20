"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from nepi.execution.resource import ResourceManager, clsinit
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.omf_api import OMFAPIFactory

import nepi
import logging

@clsinit
class OMFWifiInterface(ResourceManager):
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
    _waiters = ["OMFNode"]

    #alias2name = dict({'w0':'wlan0', 'w1':'wlan1'})

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF interface 

        """
        alias = Attribute("alias","Alias of the interface", default = "w0")
        mode = Attribute("mode","Mode of the interface")
        type = Attribute("type","Type of the interface")
        essid = Attribute("essid","Essid of the interface")
        ip = Attribute("ip","IP of the interface")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = Flags.Credential)
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = Flags.Credential)
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = Flags.Credential)
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = Flags.Credential)
        cls._register_attribute(alias)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)
        cls._register_attribute(mode)
        cls._register_attribute(type)
        cls._register_attribute(essid)
        cls._register_attribute(ip)

    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

        """
        super(OMFWifiInterface, self).__init__(ec, guid)

        self._omf_api = None
        self._alias = self.get('alias')

        self._logger = logging.getLogger("nepi.omf.omfIface  ")
        self._logger.setLevel(nepi.LOGLEVEL)

    def _validate_connection(self, guid):
        """ Check if the connection is available.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.rtype() in self._authorized_connections:
            self._logger.debug("Connection between %s %s and %s %s accepted" %
                (self.rtype(), self._guid, rm.rtype(), guid))
            return True
        self._logger.debug("Connection between %s %s and %s %s refused" % 
            (self.rtype(), self._guid, rm.rtype(), guid))
        return False

    def _get_nodes(self, conn_set):
        """ Get the RM of the node to which the application is connected

        :param conn_set: Connections of the current Guid
        :type conn_set: set
        :rtype: ResourceManager

        """
        for elt in conn_set:
            rm = self.ec.get_resource(elt)
            if rm.rtype() == "OMFNode":
                return rm
        return None

    def deploy_action(self):
        """Deploy the RM

        """
        self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
            self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

        self._logger.debug(" " + self.rtype() + " ( Guid : " + str(self._guid) +") : " +
            self.get('mode') + " : " + self.get('type') + " : " +
            self.get('essid') + " : " + self.get('ip'))
        #try:
        if self.get('mode') and self.get('type') and self.get('essid') and self.get('ip'):
            rm_node = self._get_nodes(self._connections)    
            for attrname in ["mode", "type", "essid", "ip"]:
                attrval = self.get(attrname)
                attrname = "net/%s/%s" % (self._alias, attrname)
                #print "Send the configure message"
                self._omf_api.configure(rm_node.get('hostname'), attrname, attrval)

        super(OMFWifiInterface, self).deploy_action()


    def start(self):
        """Send Xmpp Messages Using OMF protocol to configure Interface

        """

        super(OMFWifiInterface, self).start()

    def stop(self):
        """Send Xmpp Message Using OMF protocol to put down the interface

        """
        super(OMFWifiInterface, self).stop()

    def release(self):
        """Clean the RM at the end of the experiment

        """
        OMFAPIFactory.release_api(self.get('xmppSlice'), 
            self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))


