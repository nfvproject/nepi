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

from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.omf_resource import ResourceGateway, OMFResource
from nepi.resources.omf.omf_api import OMFAPIFactory


@clsinit_copy
class OMFChannel(OMFResource):
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
        cls._register_attribute(channel)

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

    @property
    def exp_id(self):
        return self.ec.exp_id

    def valid_connection(self, guid):
        """ Check if the connection with the guid in parameter is possible.
        Only meaningful connections are allowed.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        
        if rm.rtype() in self._authorized_connections:
            msg = "Connection between %s %s and %s %s accepted" % (
                    self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)
            return True

        msg = "Connection between %s %s and %s %s refused" % (
                self.rtype(), self._guid, rm.rtype(), guid)
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
        res = []
        for elt in conn_set:
            rm_iface = self.ec.get_resource(elt)
            for conn in rm_iface.connections:
                rm_node = self.ec.get_resource(conn)
                if rm_node.rtype() == "OMFNode" and rm_node.get('hostname'):
                    if rm_iface.state < ResourceState.PROVISIONED or \
                            rm_node.state < ResourceState.READY:
                        return "reschedule"
                    couple = [rm_node.get('hostname'), rm_iface.get('alias')]
                    #print couple
                    res.append(couple)
        return res

    def discover(self):
        """ Discover the availables channels

        """
        pass
     
    def provision(self):
        """ Provision some availables channels

        """
        pass

    def deploy(self):
        """ Deploy the RM. It means : Get the xmpp client and send messages 
        using OMF 5.4 protocol to configure the channel.
        It becomes DEPLOYED after sending messages to configure the channel

        """
        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        if not self._omf_api :
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            self.fail()
            return

        if not self.get('channel'):
            msg = "Channel's value is not initialized"
            self.error(msg)
            self.fail()
            raise

        self._nodes_guid = self._get_target(self._connections) 
        if self._nodes_guid == "reschedule" :
            self.ec.schedule("2s", self.deploy)
            return False

        try:
            for couple in self._nodes_guid:
                #print "Couple node/alias : " + couple[0] + "  ,  " + couple[1]
                attrval = self.get('channel')
                attrname = "net/%s/%s" % (couple[1], 'channel')
                self._omf_api.configure(couple[0], attrname, attrval)
        except AttributeError:
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            self.fail()
            raise

        super(OMFChannel, self).deploy()

    def start(self):
        """ Start the RM. It means nothing special for a channel for now
        It becomes STARTED as soon as this method starts.

        """

        super(OMFChannel, self).start()

    def stop(self):
        """ Stop the RM. It means nothing special for a channel for now
        It becomes STOPPED as soon as this method is called

        """
        super(OMFChannel, self).stop()

    def release(self):
        """ Clean the RM at the end of the experiment and release the API

        """
        if self._omf_api :
            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMFChannel, self).release()

