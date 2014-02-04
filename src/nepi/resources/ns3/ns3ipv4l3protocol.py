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
        rms.add(self.node)
        return rms

    def _configure_object(self):
        simulator = self.simulator

        uuid_list_routing = simulator.create("Ipv4ListRouting")
        simulator.invoke(self.uuid, "SetRoutingProtocol", uuid_list_routing)

        uuid_static_routing = simulator.create("Ipv4StaticRouting")
        simulator.invoke(uuid_list_routing, "AddRoutingProtocol", uuid_static_routing, 1)

