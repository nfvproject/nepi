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
class NS3Cost231PropagationLossModel(NS3BasePropagationLossModel):
    _rtype = "ns3::Cost231PropagationLossModel"

    @classmethod
    def _register_attributes(cls):
        
        attr_lambda = Attribute("Lambda",
            "The wavelength  (default is 2.3 GHz at 300 000 km/s).",
            type = Types.Double,
            default = "0.130435",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_lambda)

        attr_frequency = Attribute("Frequency",
            "The Frequency  (default is 2.3 GHz).",
            type = Types.Double,
            default = "2.3e+09",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_frequency)

        attr_bsantennaheight = Attribute("BSAntennaHeight",
            " BS Antenna Height (default is 50m).",
            type = Types.Double,
            default = "50",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_bsantennaheight)

        attr_ssantennaheight = Attribute("SSAntennaHeight",
            " SS Antenna Height (default is 3m).",
            type = Types.Double,
            default = "3",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ssantennaheight)

        attr_mindistance = Attribute("MinDistance",
            "The distance under which the propagation model refuses to give results (m) ",
            type = Types.Double,
            default = "0.5",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mindistance)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3Cost231PropagationLossModel, self).__init__(ec, guid)
        self._home = "ns3-cost231propagation-loss-model-%s" % self.guid
