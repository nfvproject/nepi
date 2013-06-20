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
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState, \
    ResourceAction
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.ccn.ccnr import LinuxCCNR
from nepi.util.timefuncs import strfnow, strfdiff

import os

reschedule_delay = "0.5s"

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
        self._published = False
        
    @property
    def ccnr(self):
        ccnr = self.get_connected(LinuxCCNR.rtype())
        if ccnr: return ccnr[0]
        return None

    @property
    def node(self):
        if self.ccnr: return self.ccnr.node
        return None

    def deploy(self):
        if not self.get("command"):
            self.set("command", self._default_command)
        
        if not self.get("env"):
            self.set("env", self._default_environment)

        if not self.get("stdin"):
            # set content to stdin, so the content will be
            # uploaded during provision
            self.set("stdin", self.get("content"))

        # Wait until associated ccnd is provisioned
        ccnr = self.ccnr

        if not ccnr or ccnr.state < ResourceState.READY:
            # ccnr needs to wait until ccnd is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            # Invoke the actual deployment
            super(LinuxCCNContent, self).deploy()

            # As soon as the ccnr is running we can push the content
            # to the repository ( we don't want to lose time launching 
            # writting the content to the repository later on )
            if self._state == ResourceState.READY:
                self._start_in_background()
                self._published = True

    def start(self):
        # CCNR should already be started by now.
        # Nothing to do but to set the state to STARTED
        if self._published:
            self._start_time = strfnow()
            self._state = ResourceState.STARTED
        else:
            msg = "Failed to execute command '%s'" % command
            self.error(msg, out, err)
            self._state = ResourceState.FAILED
            raise RuntimeError, msg

    @property
    def state(self):
        state = super(LinuxCCNContent, self).state
        if self._state in [ResourceState.FINISHED, ResourceState.FAILED]:
            self._published = False

        if self._state == ResourceState.READY:
            # CCND is really deployed only when ccn daemon is running 
            if not self._published:
                return ResourceState.PROVISIONED
 
        return self._state

    @property
    def _default_command(self):
        return "ccnseqwriter -r %s " % self.get("contentName")

    @property
    def _default_environment(self):
        env = "PATH=$PATH:${EXP_HOME}/ccnx/bin "
        return env            
        
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

