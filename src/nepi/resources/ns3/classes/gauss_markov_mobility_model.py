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
class NS3GaussMarkovMobilityModel(NS3BaseMobilityModel):
    _rtype = "ns3::GaussMarkovMobilityModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_bounds = Attribute("Bounds",
            "Bounds of the area to cruise.",
            type = Types.String,
            default = "-100|100|-100|100|0|100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_bounds)

        attr_timestep = Attribute("TimeStep",
            "Change current direction and speed after moving for this time.",
            type = Types.String,
            default = "+1000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_timestep)

        attr_alpha = Attribute("Alpha",
            "A constant representing the tunable parameter in the Gauss-Markov model.",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_alpha)

        attr_meanvelocity = Attribute("MeanVelocity",
            "A random variable used to assign the average velocity.",
            type = Types.String,
            default = "ns3::UniformRandomVariable[Min=0.0|Max=1.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_meanvelocity)

        attr_meandirection = Attribute("MeanDirection",
            "A random variable used to assign the average direction.",
            type = Types.String,
            default = "ns3::UniformRandomVariable[Min=0.0|Max=6.283185307]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_meandirection)

        attr_meanpitch = Attribute("MeanPitch",
            "A random variable used to assign the average pitch.",
            type = Types.String,
            default = "ns3::ConstantRandomVariable[Constant=0.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_meanpitch)

        attr_normalvelocity = Attribute("NormalVelocity",
            "A gaussian random variable used to calculate the next velocity value.",
            type = Types.String,
            default = "ns3::NormalRandomVariable[Mean=0.0|Variance=1.0|Bound=10.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_normalvelocity)

        attr_normaldirection = Attribute("NormalDirection",
            "A gaussian random variable used to calculate the next direction value.",
            type = Types.String,
            default = "ns3::NormalRandomVariable[Mean=0.0|Variance=1.0|Bound=10.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_normaldirection)

        attr_normalpitch = Attribute("NormalPitch",
            "A gaussian random variable used to calculate the next pitch value.",
            type = Types.String,
            default = "ns3::NormalRandomVariable[Mean=0.0|Variance=1.0|Bound=10.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_normalpitch)

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
        super(NS3GaussMarkovMobilityModel, self).__init__(ec, guid)
        self._home = "ns3-gauss-markov-mobility-model-%s" % self.guid
