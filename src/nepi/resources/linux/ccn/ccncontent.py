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
                flags = Flags.Design)

        content = Attribute("content",
                "The content to publish. It can be a path to a file or plain text ",
                flags = Flags.Design)

        scope = Attribute("scope",
                "Use the given scope on the start-write request (if -r specified). "
                "scope can be 1 (local), 2 (neighborhood), or 3 (unlimited). "
                "Note that a scope of 3 is encoded as the absence of any scope in the interest. ",
                type = Types.Integer,
                default = 1,
                flags = Flags.Design)

        cls._register_attribute(content_name)
        cls._register_attribute(content)
        cls._register_attribute(scope)

    def __init__(self, ec, guid):
        super(LinuxCCNContent, self).__init__(ec, guid)
        self._home = "content-%s" % self.guid
        
    @property
    def ccnr(self):
        ccnr = self.get_connected(LinuxCCNR.get_rtype())
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

    def do_deploy(self):
        if not self.ccnr or self.ccnr.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            
            # ccnr needs to wait until ccnd is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("command"):
                self.set("command", self._start_command)

            if not self.get("env"):
                self.set("env", self._environment)

            # set content to stdin, so the content will be
            # uploaded during provision
            self.set("stdin", self.get("content"))

            command = self.get("command")

            self.info("Deploying command '%s' " % command)

            self.do_discover()
            self.do_provision()

            self.debug("----- READY ---- ")
            self.set_ready()

    def upload_start_command(self):
        command = self.get("command")
        env = self.get("env")

        self.info("Uploading command '%s'" % command)

        # We want to make sure the content is published
        # before the experiment starts.
        # Run the command as a bash script in the background, 
        # in the host ( but wait until the command has
        # finished to continue )
        env = self.replace_paths(env)
        command = self.replace_paths(command)

        (out, err), proc = self.execute_command(command, 
                env, blocking = True)

        if proc.poll():
            msg = "Failed to execute command"
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            raise RuntimeError, msg

    @property
    def _start_command(self):
        command = ["ccnseqwriter"]
        command.append("-r %s" % self.get("contentName"))
        command.append("-s %d" % self.get("scope"))
        command.append("< %s" % os.path.join(self.app_home, 'stdin'))

        command = " ".join(command)
        return command

    @property
    def _environment(self):
        return self.ccnd.path
       
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

