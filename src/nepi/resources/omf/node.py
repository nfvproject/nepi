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
from nepi.resources.omf.omf_api import OMFAPIFactory

import time

@clsinit_copy
class OMFNode(OMFResource):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

    """
    _rtype = "OMFNode"
    _authorized_connections = ["OMFApplication" , "OMFWifiInterface"]

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF Node

        """
        hostname = Attribute("hostname", "Hostname of the machine")

        cls._register_attribute(hostname)

    # XXX: We don't necessary need to have the credentials at the 
    # moment we create the RM
    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

        """
        super(OMFNode, self).__init__(ec, guid)

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

    def do_deploy(self):
        """ Deploy the RM. It means : Send Xmpp Message Using OMF protocol 
            to enroll the node into the experiment.
            It becomes DEPLOYED after sending messages to enroll the node

        """ 
        if not (self.get('xmppSlice') and self.get('xmppHost')
              and self.get('xmppPort') and self.get('xmppPassword')):
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise RuntimeError, msg

        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        if not self.get('hostname') :
            msg = "Hostname's value is not initialized"
            self.error(msg)
            raise RuntimeError, msg

        self._omf_api.enroll_host(self.get('hostname'))

        super(OMFNode, self).do_deploy()

    def do_release(self):
        """ Clean the RM at the end of the experiment

        """
        if self._omf_api:
            self._omf_api.release(self.get('hostname'))

            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMFNode, self).do_release()

