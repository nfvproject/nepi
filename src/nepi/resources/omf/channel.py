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

from nepi.execution.resource import ResourceManager, clsinit, ResourceState
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.omf_api import OMFAPIFactory

reschedule_delay = "0.5s"

@clsinit
class OMFChannel(ResourceManager):
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
    _rtype = "OMFChannel"
    _authorized_connections = ["OMFWifiInterface", "OMFNode"]


    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF channel
        """
        channel = Attribute("channel", "Name of the application")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = Flags.Credential)
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = Flags.Credential)
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = Flags.Credential)
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = Flags.Credential)
        cls._register_attribute(channel)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)

    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

        """
        super(OMFChannel, self).__init__(ec, guid)

        self._nodes_guid = list()

        self._omf_api = None

    def valid_connection(self, guid):
        """Check if the connection with the guid in parameter is possible. Only meaningful connections are allowed.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.rtype() in self._authorized_connections:
            msg = "Connection between %s %s and %s %s accepted" % (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)
            return True
        msg = "Connection between %s %s and %s %s refused" % (self.rtype(), self._guid, rm.rtype(), guid)
        self.debug(msg)
        return False

    def _get_target(self, conn_set):
        """
        Get the couples (host, interface) that uses this channel

        :param conn_set: Connections of the current Guid
        :type conn_set: set
        :rtype: list
        :return: self._nodes_guid

        """
        for elt in conn_set:
            rm_iface = self.ec.get_resource(elt)
            for conn in rm_iface.connections:
                rm_node = self.ec.get_resource(conn)
                if rm_node.rtype() == "OMFNode" and rm_node.get('hostname'):
                    if rm_iface.state < ResourceState.READY or rm_node.state < ResourceState.READY:
                        return "reschedule"
                    couple = [rm_node.get('hostname'), rm_iface.get('alias')]
                    #print couple
                    self._nodes_guid.append(couple)
        return self._nodes_guid

    def discover(self):
        """ Discover the availables channels

        """
        pass
     
    def provision(self):
        """ Provision some availables channels

        """
        pass

    def deploy(self):
        """Deploy the RM. It means : Get the xmpp client and send messages using OMF 5.4 protocol to configure the channel
           It becomes DEPLOYED after sending messages to configure the channel

        """
        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))


        if self.get('channel'):
            set_nodes = self._get_target(self._connections) 
            if set_nodes == "reschedule" :
                self.ec.schedule(reschedule_delay, self.deploy)
                return
            print set_nodes
            try:
                for couple in set_nodes:
                    #print "Couple node/alias : " + couple[0] + "  ,  " + couple[1]
                    attrval = self.get('channel')
                    attrname = "net/%s/%s" % (couple[1], 'channel')
                    self._omf_api.configure(couple[0], attrname, attrval)
            except AttributeError:
                self._state = ResourceState.FAILED
                msg = "Credentials are not initialzed. XMPP Connections impossible"
                self.debug(msg)
                return
        else :
            msg = "Channel's value is not initialized"
            self.error(msg)

        super(OMFChannel, self).deploy()

    def start(self):
        """Start the RM. It means nothing special for a channel for now
           It becomes STARTED as soon as this method starts.

        """

        super(OMFChannel, self).start()

    def stop(self):
        """Stop the RM. It means nothing special for a channel for now
           It becomes STOPPED as soon as this method stops

        """
        super(OMFChannel, self).stop()

    def release(self):
        """Clean the RM at the end of the experiment and release the API

        """
        if self._omf_api :
            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

