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

from nepi.execution.resource import clsinit_copy
from nepi.resources.ns3.ns3base import NS3Base

@clsinit_copy
class NS3BaseNode(NS3Base):
    _rtype = "abstract::ns3::Node"

    @property
    def ipv4(self):
        from nepi.resources.ns3.ns3ipv4l3protocol import NS3BaseIpv4L3Protocol
        ipv4s = self.get_connected(NS3BaseIpv4L3Protocol.get_rtype())
        if ipv4s: return ipv4s[0]
        return None

    @property
    def others_to_wait(self):
        return set()

    def _configure_object(self):
        ### node.AggregateObject(PacketSocketFactory())
        uuid_packet_socket_factory = self.simulator.create("PacketSocketFactory")
        self.simulator.invoke(self.uuid, "AggregateObject", uuid_packet_socket_factory)

