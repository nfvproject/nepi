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
class NS3LogDistancePropagationLossModel(NS3BasePropagationLossModel):
    _rtype = "ns3::LogDistancePropagationLossModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_exponent = Attribute("Exponent",
            "The exponent of the Path Loss propagation model",
            type = Types.Double,
            default = "3",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_exponent)

        attr_referencedistance = Attribute("ReferenceDistance",
            "The distance at which the reference loss is calculated (m)",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_referencedistance)

        attr_referenceloss = Attribute("ReferenceLoss",
            "The reference loss at reference distance (dB). (Default is Friis at 1m with 5.15 GHz)",
            type = Types.Double,
            default = "46.6777",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_referenceloss)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3LogDistancePropagationLossModel, self).__init__(ec, guid)
        self._home = "ns3-log-distance-propagation-loss-model-%s" % self.guid
