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
from nepi.resources.ns3.ns3wifiphy import NS3BaseWifiPhy

@clsinit_copy
class NS3BaseErrorRateModel(NS3Base):
    _rtype = "abstract::ns3::ErrorRateModel"

    @property
    def phy(self):
        phys = self.get_connected(NS3BaseWifiPhy.get_rtype())
        if phys: return phys[0]
        return None

    @property
    def others_to_wait(self):
        others = set()
        phy = self.phy
        if phy: others.add(phy)
        return others

    def _connect_object(self):
        phy = self.phy
        if phy and phy.uuid not in self.connected:
            self.simulator.invoke(phy.uuid, "SetErrorRateModel", self.uuid)
            self._connected.add(phy.uuid)

