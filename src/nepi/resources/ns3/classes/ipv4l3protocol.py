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
from nepi.resources.ns3.ns3ipv4l3protocol import NS3BaseIpv4L3Protocol 

@clsinit_copy
class NS3Ipv4L3Protocol(NS3BaseIpv4L3Protocol):
    _rtype = "ns3::Ipv4L3Protocol"

    @classmethod
    def _register_attributes(cls):
        
        attr_defaulttos = Attribute("DefaultTos",
            "The TOS value set by default on all outgoing packets generated on this node.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_defaulttos)

        attr_defaultttl = Attribute("DefaultTtl",
            "The TTL value set by default on all outgoing packets generated on this node.",
            type = Types.Integer,
            default = "64",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_defaultttl)

        attr_fragmentexpirationtimeout = Attribute("FragmentExpirationTimeout",
            "When this timeout expires, the fragments will be cleared from the buffer.",
            type = Types.String,
            default = "+30000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_fragmentexpirationtimeout)

        attr_ipforward = Attribute("IpForward",
            "Globally enable or disable IP forwarding for all current and future Ipv4 devices.",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ipforward)

        attr_weakesmodel = Attribute("WeakEsModel",
            "RFC1122 term for whether host accepts datagram with a dest. address on another interface",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_weakesmodel)



    @classmethod
    def _register_traces(cls):
        
        tx = Trace("Tx", "Send ipv4 packet to outgoing interface.")

        cls._register_trace(tx)

        rx = Trace("Rx", "Receive ipv4 packet from incoming interface.")

        cls._register_trace(rx)

        drop = Trace("Drop", "Drop ipv4 packet")

        cls._register_trace(drop)

        sendoutgoing = Trace("SendOutgoing", "A newly-generated packet by this node is about to be queued for transmission")

        cls._register_trace(sendoutgoing)

        unicastforward = Trace("UnicastForward", "A unicast IPv4 packet was received by this node and is being forwarded to another node")

        cls._register_trace(unicastforward)

        localdeliver = Trace("LocalDeliver", "An IPv4 packet was received by/for this node, and it is being forward up the stack")

        cls._register_trace(localdeliver)



    def __init__(self, ec, guid):
        super(NS3Ipv4L3Protocol, self).__init__(ec, guid)
        self._home = "ns3-ipv4l3protocol-%s" % self.guid
