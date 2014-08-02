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

from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.omf_resource import ResourceGateway, OMFResource
from nepi.resources.omf.omf_api_factory import OMFAPIFactory


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

    """
    _rtype = "OMFChannel"
    _authorized_connections = ["OMFWifiInterface", "OMFNode"]

    ChannelToFreq = dict({
             "1" : "2412",
             "2" : "2417",
             "3" : "2422",
             "4" : "2427",
             "5" : "2432",
             "6" : "2437",
             "7" : "2442",
             "8" : "2447",
             "9" : "2452",
             "10" : "2457",
             "11" : "2462",
             "12" : "2467",
             "13" : "2472",
    })

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

        """
        super(OMFChannel, self).__init__(ec, guid)

        self._nodes_guid = list()
        self.frequency = None

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
        if rm.get_rtype() in self._authorized_connections:
            msg = "Connection between %s %s and %s %s accepted" % (
                    self.get_rtype(), self._guid, rm.get_rtype(), guid)
            self.debug(msg)
            return True
        msg = "Connection between %s %s and %s %s refused" % (
                self.get_rtype(), self._guid, rm.get_rtype(), guid)
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
                if rm_node.get_rtype() == "OMFNode" and rm_node.get('hostname'):
                    if rm_iface.state < ResourceState.PROVISIONED or \
                            rm_node.state < ResourceState.READY:
                        return "reschedule"
                    couple = [rm_node.get('hostname'), rm_iface.alias]
                    res.append(couple)
        return res

    def get_frequency(self, channel):
        """ Returns the frequency of a specific channel number

        """           
        return OMFChannel.ChannelToFreq[channel]

    def do_deploy(self):
        """ Deploy the RM. It means : Get the xmpp client and send messages 
        using OMF 5.4 or 6 protocol to configure the channel.

        """   
        if not self.get('channel'):
            msg = "Channel's value is not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if self.get('version') == "6":
            self.frequency = self.get_frequency(self.get('channel'))
            super(OMFChannel, self).do_deploy()
            return


        if not self.get('xmppServer'):
            msg = "XmppServer is not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise RuntimeError, msg

        if not (self.get('xmppUser') or self.get('xmppPort') 
                   or self.get('xmppPassword')):
            msg = "Credentials are not all initialzed. Default values will be used"
            self.warn(msg)

        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('version'), 
              self.get('xmppServer'), self.get('xmppUser'), self.get('xmppPort'),
               self.get('xmppPassword'), exp_id = self.exp_id)

        self._nodes_guid = self._get_target(self._connections)



        if self._nodes_guid == "reschedule" :
            self.ec.schedule("1s", self.deploy)
        else:
            for couple in self._nodes_guid:
                attrval = self.get('channel')
                attrname = "net/%s/%s" % (couple[1], 'channel')
                self._omf_api.configure(couple[0], attrname, attrval)

        super(OMFChannel, self).do_deploy()

    def do_release(self):
        """ Clean the RM at the end of the experiment and release the API

        """
        if self._omf_api :
            OMFAPIFactory.release_api(self.get('version'), 
              self.get('xmppServer'), self.get('xmppUser'), self.get('xmppPort'),
               self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMFChannel, self).do_release()

