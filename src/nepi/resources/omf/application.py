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
from nepi.resources.omf.node import OMFNode
from nepi.resources.omf.omf_api import OMFAPIFactory

from nepi.util import sshfuncs

@clsinit_copy
class OMFApplication(OMFResource):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient)
        :type creds: dict

    .. note::

       This class is used only by the Experiment Controller through the 
       Resource Factory

    """
    _rtype = "OMFApplication"
    _authorized_connections = ["OMFNode"]

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of an OMF application

        """
        appid = Attribute("appid", "Name of the application")
        path = Attribute("path", "Path of the application")
        args = Attribute("args", "Argument of the application")
        env = Attribute("env", "Environnement variable of the application")
        stdin = Attribute("stdin", "Input of the application", default = "")
        sources = Attribute("sources", "Sources of the application", 
                     flags = Flags.ExecReadOnly)
        sshuser = Attribute("sshUser", "user to connect with ssh", 
                     flags = Flags.ExecReadOnly)
        sshkey = Attribute("sshKey", "key to use for ssh", 
                     flags = Flags.ExecReadOnly)
        cls._register_attribute(appid)
        cls._register_attribute(path)
        cls._register_attribute(args)
        cls._register_attribute(env)
        cls._register_attribute(stdin)
        cls._register_attribute(sources)
        cls._register_attribute(sshuser)
        cls._register_attribute(sshkey)

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

        self.add_set_hook()

    @property
    def exp_id(self):
        return self.ec.exp_id

    @property
    def node(self):
        rm_list = self.get_connected(OMFNode.rtype())
        if rm_list: return rm_list[0]
        return None

    def stdin_hook(self, old_value, new_value):
        self._omf_api.send_stdin(self.node.get('hostname'), new_value, self.get('appid'))
        return new_value

    def add_set_hook(self):
        attr = self._attrs["stdin"]
        attr.set_hook = self.stdin_hook

    def valid_connection(self, guid):
        """ Check if the connection with the guid in parameter is possible. 
        Only meaningful connections are allowed.

        :param guid: Guid of RM it will be connected
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.rtype() not in self._authorized_connections:
            msg = ("Connection between %s %s and %s %s refused: "
                    "An Application can be connected only to a Node" ) % \
                (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)

            return False

        elif len(self.connections) != 0 :
            msg = ("Connection between %s %s and %s %s refused: "
                    "This Application is already connected" ) % \
                (self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)

            return False

        else :
            msg = "Connection between %s %s and %s %s accepted" % (
                    self.rtype(), self._guid, rm.rtype(), guid)
            self.debug(msg)

            return True

    def do_deploy(self):
        """ Deploy the RM. It means nothing special for an application 
        for now (later it will be upload sources, ...)
        It becomes DEPLOYED after getting the xmpp client.

        """
        self.set('xmppSlice',self.node.get('xmppSlice'))
        self.set('xmppHost',self.node.get('xmppHost'))
        self.set('xmppPort',self.node.get('xmppPort'))
        self.set('xmppPassword',self.node.get('xmppPassword'))

        if not (self.get('xmppSlice') and self.get('xmppHost')
              and self.get('xmppPort') and self.get('xmppPassword')):
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise RuntimeError, msg

        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        if self.get('sources'):
            gateway = ResourceGateway.AMtoGateway[self.get('xmppHost')]
            user = self.get('sshUser') or self.get('xmppSlice')
            dst = user + "@"+ gateway + ":"
            (out, err), proc = sshfuncs.rcopy(self.get('sources'), dst)

        super(OMFApplication, self).do_deploy()

    def do_start(self):
        """ Start the RM. It means : Send Xmpp Message Using OMF protocol 
         to execute the application. 
         It becomes STARTED before the messages are sent (for coordination)

        """
        if not (self.get('appid') and self.get('path')) :
            msg = "Application's information are not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if not self.get('args'):
            self.set('args', " ")
        if not self.get('env'):
            self.set('env', " ")

        # Some information to check the information in parameter
        msg = " " + self.rtype() + " ( Guid : " + str(self._guid) +") : " + \
            self.get('appid') + " : " + self.get('path') + " : " + \
            self.get('args') + " : " + self.get('env')
        self.info(msg)

        try:
            self._omf_api.execute(self.node.get('hostname'),self.get('appid'), \
                self.get('args'), self.get('path'), self.get('env'))
        except AttributeError:
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise

        super(OMFApplication, self).do_start()

    def do_stop(self):
        """ Stop the RM. It means : Send Xmpp Message Using OMF protocol to 
        kill the application. 
        State is set to STOPPED after the message is sent.

        """
        try:
            self._omf_api.exit(self.node.get('hostname'),self.get('appid'))
        except AttributeError:
            msg = "Credentials were not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise

        super(OMFApplication, self).do_stop()

    def do_release(self):
        """ Clean the RM at the end of the experiment and release the API.

        """
        if self._omf_api:
            OMFAPIFactory.release_api(self.get('xmppSlice'), 
                self.get('xmppHost'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMFApplication, self).do_release()

