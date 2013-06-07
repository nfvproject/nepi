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


from nepi.execution.resource import ResourceManager, clsinit, ResourceState
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.omf_api import OMFAPIFactory

import time

reschedule_delay = "0.5s"

@clsinit
class OMFNode(ResourceManager):
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
    _rtype = "OMFNode"
    _authorized_connections = ["OMFApplication" , "OMFWifiInterface"]

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF Node

        """
        hostname = Attribute("hostname", "Hostname of the machine")
        cpu = Attribute("cpu", "CPU of the node")
        ram = Attribute("ram", "RAM of the node")
        xmppSlice = Attribute("xmppSlice","Name of the slice",
                flags = Flags.Credential)
        xmppHost = Attribute("xmppHost", "Xmpp Server",
                flags = Flags.Credential)
        xmppPort = Attribute("xmppPort", "Xmpp Port",
                flags = Flags.Credential)
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",
                flags = Flags.Credential)

        host = Attribute("host", "Hostname of the machine",
                flags = Flags.Filter)
        gateway = Attribute("gateway", "Gateway",
                flags = Flags.Filter)
        granularity = Attribute("granularity", "Granularity of the reservation time",
                flags = Flags.Filter)
        hardware_type = Attribute("hardware_type", "Hardware type of the machine",
                flags = Flags.Filter)

        cls._register_attribute(hostname)
        cls._register_attribute(ram)
        cls._register_attribute(cpu)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)

        cls._register_attribute(host)
        cls._register_attribute(gateway)
        cls._register_attribute(granularity)
        cls._register_attribute(hardware_type)

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

    def deploy(self):
        """Deploy the RM. It means : Send Xmpp Message Using OMF protocol to enroll the node into the experiment
           It becomes DEPLOYED after sending messages to enroll the node

        """ 
        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
               self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

        if self.get('hostname') :
            try:
                self._omf_api.enroll_host(self.get('hostname'))
            except AttributeError:
                self._state = ResourceState.FAILED
                msg = "Credentials are not initialzed. XMPP Connections impossible"
                self.debug(msg)
                return

        super(OMFNode, self).deploy()

    def discover(self):
        """ Discover the availables nodes

        """
        pass
     
    def provision(self):
        """ Provision some availables nodes

        """
        pass

     def start(self):
        """Start the RM. It means nothing special for an interface for now
           It becomes STARTED as soon as this method starts.

        """

        super(OMFNode, self).start()

    def stop(self):
        """Stop the RM. It means nothing special for an interface for now
           It becomes STOPPED as soon as this method stops

        """
        super(OMFNode, self).stop()

    def release(self):
        """Clean the RM at the end of the experiment

        """
        if self._omf_api :
            self._omf_api.release(self.get('hostname'))
            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

