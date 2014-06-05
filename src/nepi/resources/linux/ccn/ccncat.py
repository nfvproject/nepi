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
    reschedule_delay
from nepi.resources.linux.ccn.ccnapplication import LinuxCCNApplication

import os

@clsinit_copy
class LinuxCCNCat(LinuxCCNApplication):
    _rtype = "LinuxCCNCat"

    @classmethod
    def _register_attributes(cls):
        content_name = Attribute("contentName",
            "Content name for the content to peek",
            flags = Flags.Design)

        pipeline = Attribute("pipeline",
            "CCNCat pipeline",
            flags = Flags.Design)

        cls._register_attribute(content_name)
        cls._register_attribute(pipeline)

    def __init__(self, ec, guid):
        super(LinuxCCNCat, self).__init__(ec, guid)
        self._home = "ccncat-%s" % self.guid

    def do_deploy(self):
        if not self.ccnd or self.ccnd.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            command = self.get("command")
            if not command:
                command = "ccncat %s" % self.get("contentName")
            if self.get("pipeline"):
                command += " -p %s " % self.get("pipeline")

            self.set("command", command) 

            self.info("Deploying command '%s' " % command)
            
            if not self.get("env"):
                self.set("env", self._environment)

            self.do_discover()
            self.do_provision()

            self.set_ready()

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

