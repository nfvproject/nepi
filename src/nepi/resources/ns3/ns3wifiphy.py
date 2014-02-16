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
from nepi.resources.ns3.ns3wifinetdevice import WIFI_STANDARDS

@clsinit_copy
class NS3BaseWifiPhy(NS3Base):
    _rtype = "abstract::ns3::WifiPhy"

    @classmethod
    def _register_attributes(cls):
        standard = Attribute("Standard", "Wireless standard",
                default = "WIFI_PHY_STANDARD_80211a",
                allowed = WIFI_STANDARDS.keys(),
                type = Types.Enumerate,
                flags = Flags.Design)

        cls._register_attribute(standard)

    @property
    def node(self):
        return self.device.node

    @property
    def device(self):
        from nepi.resources.ns3.ns3wifinetdevice import NS3BaseWifiNetDevice
        devices = self.get_connected(NS3BaseWifiNetDevice.get_rtype())

        if not devices: 
            msg = "WifiPhy not connected to device"
            self.error(msg)
            raise RuntimeError, msg

        return devices[0]

    @property
    def channel(self):
        from nepi.resources.ns3.ns3wifichannel import NS3BaseWifiChannel
        channels = self.get_connected(NS3BaseWifiChannel.get_rtype())

        if not channels: 
            msg = "WifiPhy not connected to channel"
            self.error(msg)
            raise RuntimeError, msg

        return channels[0]

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.device)
        return rms

    def _connect_object(self):
        device = self.device
        if device.uuid not in self.connected:
            self._connected.add(device.uuid)

            self.simulation.invoke(self.uuid, "SetMobility", self.node.uuid)

            standard = self.get("Standard")
            self.simulation.invoke(self.uuid, "ConfigureStandard", WIFI_STANDARDS[standard])

            self.simulation.invoke(self.uuid, "SetDevice", device.uuid)

            self.simulation.invoke(self.uuid, "SetChannel", self.channel.uuid)
            
            self.simulation.invoke(device.uuid, "SetPhy", self.uuid)

