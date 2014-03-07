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
from nepi.resources.omf.omf6_resource import OMF6Resource
from nepi.resources.omf.node6 import OMF6Node
from nepi.resources.omf.omf6_api import OMF6APIFactory

import os, time
from nepi.util import sshfuncs

@clsinit_copy
class OMF6Application(OMF6Resource):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    """
    _rtype = "OMF6Application"
    _authorized_connections = ["OMF6Node"]

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of an OMF application

        """
        command = Attribute("command", "Command to execute")
        env = Attribute("env", "Environnement variable of the application")
#        sources = Attribute("sources", "Sources of the application", 
#                     flags = Flags.ExecReadOnly)
#        sshuser = Attribute("sshUser", "user to connect with ssh", 
#                     flags = Flags.ExecReadOnly)
#        sshkey = Attribute("sshKey", "key to use for ssh", 
#                     flags = Flags.ExecReadOnly)
        cls._register_attribute(command)
        cls._register_attribute(env)
#        cls._register_attribute(sources)
#        cls._register_attribute(sshuser)
#        cls._register_attribute(sshkey)

    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

        """
        super(OMF6Application, self).__init__(ec, guid)

        self.set('command', "")
        self.set('env', "")

        self._node = None
        self._topic_app = None

        self._omf_api = None

    @property
    def exp_id(self):
        return self.ec.exp_id

    @property
    def node(self):
        rm_list = self.get_connected(OMF6Node.get_rtype())
        if rm_list: return rm_list[0]
        return None

    def valid_connection(self, guid):
        """ Check if the connection with the guid in parameter is possible. 
        Only meaningful connections are allowed.

        :param guid: Guid of RM it will be connected
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.get_rtype() not in self._authorized_connections:
            msg = ("Connection between %s %s and %s %s refused: "
                    "An Application can be connected only to a Node" ) % \
                (self.get_rtype(), self._guid, rm.get_rtype(), guid)
            self.debug(msg)

            return False

        elif len(self.connections) != 0 :
            msg = ("Connection between %s %s and %s %s refused: "
                    "This Application is already connected" ) % \
                (self.get_rtype(), self._guid, rm.get_rtype(), guid)
            self.debug(msg)

            return False

        else :
            msg = "Connection between %s %s and %s %s accepted" % (
                    self.get_rtype(), self._guid, rm.get_rtype(), guid)
            self.debug(msg)

            return True

    def do_deploy(self):
        """ Deploy the RM. It means nothing special for an application 
        for now (later it will be upload sources, ...)
        It becomes DEPLOYED after getting the xmpp client.

        """

        self.set('xmppUser',self.node.get('xmppUser'))
        self.set('xmppHost',self.node.get('xmppHost'))
        self.set('xmppPort',self.node.get('xmppPort'))
        self.set('xmppPassword',self.node.get('xmppPassword'))

        if not (self.get('xmppUser') and self.get('xmppHost')
              and self.get('xmppPort') and self.get('xmppPassword')):
            msg = "Credentials are not initialzed. XMPP Connections impossible"
            self.error(msg)
            raise RuntimeError, msg

        if not self._omf_api :
            self._omf_api = OMF6APIFactory.get_api(self.get('xmppHost'), 
                self.get('xmppUser'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

#        if self.get('sources'):
#            gateway = ResourceGateway.AMtoGateway[self.get('xmppHost')]
#            user = self.get('sshUser') or self.get('xmppSlice')
#            dst = user + "@"+ gateway + ":"
#            (out, err), proc = sshfuncs.rcopy(self.get('sources'), dst)
         
        self._topic_app = self.node.get('hostname') +'_'+ str(self.guid) +'_app'

        self._omf_api.enroll_topic(self._topic_app)

        props = {}
        if self.get('command'):
            props['application:binary_path'] = self.get('command')
            props['application:hrn'] = self.get('command')
            props['application:membership'] = self._topic_app
        props['application:type'] = "application"
        self._omf_api.frcp_create( self.node.get('hostname'), "application", props = props)



        super(OMF6Application, self).do_deploy()

    def do_start(self):
        """ Start the RM. It means : Send Xmpp Message Using OMF protocol 
         to execute the application. 
         It becomes STARTED before the messages are sent (for coordination)

        """
        if not self.get('command') :
            msg = "Application's Command is not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if not self.get('env'):
            self.set('env', " ")

        props = {}
        props['state'] = "running"

        guards = {}
        guards['type'] = "application"
        guards['name'] = self.get('command')
        time.sleep(2)
        self._omf_api.frcp_configure(self._topic_app, props = props, guards = guards )


        super(OMF6Application, self).do_start()

    def do_stop(self):
        """ Stop the RM. It means : Send Xmpp Message Using OMF protocol to 
        kill the application. 
        State is set to STOPPED after the message is sent.

        """

        super(OMF6Application, self).do_stop()

    def do_release(self):
        """ Clean the RM at the end of the experiment and release the API.

        """
        props = {}
        props['frcp:type'] = "application"

        self._omf_api.frcp_release(self.node.get('hostname'),self._topic_app, props = props )

        if self._omf_api:
            OMF6APIFactory.release_api(self.get('xmppHost'), 
                self.get('xmppUser'), self.get('xmppPort'), 
                self.get('xmppPassword'), exp_id = self.exp_id)

        super(OMF6Application, self).do_release()

