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
class NS3SixLowPanNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::SixLowPanNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_rfc6282 = Attribute("Rfc6282",
            "Use RFC6282 (IPHC) if true, RFC4944 (HC1) otherwise.",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rfc6282)

        attr_omitudpchecksum = Attribute("OmitUdpChecksum",
            "Omit the UDP checksum in IPHC compression.",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_omitudpchecksum)

        attr_fragmentreassemblylistsize = Attribute("FragmentReassemblyListSize",
            "The maximum size of the reassembly buffer (in packets). Zero meaning infinite.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_fragmentreassemblylistsize)

        attr_fragmentexpirationtimeout = Attribute("FragmentExpirationTimeout",
            "When this timeout expires, the fragments will be cleared from the buffer.",
            type = Types.String,
            default = "+60000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_fragmentexpirationtimeout)

        attr_compressionthreshold = Attribute("CompressionThreshold",
            "The minimum MAC layer payload size.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_compressionthreshold)

        attr_forceethertype = Attribute("ForceEtherType",
            "Force a specific EtherType in L2 frames.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_forceethertype)

        attr_ethertype = Attribute("EtherType",
            "The specific EtherType to be used in L2 frames.",
            type = Types.Integer,
            default = "65535",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ethertype)



    @classmethod
    def _register_traces(cls):
        
        tx = Trace("Tx", "Send - packet (including 6LoWPAN header), SixLoWPanNetDevice Ptr, interface index.")

        cls._register_trace(tx)

        rx = Trace("Rx", "Receive - packet (including 6LoWPAN header), SixLoWPanNetDevice Ptr, interface index.")

        cls._register_trace(rx)

        drop = Trace("Drop", "Drop - DropReason, packet (including 6LoWPAN header), SixLoWPanNetDevice Ptr, interface index.")

        cls._register_trace(drop)



    def __init__(self, ec, guid):
        super(NS3SixLowPanNetDevice, self).__init__(ec, guid)
        self._home = "ns3-six-low-pan-net-device-%s" % self.guid
