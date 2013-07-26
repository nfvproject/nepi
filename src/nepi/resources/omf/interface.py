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
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>
#         Julien Tribino <julien.tribino@inria.fr>

from nepi.execution.resource import ResourceManager, clsinit, ResourceState, \
        reschedule_delay
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.node import OMFNode
from nepi.resources.omf.omf_api import OMFAPIFactory


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

    @property
    def exp_id(self):
        if self.ec.exp_id.startswith('exp-'):
            return None
        return self.ec.exp_id

    def valid_connection(self, guid):
        """ Check if the connection with the guid in parameter is possible. Only meaningful connections are allowed.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.rtype() in self._authorized_connections:
            msg = "Connection between %s %s and %s %s accepted" % \
                (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)
            return True
        msg = "Connection between %s %s and %s %s refused" % \
             (self.rtype(), self._guid, rm.rtype(), guid)
        self.debug(msg)
        return False

    @property
    def node(self):
        rm_list = self.get_connected(OMFNode.rtype())
        if rm_list: return rm_list[0]
        return None

    def deploy(self):
        """Deploy the RM. It means : Get the xmpp client and send messages using OMF 5.4 protocol to configure the interface
           It becomes DEPLOYED after sending messages to configure the interface
        """
        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'), exp_id = self.exp_id)

        if not self._omf_api :
            self._state = ResourceState.FAILED
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            return

        if not (self.get('mode') and self.get('type') and self.get('essid') and self.get('ip')):
            self._state = ResourceState.FAILED
            msg = "Interface's variable are not initialized"
            self.error(msg)
            return False

        if not self.node.get('hostname') :
            msg = "The channel is connected with an undefined node"
            self.error(msg)
            return False

        # Just for information
        self.debug(" " + self.rtype() + " ( Guid : " + str(self._guid) +") : " + \
            self.get('mode') + " : " + self.get('type') + " : " + \
            self.get('essid') + " : " + self.get('ip'))
    
        # Check if the node is already deployed
        if self.node.state < ResourceState.READY:
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        try :
            for attrname in ["mode", "type", "essid", "ip"]:
                attrval = self.get(attrname)
                attrname = "net/%s/%s" % (self._alias, attrname)
                self._omf_api.configure(self.node.get('hostname'), attrname, attrval)
        except AttributeError:
            self._state = ResourceState.FAILED
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.debug(msg)
            #raise

        super(OMFWifiInterface, self).deploy()

    def start(self):
        """Start the RM. It means nothing special for an interface for now
           It becomes STARTED as soon as this method starts.

        """

        super(OMFWifiInterface, self).start()

    def stop(self):
        """Stop the RM. It means nothing special for an interface for now
           It becomes STOPPED as soon as this method stops

        """
        super(OMFWifiInterface, self).stop()

    def release(self):
        """Clean the RM at the end of the experiment and release the API

        """
        if self._omf_api :
            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMFWifiInterface, self).release()

