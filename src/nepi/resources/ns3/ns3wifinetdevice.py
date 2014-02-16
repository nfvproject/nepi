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
from nepi.resources.ns3.ns3netdevice import NS3BaseNetDevice

WIFI_STANDARDS = dict({
    "WIFI_PHY_STANDARD_holland": 5,
    "WIFI_PHY_STANDARD_80211p_SCH": 7,
    "WIFI_PHY_STANDARD_80211_5Mhz": 4,
    "WIFI_PHY_UNKNOWN": 8,
    "WIFI_PHY_STANDARD_80211_10Mhz": 3,
    "WIFI_PHY_STANDARD_80211g": 2,
    "WIFI_PHY_STANDARD_80211p_CCH": 6,
    "WIFI_PHY_STANDARD_80211a": 0,
    "WIFI_PHY_STANDARD_80211b": 1
})

@clsinit_copy
class NS3BaseWifiNetDevice(NS3BaseNetDevice):
    _rtype = "abstract::ns3::WifiNetDevice"

    @property
    def _rms_to_wait(self):
        rms = set()
        
        node = self.node
        rms.add(node)

        ipv4 = node.ipv4
        if node.ipv4:
            rms.add(ipv4)

        return rms

    def _configure_mac_address(self):
        # The wifimac is the one responsible for
        # configuring the MAC address
        pass

    def _connect_object(self):
        node = self.node
        if node and node.uuid not in self.connected:
            self.simulation.invoke(node.uuid, "AddDevice", self.uuid)
            self._connected.add(node.uuid)

