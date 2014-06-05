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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.ns3.ns3mobilitymodel import NS3BaseMobilityModel 

@clsinit_copy
class NS3ConstantVelocityMobilityModel(NS3BaseMobilityModel):
    _rtype = "ns3::ConstantVelocityMobilityModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_position = Attribute("Position",
            "The current position of the mobility model.",
            type = Types.String,
            default = "0:0:0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved)

        cls._register_attribute(attr_position)

        attr_velocity = Attribute("Velocity",
            "The current velocity of the mobility model.",
            type = Types.String,
            default = "0:0:0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.NoWrite)

        cls._register_attribute(attr_velocity)



    @classmethod
    def _register_traces(cls):
        
        coursechange = Trace("CourseChange", "The value of the position and/or velocity vector changed")

        cls._register_trace(coursechange)



    def __init__(self, ec, guid):
        super(NS3ConstantVelocityMobilityModel, self).__init__(ec, guid)
        self._home = "ns3-constant-velocity-mobility-model-%s" % self.guid
