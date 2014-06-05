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

import os

from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.execution.attribute import Attribute, Flags 
from nepi.resources.omf.omf_resource import ResourceGateway, OMFResource
from nepi.resources.omf.node import OMFNode, confirmation_counter, reschedule_check
from nepi.resources.omf.omf_api_factory import OMFAPIFactory

from nepi.util import sshfuncs

@clsinit_copy
class OMFApplication(OMFResource):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    """
    _rtype = "OMFApplication"
    _authorized_connections = ["OMFNode"]

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of an OMF application

        """
        command = Attribute("command", "Command to execute")
        env = Attribute("env", "Environnement variable of the application")

        # For OMF 5:
        appid = Attribute("appid", "Name of the application")
        stdin = Attribute("stdin", "Input of the application", default = "")
        sources = Attribute("sources", "Sources of the application", 
                     flags = Flags.ExecReadOnly)
        sshuser = Attribute("sshUser", "user to connect with ssh", 
                     flags = Flags.ExecReadOnly)
        sshkey = Attribute("sshKey", "key to use for ssh", 
                     flags = Flags.ExecReadOnly)

        cls._register_attribute(appid)
        cls._register_attribute(command)
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

        self.set('command', "")
        self.set('appid', "")
        self._path= ""
        self._args = ""
        self.set('env', "")

        self._node = None

        self._omf_api = None
        self._topic_app = None
        self.create_id = None
        self._create_cnt = 0
        self._start_cnt = 0
        self.release_id = None
        self._release_cnt = 0

        self.add_set_hook()

    def _init_command(self):
        comm = self.get('command').split(' ')
        self._path= comm[0]
        if len(comm)>1:
            self._args = ' '.join(comm[1:])

    @property
    def exp_id(self):
        return self.ec.exp_id

    @property
    def node(self):
        rm_list = self.get_connected(OMFNode.get_rtype())
        if rm_list: return rm_list[0]
        return None

    def stdin_hook(self, old_value, new_value):
        """ Set a hook to the stdin attribute in order to send a message at each time
        the value of this parameter is changed. Used ofr OMF 5.4 only

        """
        self._omf_api.send_stdin(self.node.get('hostname'), new_value, self.get('appid'))
        return new_value

    def add_set_hook(self):
        """ Initialize the hooks for OMF 5.4 only

        """
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
        It becomes DEPLOYED after the topic for the application has been created

        """
        if not self.node or self.node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s "
                       % self.node.state )
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self._init_command()

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

        if not self.get('command') :
            msg = "Application's Command is not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if not self._omf_api :
            self._omf_api = OMFAPIFactory.get_api(self.get('version'), 
              self.get('xmppServer'), self.get('xmppUser'), self.get('xmppPort'),
               self.get('xmppPassword'), exp_id = self.exp_id)

        if self.get('version') == "5":
            if self.get('sources'):
                gateway = ResourceGateway.AMtoGateway[self.get('xmppServer')]
                user = self.get('sshUser') or self.get('xmppUser')
                dst = user + "@"+ gateway + ":"
                (out, err), proc = sshfuncs.rcopy(self.get('sources'), dst)
        else :
            # For OMF 6 :
            if not self.create_id:
                props = {}
                if self.get('command'):
                    props['application:binary_path'] = self.get('command')
                    props['application:hrn'] = self.get('command')
                    props['application:membership'] = self._topic_app
                props['application:type'] = "application"
    
                self.create_id = os.urandom(16).encode('hex')
                self._omf_api.frcp_create( self.create_id, self.node.get('hostname'), "application", props = props)
   
            if self._create_cnt > confirmation_counter:
                msg = "Couldn't retrieve the confirmation of the creation"
                self.error(msg)
                raise RuntimeError, msg

            uid = self.check_deploy(self.create_id)
            if not uid:
                self._create_cnt +=1
                self.ec.schedule(reschedule_check, self.deploy)
                return

            self._topic_app = uid
            self._omf_api.enroll_topic(self._topic_app)

        super(OMFApplication, self).do_deploy()

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

    def do_start(self):
        """ Start the RM. It means : Send Xmpp Message Using OMF protocol 
         to execute the application. 

        """

        if not self.get('env'):
            self.set('env', " ")

        if self.get('version') == "5":
            # Some information to check the command for OMF5
            msg = " " + self.get_rtype() + " ( Guid : " + str(self._guid) +") : " + \
                self.get('appid') + " : " + self._path + " : " + \
                self._args + " : " + self.get('env')
            self.debug(msg)

            self._omf_api.execute(self.node.get('hostname'),self.get('appid'), \
                self._args, self._path, self.get('env'))
        else:
            #For OMF 6
            if self._start_cnt == 0:
                props = {}
                props['state'] = "running"
    
                guards = {}
                guards['type'] = "application"
                guards['name'] = self.get('command')

                self._omf_api.frcp_configure(self._topic_app, props = props, guards = guards )

            if self._start_cnt > confirmation_counter:
                msg = "Couldn't retrieve the confirmation that the application started"
                self.error(msg)
                raise RuntimeError, msg

            res = self.check_start(self._topic_app)
            if not res:
                self._start_cnt +=1
                self.ec.schedule(reschedule_check, self.start)
                return

        super(OMFApplication, self).do_start()

    def check_start(self, uid):
        """ Check, through the mail box in the parser, 
        if the confirmation of the start has been received

        :param uid: the id of the original message
        :type guid: string

        """
        res = self._omf_api.check_mailbox("started", uid)
        if res : 
            return True
        return False

    def do_stop(self):
        """ Stop the RM. It means : Send Xmpp Message Using OMF protocol to 
        kill the application. 
        State is set to STOPPED after the message is sent.

        """
        if self.get('version') == 5:
            self._omf_api.exit(self.node.get('hostname'),self.get('appid'))
        super(OMFApplication, self).do_stop()

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
        """ Clean the RM at the end of the experiment and release the API.

        """
        if self._omf_api:
            if self.get('version') == "6":
                if not self.release_id:
                    self.release_id = os.urandom(16).encode('hex')
                    self._omf_api.frcp_release( self.release_id, self.node.get('hostname'),self._topic_app, res_id=self._topic_app)
    
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

        super(OMFApplication, self).do_release()

