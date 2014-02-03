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
from nepi.execution.resource import clsinit_copy, failtrap 
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow

import os
import socket

@clsinit_copy
class LinuxTraceroute(LinuxApplication):
    _rtype = "LinuxTraceroute"

    @classmethod
    def _register_attributes(cls):
        countinuous = Attribute("continuous",
            "Run traceroute in a while loop",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        print_timestamp = Attribute("printTimestamp",
            "Print timestamp before running traceroute",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        use_ip = Attribute("useIP",
            "Use the IP address instead of the host domain name. "
            "Useful for environments were dns resolution problems occur "
            "frequently",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        target = Attribute("target",
            "Traceroute target host (host that will be pinged)",
            flags = Flags.Design)

        cls._register_attribute(countinuous)
        cls._register_attribute(print_timestamp)
        cls._register_attribute(use_ip)
        cls._register_attribute(target)

    def __init__(self, ec, guid):
        super(LinuxTraceroute, self).__init__(ec, guid)
        self._home = "traceroute-%s" % self.guid

    @failtrap
    def deploy(self):
        if not self.get("command"):
            self.set("command", self._start_command)

        if not self.get("depends"):
            self.set("depends", "traceroute")

        super(LinuxTraceroute, self).deploy()

    @property
    def _start_command(self):
        args = []
        if self.get("continuous") == True:
            args.append("while true; do ")
        if self.get("printTimestamp") == True:
            args.append("""echo "`date +'%Y%m%d%H%M%S'`";""")
        args.append("traceroute")

        target = self.get("target")
        if self.get("useIP") == True:
            target = socket.gethostbyname(target)
        args.append(target)
        
        if self.get("continuous") == True:
            args.append("; sleep 2 ; done ")

        command = " ".join(args)

        return command

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

