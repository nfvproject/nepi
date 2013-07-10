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
class OMFApplication(ResourceManager):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient)
        :type creds: dict

    .. note::

       This class is used only by the Experiment Controller through the Resource Factory

    """
    _rtype = "OMFApplication"
    _authorized_connections = ["OMFNode"]

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF application
        """

        appid = Attribute("appid", "Name of the application")
        path = Attribute("path", "Path of the application")
        args = Attribute("args", "Argument of the application")
        env = Attribute("env", "Environnement variable of the application")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = Flags.Credential)
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = Flags.Credential)
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = Flags.Credential)
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = Flags.Credential)
        cls._register_attribute(appid)
        cls._register_attribute(path)
        cls._register_attribute(args)
        cls._register_attribute(env)
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
        
        super(OMFApplication, self).__init__(ec, guid)

        self.set('appid', "")
        self.set('path', "")
        self.set('args', "")
        self.set('env', "")

        self._node = None

        self._omf_api = None

    def valid_connection(self, guid):
        """Check if the connection with the guid in parameter is possible. Only meaningful connections are allowed.

        :param guid: Guid of RM it will be connected
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.rtype() not in self._authorized_connections:
            msg = "Connection between %s %s and %s %s refused : An Application can be connected only to a Node" %\
                (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)
            return False
        elif len(self.connections) != 0 :
            msg = "Connection between %s %s and %s %s refused : This Application is already connected" % \
                (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)
            return False
        else :
            msg = "Connection between %s %s and %s %s accepted" % (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)
            return True

    def deploy(self):
        """Deploy the RM. It means nothing special for an application for now (later it will be upload sources, ...)
           It becomes DEPLOYED after getting the xmpp client.
        """
        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))
        
        super(OMFApplication, self).deploy()

    def start(self):
        """Start the RM. It means : Send Xmpp Message Using OMF protocol to execute the application
           It becomes STARTED before the messages are sent (for coordination)

        """
        super(OMFApplication, self).start()
        if self.get('appid') and self.get('path') and self.get('args') and self.get('env') :
            msg = " " + self.rtype() + " ( Guid : " + str(self._guid) +") : " + \
                self.get('appid') + " : " + self.get('path') + " : " + \
                self.get('args') + " : " + self.get('env')
            self.info(msg)
            rm_list = self.get_connected(OMFNode.rtype())
            try:
                for rm_node in rm_list:
                    if rm_node.get('hostname') :
                        self._omf_api.execute(rm_node.get('hostname'),self.get('appid'), \
                            self.get('args'), self.get('path'), self.get('env'))
            except AttributeError:
                self._state = ResourceState.FAILED
                msg = "Credentials are not initialzed. XMPP Connections impossible"
                self.error(msg)
                raise
        else :
            self._state = ResourceState.FAILED
            msg = "Application's information are not initialized"
            self.error(msg)

    def stop(self):
        """Stop the RM. It means : Send Xmpp Message Using OMF protocol to kill the application
           It becomes STOPPED after the message is sent.

        """
        try:
            rm_list = self.get_connected("OMFNode")
            for rm_node in rm_list :
                self._omf_api.exit(rm_node.get('hostname'),self.get('appid'))
        except AttributeError:
            self._state = ResourceState.FAILED
            msg = "Credentials were not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise
        super(OMFApplication, self).stop()
        self._state = ResourceState.FINISHED
        

    def release(self):
        """Clean the RM at the end of the experiment and release the API.

        """
        if self._omf_api :
            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

