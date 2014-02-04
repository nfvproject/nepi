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
class NS3BaseChannel(NS3Base):
    _rtype = "abstract::ns3::Channel"

    @property
    def simulator(self):
        return self.devices[0].node.simulator

    @property
    def devices(self):
        from nepi.resources.ns3.ns3netdevice import NS3BaseNetDevice
        devices = self.get_connected(NS3BaseNetDevice.get_rtype())

        if not devices: 
            msg = "Channel not connected to devices"
            self.error(msg)
            raise RuntimeError, msg

        return devices

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.simulator)
        return rms

