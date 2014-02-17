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
from nepi.resources.ns3.ns3netdevice import NS3BaseNetDevice 

@clsinit_copy
class NS3AlohaNoackNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::AlohaNoackNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_address = Attribute("Address",
            "The MAC address of this device.",
            type = Types.String,
            default = "12:34:56:78:90:12",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_address)

        attr_mtu = Attribute("Mtu",
            "The Maximum Transmission Unit",
            type = Types.Integer,
            default = "1500",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mtu)



    @classmethod
    def _register_traces(cls):
        
        mactx = Trace("MacTx", "Trace source indicating a packet has arrived for transmission by this device")

        cls._register_trace(mactx)

        mactxdrop = Trace("MacTxDrop", "Trace source indicating a packet has been dropped by the device before transmission")

        cls._register_trace(mactxdrop)

        macpromiscrx = Trace("MacPromiscRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a promiscuous trace,")

        cls._register_trace(macpromiscrx)

        macrx = Trace("MacRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a non-promiscuous trace,")

        cls._register_trace(macrx)



    def __init__(self, ec, guid):
        super(NS3AlohaNoackNetDevice, self).__init__(ec, guid)
        self._home = "ns3-aloha-noack-net-device-%s" % self.guid
