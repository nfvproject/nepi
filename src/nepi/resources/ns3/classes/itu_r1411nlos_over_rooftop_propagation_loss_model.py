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
from nepi.resources.ns3.ns3propagationlossmodel import NS3BasePropagationLossModel 

@clsinit_copy
class NS3ItuR1411NlosOverRooftopPropagationLossModel(NS3BasePropagationLossModel):
    _rtype = "ns3::ItuR1411NlosOverRooftopPropagationLossModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_environment = Attribute("Environment",
            "Environment Scenario",
            type = Types.Enumerate,
            default = "Urban",  
            allowed = ["Urban","SubUrban","OpenAreas"],
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_environment)

        attr_citysize = Attribute("CitySize",
            "Dimension of the city",
            type = Types.Enumerate,
            default = "Large",  
            allowed = ["Small","Medium","Large"],
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_citysize)

        attr_rooftoplevel = Attribute("RooftopLevel",
            "The height of the rooftop level in meters",
            type = Types.Double,
            default = "20",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rooftoplevel)

        attr_streetsorientation = Attribute("StreetsOrientation",
            "The orientation of streets in degrees [0,90] with respect to the direction of propagation",
            type = Types.Double,
            default = "45",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_streetsorientation)

        attr_streetswidth = Attribute("StreetsWidth",
            "The width of streets",
            type = Types.Double,
            default = "20",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_streetswidth)

        attr_buildingsextend = Attribute("BuildingsExtend",
            "The distance over which the buildings extend",
            type = Types.Double,
            default = "80",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_buildingsextend)

        attr_buildingseparation = Attribute("BuildingSeparation",
            "The separation between buildings",
            type = Types.Double,
            default = "50",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_buildingseparation)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3ItuR1411NlosOverRooftopPropagationLossModel, self).__init__(ec, guid)
        self._home = "ns3-itu-r1411nlos-over-rooftop-propagation-loss-model-%s" % self.guid
