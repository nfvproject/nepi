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
from nepi.resources.ns3.ns3wifimac import NS3BaseWifiMac 

@clsinit_copy
class NS3OcbWifiMac(NS3BaseWifiMac):
    _rtype = "ns3::OcbWifiMac"

    @classmethod
    def _register_attributes(cls):
        
        attr_qossupported = Attribute("QosSupported",
            "This Boolean attribute is set to enable 802.11e/WMM-style QoS support at this STA",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_qossupported)

        attr_htsupported = Attribute("HtSupported",
            "This Boolean attribute is set to enable 802.11n support at this STA",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_htsupported)

        attr_ctstoselfsupported = Attribute("CtsToSelfSupported",
            "Use CTS to Self when using a rate that is not in the basic set rate",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ctstoselfsupported)

        attr_ctstimeout = Attribute("CtsTimeout",
            "When this timeout expires, the RTS/CTS handshake has failed.",
            type = Types.String,
            default = "+75000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ctstimeout)

        attr_acktimeout = Attribute("AckTimeout",
            "When this timeout expires, the DATA/ACK handshake has failed.",
            type = Types.String,
            default = "+75000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_acktimeout)

        attr_basicblockacktimeout = Attribute("BasicBlockAckTimeout",
            "When this timeout expires, the BASIC_BLOCK_ACK_REQ/BASIC_BLOCK_ACK handshake has failed.",
            type = Types.String,
            default = "+281000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_basicblockacktimeout)

        attr_compressedblockacktimeout = Attribute("CompressedBlockAckTimeout",
            "When this timeout expires, the COMPRESSED_BLOCK_ACK_REQ/COMPRESSED_BLOCK_ACK handshake has failed.",
            type = Types.String,
            default = "+107000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_compressedblockacktimeout)

        attr_sifs = Attribute("Sifs",
            "The value of the SIFS constant.",
            type = Types.String,
            default = "+16000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_sifs)

        attr_eifsnodifs = Attribute("EifsNoDifs",
            "The value of EIFS-DIFS",
            type = Types.String,
            default = "+60000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_eifsnodifs)

        attr_slot = Attribute("Slot",
            "The duration of a Slot.",
            type = Types.String,
            default = "+9000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_slot)

        attr_pifs = Attribute("Pifs",
            "The value of the PIFS constant.",
            type = Types.String,
            default = "+25000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pifs)

        attr_rifs = Attribute("Rifs",
            "The value of the RIFS constant.",
            type = Types.String,
            default = "+2000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rifs)

        attr_maxpropagationdelay = Attribute("MaxPropagationDelay",
            "The maximum propagation delay. Unused for now.",
            type = Types.String,
            default = "+3333.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxpropagationdelay)

        attr_ssid = Attribute("Ssid",
            "The ssid we want to belong to.",
            type = Types.String,
            default = "default",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ssid)



    @classmethod
    def _register_traces(cls):
        
        txokheader = Trace("TxOkHeader", "The header of successfully transmitted packet")

        cls._register_trace(txokheader)

        txerrheader = Trace("TxErrHeader", "The header of unsuccessfully transmitted packet")

        cls._register_trace(txerrheader)

        mactx = Trace("MacTx", "A packet has been received from higher layers and is being processed in preparation for queueing for transmission.")

        cls._register_trace(mactx)

        mactxdrop = Trace("MacTxDrop", "A packet has been dropped in the MAC layer before being queued for transmission.")

        cls._register_trace(mactxdrop)

        macpromiscrx = Trace("MacPromiscRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a promiscuous trace,")

        cls._register_trace(macpromiscrx)

        macrx = Trace("MacRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a non-promiscuous trace,")

        cls._register_trace(macrx)

        macrxdrop = Trace("MacRxDrop", "A packet has been dropped in the MAC layer after it has been passed up from the physical layer.")

        cls._register_trace(macrxdrop)



    def __init__(self, ec, guid):
        super(NS3OcbWifiMac, self).__init__(ec, guid)
        self._home = "ns3-ocb-wifi-mac-%s" % self.guid
