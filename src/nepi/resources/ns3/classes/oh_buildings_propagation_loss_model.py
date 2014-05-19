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
class NS3OhBuildingsPropagationLossModel(NS3BasePropagationLossModel):
    _rtype = "ns3::OhBuildingsPropagationLossModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_shadowsigmaoutdoor = Attribute("ShadowSigmaOutdoor",
            "Standard deviation of the normal distribution used for calculate the shadowing for outdoor nodes",
            type = Types.Double,
            default = "7",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_shadowsigmaoutdoor)

        attr_shadowsigmaindoor = Attribute("ShadowSigmaIndoor",
            "Standard deviation of the normal distribution used for calculate the shadowing for indoor nodes ",
            type = Types.Double,
            default = "8",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_shadowsigmaindoor)

        attr_shadowsigmaextwalls = Attribute("ShadowSigmaExtWalls",
            "Standard deviation of the normal distribution used for calculate the shadowing due to ext walls ",
            type = Types.Double,
            default = "5",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_shadowsigmaextwalls)

        attr_internalwallloss = Attribute("InternalWallLoss",
            "Additional loss for each internal wall [dB]",
            type = Types.Double,
            default = "5",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_internalwallloss)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3OhBuildingsPropagationLossModel, self).__init__(ec, guid)
        self._home = "ns3-oh-buildings-propagation-loss-model-%s" % self.guid
