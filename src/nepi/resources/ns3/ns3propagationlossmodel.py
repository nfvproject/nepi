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
class NS3BasePropagationLossModel(NS3Base):
    _rtype = "ns3::PropagationLossModel"

    @property
    def simulation(self):
        return self.channel.simulation

    @property
    def channel(self):
        from nepi.resources.ns3.ns3channel import NS3BaseChannel
        channels = self.get_connected(NS3BaseChannel.get_rtype())

        if not channels: 
            msg = "PropagationLossModel not connected to channel"
            self.error(msg)
            raise RuntimeError, msg

        return channels[0]

    @property
    def _rms_to_wait(self):
        others = set()
        others.add(self.channel)
        return others

    def _connect_object(self):
        channel = self.channel
        if channel.uuid not in self.connected:
            self.simulation.invoke(channel.uuid, "SetPropagationLossModel", self.uuid)
            self._connected.add(channel.uuid)

