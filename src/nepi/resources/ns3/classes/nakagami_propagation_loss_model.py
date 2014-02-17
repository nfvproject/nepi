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
class NS3NakagamiPropagationLossModel(NS3BasePropagationLossModel):
    _rtype = "ns3::NakagamiPropagationLossModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_distance1 = Attribute("Distance1",
            "Beginning of the second distance field. Default is 80m.",
            type = Types.Double,
            default = "80",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_distance1)

        attr_distance2 = Attribute("Distance2",
            "Beginning of the third distance field. Default is 200m.",
            type = Types.Double,
            default = "200",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_distance2)

        attr_m0 = Attribute("m0",
            "m0 for distances smaller than Distance1. Default is 1.5.",
            type = Types.Double,
            default = "1.5",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_m0)

        attr_m1 = Attribute("m1",
            "m1 for distances smaller than Distance2. Default is 0.75.",
            type = Types.Double,
            default = "0.75",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_m1)

        attr_m2 = Attribute("m2",
            "m2 for distances greater than Distance2. Default is 0.75.",
            type = Types.Double,
            default = "0.75",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_m2)

        attr_erlangrv = Attribute("ErlangRv",
            "Access to the underlying ErlangRandomVariable",
            type = Types.String,
            default = "ns3::ErlangRandomVariable",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_erlangrv)

        attr_gammarv = Attribute("GammaRv",
            "Access to the underlying GammaRandomVariable",
            type = Types.String,
            default = "ns3::GammaRandomVariable",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_gammarv)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3NakagamiPropagationLossModel, self).__init__(ec, guid)
        self._home = "ns3-nakagami-propagation-loss-model-%s" % self.guid
