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
from nepi.execution.resource import clsinit_copy 
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow

import os

@clsinit_copy
class LinuxMtr(LinuxApplication):
    _rtype = "LinuxMtr"

    @classmethod
    def _register_attributes(cls):
        report_cycles = Attribute("reportCycles",
            "sets mtr --report-cycles (-c) option. Determines the number of "
            "pings sent to determine both machines in the networks. Each "
            "cycle lasts one sencond.",
            flags = Flags.ExecReadOnly)

        no_dns = Attribute("noDns",
            "sets mtr --no-dns (-n) option. Forces mtr to display IPs intead of "
            "trying to resolve to host names ",
            type = Types.Bool,
            default = True,
            flags = Flags.ExecReadOnly)

        address = Attribute("address",
            "sets mtr --address (-a) option. Binds the socket to send outgoing "
            "packets to the interface of the specified address, so that any "
            "any packets are sent through this interface. ",
            flags = Flags.ExecReadOnly)

        interval = Attribute("interval",
            "sets mtr --interval (-i) option. Specifies the number of seconds "
            "between ICMP ECHO requests. Default value is one second ",
            flags = Flags.ExecReadOnly)

        target = Attribute("target",
            "mtr target host (host that will be pinged)",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(report_cycles)
        cls._register_attribute(no_dns)
        cls._register_attribute(address)
        cls._register_attribute(interval)
        cls._register_attribute(target)

    def __init__(self, ec, guid):
        super(LinuxMtr, self).__init__(ec, guid)
        self._home = "mtr-%s" % self.guid

    def deploy(self):
        if not self.get("command"):
            self.set("command", self._start_command)

        if not self.get("depends"):
            self.set("depends", "mtr")

        super(LinuxMtr, self).deploy()

    @property
    def _start_command(self):
        args = []
        if self.get("reportCycles"):
            args.append("-c %s" % self.get("reportCycles"))
        if self.get("noDns") == True:
            args.append("-n")
        if self.get("address"):
            args.append("-a %s" % self.get("address"))
        args.append(self.get("target"))

        command = """echo "Starting mtr `date +'%Y%m%d%H%M%S'`"; """
        command += " sudo -S mtr --report "
        command += " ".join(args)

        return command

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

