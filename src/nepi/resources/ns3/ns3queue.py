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
class NS3BaseQueue(NS3Base):
    _rtype = "abstract::ns3::Queue"

    @property
    def device(self):
        from nepi.resources.ns3.ns3netdevice import NS3BaseNetDevice
        devices = self.get_connected(NS3BaseNetDevice.get_rtype())

        if not devices: 
            msg = "Queue not connected to device"
            self.error(msg, out, err)
            raise RuntimeError, msg

        return devices[0]

    @property
    def node(self):
        return self.device.node

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.device)
        return rms

    def _connect_object(self):
        device = self.device
        if device.uuid not in self.connected:
            self.simulator.invoke(device.uuid, "SetQueue", self.uuid)
            self._connected.add(device.uuid)

