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
class NS3PointToPointRemoteChannel(NS3BaseChannel):
    _rtype = "ns3::PointToPointRemoteChannel"

    @classmethod
    def _register_attributes(cls):
        
        attr_delay = Attribute("Delay",
            "Transmission delay through the channel",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_delay)

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
        
        txrxpointtopoint = Trace("TxRxPointToPoint", "Trace source indicating transmission of packet from the PointToPointChannel, used by the Animation interface.")

        cls._register_trace(txrxpointtopoint)



    def __init__(self, ec, guid):
        super(NS3PointToPointRemoteChannel, self).__init__(ec, guid)
        self._home = "ns3-point-to-point-remote-channel-%s" % self.guid
