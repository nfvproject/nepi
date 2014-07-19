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
from nepi.execution.resource import clsinit_copy
from nepi.resources.ns3.ns3base import NS3Base

@clsinit_copy
class NS3BaseNode(NS3Base):
    _rtype = "abstract::ns3::Node"

    @classmethod
    def _register_attributes(cls):
        enablestack = Attribute("enableStack", 
                "Install network stack in Node, including: ARP, "
                "IP4, ICMP, UDP and TCP ",
                type = Types.Bool,
                default = False,
                flags = Flags.Design)

        cls._register_attribute(enablestack)

    @property
    def simulation(self):
        from nepi.resources.ns3.ns3simulation import NS3Simulation
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if isinstance(rm, NS3Simulation):
                return rm

        msg = "Node not connected to simulation"
        self.error(msg)
        raise RuntimeError, msg
 
    @property
    def ipv4(self):
        from nepi.resources.ns3.ns3ipv4l3protocol import NS3BaseIpv4L3Protocol
        ipv4s = self.get_connected(NS3BaseIpv4L3Protocol.get_rtype())
        if ipv4s: return ipv4s[0]
        return None

    @property
    def arp(self):
        from nepi.resources.ns3.ns3arpl3protocol import NS3BaseArpL3Protocol
        arps = self.get_connected(NS3BaseArpL3Protocol.get_rtype())
        if arps: return arps[0]
        return None

    @property
    def mobility(self):
        from nepi.resources.ns3.ns3mobilitymodel import NS3BaseMobilityModel
        mobility = self.get_connected(NS3BaseMobilityModel.get_rtype())
        if mobility: return mobility[0]
        return None

    @property
    def devices(self):
        from nepi.resources.ns3.ns3netdevice import NS3BaseNetDevice
        devices = self.get_connected(NS3BaseNetDevice.get_rtype())

        if not devices: 
            msg = "Node not connected to devices"
            self.error(msg)
            raise RuntimeError, msg

        return devices

    @property
    def dceapplications(self):
        from nepi.resources.ns3.ns3dceapplication import NS3BaseDceApplication
        dceapplications = self.get_connected(NS3BaseDceApplication.get_rtype())

        return dceapplications

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.simulation)

        ipv4 = self.ipv4
        if ipv4:
            rms.add(ipv4)

        arp = self.arp
        if arp:
            rms.add(arp)

        mobility = self.mobility
        if mobility:
            rms.add(mobility)

        return rms

    def _configure_object(self):
        if self.get("enableStack"):
            uuid_stack_helper = self.simulation.create("InternetStackHelper")
            self.simulation.invoke(uuid_stack_helper, "Install", self.uuid)

            # Retrieve IPV4 object
            ipv4_uuid = self.simulation.invoke(self.uuid, "retrieveObject",
                    "ns3::Ipv4L3Protocol")
            
            # Add IPv4 RM to the node
            ipv4 = self.ec.register_resource("ns3::Ipv4L3Protocol")
            self.ec.register_connection(self.guid, ipv4)
            ipv4rm = self.ec.get_resource(ipv4)
            ipv4rm._uuid = ipv4_uuid
            ipv4rm.set_started()
        else:
            ### node.AggregateObject(PacketSocketFactory())
            uuid_packet_socket_factory = self.simulation.create("PacketSocketFactory")
            self.simulation.invoke(self.uuid, "AggregateObject", uuid_packet_socket_factory)

        dceapplications = self.dceapplications
        if dceapplications:
            self._add_dce(dceapplications)

    def _connect_object(self):
        if not self.get("enableStack"):
            ipv4 = self.ipv4
            if ipv4:
                self.simulation.invoke(self.uuid, "AggregateObject", ipv4.uuid)
                self._connected.add(ipv4.uuid)
                ipv4._connected.add(self.uuid)

            arp = self.arp
            if arp:
                self.simulation.invoke(self.uuid, "AggregateObject", arp.uuid)
                self._connected.add(arp.uuid)
                arp._connected.add(self.uuid)

        mobility = self.mobility
        if mobility:
            self.simulation.invoke(self.uuid, "AggregateObject", mobility.uuid)
            self._connected.add(mobility.uuid)
            mobility._connected.add(self.uuid)

    def _add_dce(self, dceapplications):
        dceapp = dceapplications[0]

        container_uuid = self.simulation.create("NodeContainer")
        self.simulation.invoke(container_uuid, "Add", self.uuid)
        with dceapp.dce_manager_lock:
            self.simulation.invoke(dceapp.dce_manager_helper_uuid, 
                    "Install", container_uuid)

