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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import clsinit_copy, ResourceState, \
    ResourceAction, reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.ccn.ccnr import LinuxCCNR
from nepi.util.timefuncs import tnow

import os

@clsinit_copy
class LinuxCCNContent(LinuxApplication):
    _rtype = "LinuxCCNContent"

    @classmethod
    def _register_attributes(cls):
        content_name = Attribute("contentName",
                "The name of the content to publish (e.g. ccn:/VIDEO) ",
                flags = Flags.ExecReadOnly)

        content = Attribute("content",
                "The content to publish. It can be a path to a file or plain text ",
                flags = Flags.ExecReadOnly)

        cls._register_attribute(content_name)
        cls._register_attribute(content)

    def __init__(self, ec, guid):
        super(LinuxCCNContent, self).__init__(ec, guid)
        self._home = "content-%s" % self.guid
        
    @property
    def ccnr(self):
        ccnr = self.get_connected(LinuxCCNR.rtype())
        if ccnr: return ccnr[0]
        return None

    @property
    def ccnd(self):
        if self.ccnr: return self.ccnr.ccnd
        return None

    @property
    def node(self):
        if self.ccnr: return self.ccnr.node
        return None


    def deploy(self):
        if not self.ccnr or self.ccnr.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            
            # ccnr needs to wait until ccnd is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            command = self._start_command
            env = self._environment

            self.set("command", command)
            self.set("env", env)

            # set content to stdin, so the content will be
            # uploaded during provision
            self.set("stdin", self.get("content"))

            self.info("Deploying command '%s' " % command)

            # create run dir for application
            self.node.mkdir(self.run_home)

            # upload content 
            self.upload_stdin()

            # We want to make sure the content is published
            # before the experiment starts.
            # Run the command as a bash script in the background, 
            # in the host ( but wait until the command has
            # finished to continue )
            (out, err), proc = self.execute_command(command, env)

            if proc.poll():
                self._state = ResourceState.FAILED
                msg = "Failed to execute command"
                self.error(msg, out, err)
                raise RuntimeError, msg

            self.debug("----- READY ---- ")
            self._ready_time = tnow()
            self._state = ResourceState.READY

    def start(self):
        if self._state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            self._start_time = tnow()
            self._state = ResourceState.STARTED
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            self._state = ResourceState.FAILED
            raise RuntimeError, msg

    @property
    def state(self):
        return self._state

    @property
    def _start_command(self):
        return "ccnseqwriter -r %s < %s" % (self.get("contentName"),
                os.path.join(self.app_home, 'stdin'))

    @property
    def _environment(self):
        return self.ccnd.path
       
    def execute_command(self, command, env):
        environ = self.node.format_environment(env, inline = True)
        command = environ + command
        command = self.replace_paths(command)

        return self.node.execute(command)

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

