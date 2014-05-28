#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2014 INRIA
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
from nepi.execution.resource import clsinit_copy, ResourceState, reschedule_delay
from nepi.resources.linux.ns3.ccn.ns3ccndceapplication import LinuxNS3CCNDceApplication

@clsinit_copy
class LinuxNS3DceFIBEntry(LinuxNS3CCNDceApplication):
    _rtype = "ns3::LinuxDceFIBEntry"

    @classmethod
    def _register_attributes(cls):
        uri = Attribute("uri",
                "URI prefix to match and route for this FIB entry",
                default = "ccnx:/",
                flags = Flags.Design)

        protocol = Attribute("protocol",
                "Transport protocol used in network connection to peer "
                "for this FIB entry. One of 'udp' or 'tcp'.",
                type = Types.Enumerate, 
                default = "udp",
                allowed = ["udp", "tcp"],
                flags = Flags.Design)

        host = Attribute("host",
                "Peer hostname used in network connection for this FIB entry. ",
                flags = Flags.Design)

        port = Attribute("port",
                "Peer port address used in network connection to peer "
                "for this FIB entry.",
                flags = Flags.Design)

        ip = Attribute("ip",
                "Peer host public IP used in network connection for this FIB entry. ",
                flags = Flags.Design)

        cls._register_attribute(uri)
        cls._register_attribute(protocol)
        cls._register_attribute(host)
        cls._register_attribute(port)
        cls._register_attribute(ip)

    def _instantiate_object(self):
        if not self.get("binary"):
            self.set("binary", "ccndc")
            
        if not self.get("arguments"):
            self.set("arguments", self._arguments)

        super(LinuxNS3DceFIBEntry, self)._instantiate_object()

    @property
    def _arguments(self):
        args = ["-v", "add"]

        if self.get("uri"):
            args.append(self.get("uri"))
        if self.get("protocol"):
            args.append(self.get("protocol"))
        if self.get("host"):
            args.append(self.get("host"))
        if self.get("port"):
            args.append(self.get("port"))
        if self.get("ip"):
            args.append(self.get("ip"))

        return ";".join(args) 


