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
class NS3BaseIpv4L3Protocol(NS3Base):
    _rtype = "abstract::ns3::Ipv4L3Protocol"

    def __init__(self, ec, guid):
        super(NS3BaseIpv4L3Protocol, self).__init__(ec, guid)
        self.list_routing_uuid = None
        self.static_routing_uuid = None
        self.global_routing_uuid = None

    @property
    def node(self):
        from nepi.resources.ns3.ns3node import NS3BaseNode
        nodes = self.get_connected(NS3BaseNode.get_rtype())

        if not nodes: 
            msg = "Ipv4L3Protocol not connected to node"
            self.error(msg)
            raise RuntimeError, msg

        return nodes[0]

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.simulation)
        return rms

    def _configure_object(self):
        simulation = self.simulation

        self.list_routing_uuid = simulation.create("Ipv4ListRouting")
        simulation.invoke(self.uuid, "SetRoutingProtocol", self.list_routing_uuid)

        self.static_routing_uuid = simulation.create("Ipv4StaticRouting")
        simulation.invoke(self.list_routing_uuid, "AddRoutingProtocol", 
                self.static_routing_uuid, 0)

        self.global_routing_uuid = simulation.create("Ipv4GlobalRouting")
        simulation.invoke(self.list_routing_uuid, "AddRoutingProtocol", 
                self.global_routing_uuid, -10)

    def _connect_object(self):
        pass
