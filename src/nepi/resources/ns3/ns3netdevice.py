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
from nepi.resources.ns3.ns3base import NS3Base

import ipaddr

@clsinit_copy
class NS3BaseNetDevice(NS3Base):
    _rtype = "abstract::ns3::NetDevice"

    @classmethod
    def _register_attributes(cls):
        mac = Attribute("mac", "MAC address for device",
                flags = Flags.Design)

        ip = Attribute("ip", "IP address for device",
                flags = Flags.Design)

        prefix = Attribute("prefix", "Network prefix for device",
                flags = Flags.Design)

        cls._register_attribute(mac)
        cls._register_attribute(ip)
        cls._register_attribute(prefix)

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
    def channel(self):
        from nepi.resources.ns3.ns3channel import NS3BaseChannel
        channels = self.get_connected(NS3BaseChannel.get_rtype())

        if not channels: 
            msg = "Device not connected to channel"
            self.error(msg)
            raise RuntimeError, msg

        return channels[0]

    @property
    def _rms_to_wait(self):
        others = set()
        
        node = self.node
        others.add(node)

        ipv4 = node.ipv4
        if node.ipv4:
            others.add(ipv4)

        others.add(self.channel)
        return others

    def _configure_object(self):
        # Set Mac
        mac = self.get("mac")
        if mac:
            mac_uuid = self.simulation.create("Mac48Address", mac)
        else:
            mac_uuid = self.simulation.invoke("singleton::Mac48Address", "Allocate")
        self.simulation.invoke(self.uuid, "SetAddress", mac_uuid)

        # Set IP address
        ip = self.get("ip")
        prefix = self.get("prefix")

        i = ipaddr.IPAddress(ip)
        if i.version == 4:
            # IPv4
            ipv4 = self.node.ipv4
            ifindex_uuid = self.simulation.invoke(ipv4.uuid, "AddInterface", 
                    self.uuid)
            ipv4_addr_uuid = self.simulation.create("Ipv4Address", ip)
            ipv4_mask_uuid = self.simulation.create("Ipv4Mask", "/%s" % str(prefix))
            inaddr_uuid = self.simulation.create("Ipv4InterfaceAddress", 
                    ipv4_addr_uuid, ipv4_mask_uuid)
            self.simulation.invoke(ipv4.uuid, "AddAddress", ifindex_uuid, 
                    inaddr_uuid)
            self.simulation.invoke(ipv4.uuid, "SetMetric", ifindex_uuid, 1)
            self.simulation.invoke(ipv4.uuid, "SetUp", ifindex_uuid)
        else:
            # IPv6
            # TODO!
            pass

    def _connect_object(self):
        node = self.node
        if node and node.uuid not in self.connected:
            self.simulation.invoke(node.uuid, "AddDevice", self.uuid)
            self._connected.add(node.uuid)

        channel = self.channel
        if channel and channel.uuid not in self.connected:
            self.simulation.invoke(self.uuid, "Attach", channel.uuid)
            self._connected.add(channel.uuid)

