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
class NS3BaseIpV4Protocol(Ns3Base):
    _rtype = "ns3::IpV4Protocol"

    def do_provision(self):
        # create run dir for ns3 object
        # self.simulator.node.mkdir(self.run_home)
        
        self._instantiate_object()

        uuid_list_routing = simulator.create("Ipv4ListRouting")
        simulator.invoke(self.uuid, "SetRoutingProtocol", uuid_list_routing)

        uuid_static_routing = simulator.create("Ipv4StaticRouting")
        simulator.invoke(self.uuid, "SetRoutingProtocol", uuid_static_routing, 1)

        super(NS3BaseIpV4Protocol, self).do_provision()

