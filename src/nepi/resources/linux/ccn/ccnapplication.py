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

from nepi.execution.resource import clsinit_copy, ResourceState, \
    ResourceAction
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.ccn.ccnd import LinuxCCND

import os

@clsinit_copy
class LinuxCCNApplication(LinuxApplication):
    _rtype = "LinuxCCNApplication"

    def __init__(self, ec, guid):
        super(LinuxCCNApplication, self).__init__(ec, guid)
        self._home = "ccnapp-%s" % self.guid

    @property
    def ccnd(self):
        ccnd = self.get_connected(LinuxCCND.rtype())
        if ccnd: return ccnd[0]
        return None

    @property
    def node(self):
        if self.ccnd: return self.ccnd.node
        return None

    def deploy(self):
        if not self.get("env"):
            self.set("env", self._environment)

        super(LinuxCCNApplication, self).deploy()

    @property
    def _environment(self):
        env = "PATH=$PATH:${EXP_HOME}/ccnx/bin "
        return env            
       
    def execute_command(self, command, env):
        environ = self.node.format_environment(env, inline = True)
        command = environ + command
        command = self.replace_paths(command)

        (out, err), proc = self.node.execute(command)

        if proc.poll():
            self._state = ResourceState.FAILED
            self.error(msg, out, err)
            raise RuntimeError, msg

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

