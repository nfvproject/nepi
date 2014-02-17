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
class NS3SteadyStateRandomWaypointMobilityModel(NS3BaseMobilityModel):
    _rtype = "ns3::SteadyStateRandomWaypointMobilityModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_minspeed = Attribute("MinSpeed",
            "Minimum speed value, [m/s]",
            type = Types.Double,
            default = "0.3",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minspeed)

        attr_maxspeed = Attribute("MaxSpeed",
            "Maximum speed value, [m/s]",
            type = Types.Double,
            default = "0.7",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxspeed)

        attr_minpause = Attribute("MinPause",
            "Minimum pause value, [s]",
            type = Types.Double,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minpause)

        attr_maxpause = Attribute("MaxPause",
            "Maximum pause value, [s]",
            type = Types.Double,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxpause)

        attr_minx = Attribute("MinX",
            "Minimum X value of traveling region, [m]",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minx)

        attr_maxx = Attribute("MaxX",
            "Maximum X value of traveling region, [m]",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxx)

        attr_miny = Attribute("MinY",
            "Minimum Y value of traveling region, [m]",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_miny)

        attr_maxy = Attribute("MaxY",
            "Maximum Y value of traveling region, [m]",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxy)

        attr_z = Attribute("Z",
            "Z value of traveling region (fixed), [m]",
            type = Types.Double,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_z)

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
        super(NS3SteadyStateRandomWaypointMobilityModel, self).__init__(ec, guid)
        self._home = "ns3-steady-state-random-waypoint-mobility-model-%s" % self.guid
