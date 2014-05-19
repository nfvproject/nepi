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
class NS3RandomWalk2dMobilityModel(NS3BaseMobilityModel):
    _rtype = "ns3::RandomWalk2dMobilityModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_bounds = Attribute("Bounds",
            "Bounds of the area to cruise.",
            type = Types.String,
            default = "0|0|100|100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_bounds)

        attr_time = Attribute("Time",
            "Change current direction and speed after moving for this delay.",
            type = Types.String,
            default = "+1000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_time)

        attr_distance = Attribute("Distance",
            "Change current direction and speed after moving for this distance.",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_distance)

        attr_mode = Attribute("Mode",
            "The mode indicates the condition used to change the current speed and direction",
            type = Types.Enumerate,
            default = "Distance",  
            allowed = ["Distance","Time"],
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mode)

        attr_direction = Attribute("Direction",
            "A random variable used to pick the direction (gradients).",
            type = Types.String,
            default = "ns3::UniformRandomVariable[Min=0.0|Max=6.283184]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_direction)

        attr_speed = Attribute("Speed",
            "A random variable used to pick the speed (m/s).",
            type = Types.String,
            default = "ns3::UniformRandomVariable[Min=2.0|Max=4.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_speed)

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
        super(NS3RandomWalk2dMobilityModel, self).__init__(ec, guid)
        self._home = "ns3-random-walk2d-mobility-model-%s" % self.guid
