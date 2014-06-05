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

import os, time
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.node import OMFNode, confirmation_counter, reschedule_check
from nepi.resources.omf.omf_resource import ResourceGateway, OMFResource
from nepi.resources.omf.channel import OMFChannel
from nepi.resources.omf.omf_api_factory import OMFAPIFactory

@clsinit_copy
class OMFWifiInterface(OMFResource):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    """
    _rtype = "OMFWifiInterface"
    _authorized_connections = ["OMFNode" , "OMFChannel"]

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF interface 

        """
        name = Attribute("name","Alias of the interface : wlan0, wlan1, ..", default = "wlan0")
        mode = Attribute("mode","Mode of the interface")
        hw_mode = Attribute("hw_mode","Choose between : a, b, g, n")
        essid = Attribute("essid","Essid of the interface")
        ip = Attribute("ip","IP of the interface")
        cls._register_attribute(name)
        cls._register_attribute(mode)
        cls._register_attribute(hw_mode)
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

        self._conf = False
        self.alias = None
        self._type = None

        self.create_id = None
        self._create_cnt = 0
        self.release_id = None
        self._release_cnt = 0
        self._topic_iface = None
        self._omf_api = None
        self._type = ""


    def valid_connection(self, guid):
        """ Check if the connection with the guid in parameter is possible. 
        Only meaningful connections are allowed.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.get_rtype() in self._authorized_connections:
            msg = "Connection between %s %s and %s %s accepted" % \
                (self.get_rtype(), self._guid, rm.get_rtype(), guid)
            self.debug(msg)
            return True

        msg = "Connection between %s %s and %s %s refused" % \
             (self.get_rtype(), self._guid, rm.get_rtype(), guid)
        self.debug(msg)
        return False

    @property
    def exp_id(self):
        return self.ec.exp_id

    @property
    def node(self):
        rm_list = self.get_connected(OMFNode.get_rtype())
        if rm_list: return rm_list[0]
        return None

    @property
    def channel(self):
        rm_list = self.get_connected(OMFChannel.get_rtype())
        if rm_list: return rm_list[0]
        return None

    def configure_iface(self):
        """ Configure the interface without the ip

        """
        if self.node.state < ResourceState.READY:
            self.ec.schedule(reschedule_delay, self.deploy)
            return False

        for attrname in ["mode", "type", "essid"]:
            if attrname == "type" :
                attrval = self._type
            else :
                attrval = self.get(attrname)
            attrname = "net/%s/%s" % (self.alias, attrname)
            self._omf_api.configure(self.node.get('hostname'), attrname, 
                        attrval)
        
        super(OMFWifiInterface, self).do_provision()
        return True

    def configure_ip(self):
        """ Configure the ip of the interface

        .. note : The ip is separated from the others parameters to avoid 
        CELL ID shraing problem. By putting th ip at the end of the configuration, 
        each node use the same channel and can then share the same CELL ID.
        In the second case, the channel is defined at the end and the node don't
        share a common CELL ID and can not communicate.

        """
        if self.channel.state < ResourceState.READY:
            self.ec.schedule(reschedule_delay, self.deploy)
            return False

        attrval = self.get("ip")
        if '/' in attrval:
           attrval,mask = attrval.split('/')
        attrname = "net/%s/%s" % (self.alias, "ip")
        self._omf_api.configure(self.node.get('hostname'), attrname, 
                    attrval)
        return True


    def configure_on_omf5(self):
        """ Method to configure the wifi interface when OMF 5.4 is used.

        """    

        self._type = self.get('hw_mode')
        if self.get('name') == "wlan0" or "eth0":
            self.alias = "w0"
        else:    
            self.alias = "w1"
        res = False
        if self.state < ResourceState.PROVISIONED:
            if self._conf == False:
                self._conf = self.configure_iface()
        if self._conf == True:
            res = self.configure_ip()
        return res

    def check_deploy(self, cid):
        """ Check, through the mail box in the parser, 
        if the confirmation of the creation has been received

        :param cid: the id of the original message
        :type guid: string

        """
        uid = self._omf_api.check_mailbox("create", cid)
        if uid : 
            return uid
        return False

    def do_deploy(self):
        """ Deploy the RM. It means : Get the xmpp client and send messages 
        using OMF 5.4 or 6 protocol to configure the interface.

        """
        if not self.node or self.node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s "
                       % self.node.state )
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        if not self.channel or self.channel.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- channel state %s "
                       % self.channel.state )
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.set('xmppUser',self.node.get('xmppUser'))
        self.set('xmppServer',self.node.get('xmppServer'))
        self.set('xmppPort',self.node.get('xmppPort'))
        self.set('xmppPassword',self.node.get('xmppPassword'))
        self.set('version',self.node.get('version'))

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

        if not (self.get('name')):
            msg = "Interface's name is not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if not (self.get('mode') and self.get('essid') \
                 and self.get('hw_mode') and self.get('ip')):
            msg = "Interface's variable are not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if self.get('version') == "5":
            res = self.configure_on_omf5()        

        else :
            res = self.configure_on_omf6()

        if res:
            super(OMFWifiInterface, self).do_deploy()

    def configure_on_omf6(self):
        """ Method to configure the wifi interface when OMF 6 is used.

        """   
        if not self.create_id :
            props = {}
            props['wlan:if_name'] = self.get('name')
            props['wlan:mode'] = {
                "mode": self.get('mode'),
                "hw_mode" :  self.get('hw_mode'),
                "channel" : self.channel.get('channel'),
                "essid" : self.get('essid'),
                "ip_addr" : self.get('ip'),
                "frequency" : self.channel.frequency,
                "phy" : "%0%"
               }
            props['wlan:hrn'] = self.get('name')
            props['wlan:type'] = "wlan"
    
            self.create_id = os.urandom(16).encode('hex')
            self._omf_api.frcp_create( self.create_id, self.node.get('hostname'), "wlan", props = props)
    
        if self._create_cnt > confirmation_counter:
            msg = "Couldn't retrieve the confirmation of the creation"
            self.error(msg)
            raise RuntimeError, msg

        uid = self.check_deploy(self.create_id)
        if not uid:
            self._create_cnt +=1
            self.ec.schedule(reschedule_check, self.deploy)
            return False

        self._topic_iface = uid
        self._omf_api.enroll_topic(self._topic_iface)
        return True

    def check_release(self, cid):
        """ Check, through the mail box in the parser, 
        if the confirmation of the release has been received

        :param cid: the id of the original message
        :type guid: string

        """
        res = self._omf_api.check_mailbox("release", cid)
        if res : 
            return res
        return False

    def do_release(self):
        """ Clean the RM at the end of the experiment and release the API

        """
        if self._omf_api:
            if self.get('version') == "6":
                if not self.release_id:
                    self.release_id = os.urandom(16).encode('hex')
                    self._omf_api.frcp_release( self.release_id, self.node.get('hostname'),self._topic_iface, res_id=self._topic_iface)
    
                if self._release_cnt < confirmation_counter:
                    cid = self.check_release(self.release_id)
                    if not cid:
                        self._release_cnt +=1
                        self.ec.schedule(reschedule_check, self.release)
                        return
                else:
                    msg = "Couldn't retrieve the confirmation of the release"
                    self.error(msg)


            OMFAPIFactory.release_api(self.get('version'), 
              self.get('xmppServer'), self.get('xmppUser'), self.get('xmppPort'),
               self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMFWifiInterface, self).do_release()

