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

# TODO: 
#       - mobility.SetPositionAllocator ("ns3::GridPositionAllocator",
#       - set hook for Position - SetPosition(Vector)

@clsinit_copy
class NS3BaseMobilityModel(NS3Base):
    _rtype = "abstract::ns3::MobilityModel"

    def _configure_object(self):
        # Set initial position
        position = self.get("Position")
        if position:
            self.simulation.ns3_set(self.uuid, "Position", position)

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.simulation)
        return rms

    def _connect_object(self):
        pass
