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

from nepi.execution.attribute import Attribute, Flags
from nepi.execution.resource import clsinit_copy
from nepi.execution.trace import Trace
from nepi.resources.ns3.ns3base import NS3Base

import ipaddr

@clsinit_copy
class NS3Route(NS3Base):
    _rtype = "ns3::Route"

    @classmethod
    def _register_attributes(cls):
        network = Attribute("network", "Destination network address",
                flags = Flags.Design)

        prefix = Attribute("prefix", "Network prefix for the network",
                flags = Flags.Design)

        nexthop = Attribute("nexthop", "Address of next hop in the route",
                flags = Flags.Design)

        cls._register_attribute(network)
        cls._register_attribute(prefix)
        cls._register_attribute(nexthop)

    def __init__(self, ec, guid):
        super(NS3Route, self).__init__(ec, guid)

    @property
    def node(self):
        from nepi.resources.ns3.ns3node import NS3BaseNode
        nodes = self.get_connected(NS3BaseNode.get_rtype())

        if not nodes: 
            msg = "Device not connected to node"
            self.error(msg)
            raise RuntimeError, msg

        return nodes[0]

    @property
    def _rms_to_wait(self):
        # Wait for all network devices connected to the node to be ready
        # before configuring the routes, else the route might refer to a
        # non yet existing interface

        rms = set()
        rms.update(self.node.devices)
        return rms

    def _instantiate_object(self):
        pass

    def _configure_object(self):
        network = self.get("network")
        prefix = self.get("prefix")
        nexthop = self.get("nexthop")
        ipv4_uuid = self.node.ipv4.uuid

        ret = self.simulation.invoke(ipv4_uuid, "addStaticRoute", network, 
            prefix, nexthop)

        if not ret: 
            msg = "Could not configure route %s/%s hop: %s" % (network, prefix, 
                    nexthop)
            self.error(msg)
            raise RuntimeError, msg

    def _connect_object(self):
        node = self.node
        if node and node.uuid not in self.connected:
            self._connected.add(node.uuid)

