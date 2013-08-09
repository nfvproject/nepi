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
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState, \
    reschedule_delay
from nepi.resources.linux.ccn.ccnpingserver import LinuxCCNPingServer
from nepi.util.timefuncs import tnow, tdiffsec

import os

@clsinit_copy
class LinuxCCNPing(LinuxCCNPingServer):
    _rtype = "LinuxCCNPing"

    @classmethod
    def _register_attributes(cls):
        interval = Attribute("i",
            "Set ping interval in seconds (minimum 0.10 second) ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        count = Attribute("c",
            "Total number of pings",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        number = Attribute("n",
            "Set the starting number, the number is incremented by 1 after each Interest ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)
 
        prefix = Attribute("prefix",
            "Prefix to serve content (e.g. ccnx:/name/prefix)",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(interval)
        cls._register_attribute(count)
        cls._register_attribute(number)
        cls._register_attribute(prefix)

    def __init__(self, ec, guid):
        super(LinuxCCNPing, self).__init__(ec, guid)
        self._home = "ccnping-%s" % self.guid

    @property
    def ccnpingserver(self):
        ccnpingserver = self.get_connected(LinuxCCNPingServer.rtype())
        if ccnpingserver: return ccnpingserver[0]
        return None

    def start(self):
        if not self.ccnpingserver or \
                self.ccnpingserver.state < ResourceState.STARTED:
            self.debug("---- RESCHEDULING START----  ccnpingserver state %s " % \
                    self.ccnpingserver.state )
            self.ec.schedule(reschedule_delay, self.start)
        else:
            super(LinuxCCNPing, self).start()
 
    @property
    def _start_command(self):
        args = []
        args.append("ccnping")
        args.append(self.get("prefix"))
        if self.get("c"):
            args.append("-c %d" % self.get("c"))
        if self.get("n"):
            args.append("-n %d" % self.get("n"))
        if self.get("i"):
            args.append("-i %d" % self.get("i"))

        command = " ".join(args)

        return command

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

