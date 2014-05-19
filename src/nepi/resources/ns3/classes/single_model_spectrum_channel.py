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
from nepi.resources.ns3.ns3channel import NS3BaseChannel 

@clsinit_copy
class NS3SingleModelSpectrumChannel(NS3BaseChannel):
    _rtype = "ns3::SingleModelSpectrumChannel"

    @classmethod
    def _register_attributes(cls):
        
        attr_maxlossdb = Attribute("MaxLossDb",
            "If a single-frequency PropagationLossModel is used, this value represents the maximum loss in dB for which transmissions will be passed to the receiving PHY. Signals for which the PropagationLossModel returns a loss bigger than this value will not be propagated to the receiver. This parameter is to be used to reduce the computational load by not propagating signals that are far beyond the interference range. Note that the default value corresponds to considering all signals for reception. Tune this value with care. ",
            type = Types.Double,
            default = "1e+09",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxlossdb)

        attr_id = Attribute("Id",
            "The id (unique integer) of this Channel.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.NoWrite)

        cls._register_attribute(attr_id)



    @classmethod
    def _register_traces(cls):
        
        pathloss = Trace("PathLoss", "This trace is fired whenever a new path loss value is calculated. The first and second parameters to the trace are pointers respectively to the TX and RX SpectrumPhy instances, whereas the third parameters is the loss value in dB. Note that the loss value reported by this trace is the single-frequency loss value obtained by evaluating only the TX and RX AntennaModels and the PropagationLossModel. In particular, note that SpectrumPropagationLossModel (even if present) is never used to evaluate the loss value reported in this trace. ")

        cls._register_trace(pathloss)



    def __init__(self, ec, guid):
        super(NS3SingleModelSpectrumChannel, self).__init__(ec, guid)
        self._home = "ns3-single-model-spectrum-channel-%s" % self.guid
