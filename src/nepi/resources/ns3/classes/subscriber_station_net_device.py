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
class NS3SubscriberStationNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::SubscriberStationNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_lostdlmapinterval = Attribute("LostDlMapInterval",
            "Time since last received DL-MAP message before downlink synchronization is considered lost. Maximum is 600ms",
            type = Types.String,
            default = "+500000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_lostdlmapinterval)

        attr_lostulmapinterval = Attribute("LostUlMapInterval",
            "Time since last received UL-MAP before uplink synchronization is considered lost, maximum is 600.",
            type = Types.String,
            default = "+500000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_lostulmapinterval)

        attr_maxdcdinterval = Attribute("MaxDcdInterval",
            "Maximum time between transmission of DCD messages. Maximum is 10s",
            type = Types.String,
            default = "+10000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxdcdinterval)

        attr_maxucdinterval = Attribute("MaxUcdInterval",
            "Maximum time between transmission of UCD messages. Maximum is 10s",
            type = Types.String,
            default = "+10000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxucdinterval)

        attr_intervalt1 = Attribute("IntervalT1",
            "Wait for DCD timeout. Maximum is 5*maxDcdInterval",
            type = Types.String,
            default = "+50000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt1)

        attr_intervalt2 = Attribute("IntervalT2",
            "Wait for broadcast ranging timeout, i.e., wait for initial ranging opportunity. Maximum is 5*Ranging interval",
            type = Types.String,
            default = "+10000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt2)

        attr_intervalt3 = Attribute("IntervalT3",
            "ranging Response reception timeout following the transmission of a ranging request. Maximum is 200ms",
            type = Types.String,
            default = "+200000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt3)

        attr_intervalt7 = Attribute("IntervalT7",
            "wait for DSA/DSC/DSD Response timeout. Maximum is 1s",
            type = Types.String,
            default = "+100000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt7)

        attr_intervalt12 = Attribute("IntervalT12",
            "Wait for UCD descriptor.Maximum is 5*MaxUcdInterval",
            type = Types.String,
            default = "+10000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt12)

        attr_intervalt20 = Attribute("IntervalT20",
            "Time the SS searches for preambles on a given channel. Minimum is 2 MAC frames",
            type = Types.String,
            default = "+500000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt20)

        attr_intervalt21 = Attribute("IntervalT21",
            "time the SS searches for (decodable) DL-MAP on a given channel",
            type = Types.String,
            default = "+10000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt21)

        attr_maxcontentionrangingretries = Attribute("MaxContentionRangingRetries",
            "Number of retries on contention Ranging Requests",
            type = Types.Integer,
            default = "16",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxcontentionrangingretries)

        attr_mtu = Attribute("Mtu",
            "The MAC-level Maximum Transmission Unit",
            type = Types.Integer,
            default = "1400",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mtu)

        attr_rtg = Attribute("RTG",
            "receive/transmit transition gap.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rtg)

        attr_ttg = Attribute("TTG",
            "transmit/receive transition gap.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ttg)



    @classmethod
    def _register_traces(cls):
        
        sstxdrop = Trace("SSTxDrop", "A packet has been dropped in the MAC layer before being queued for transmission.")

        cls._register_trace(sstxdrop)

        sspromiscrx = Trace("SSPromiscRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a promiscuous trace,")

        cls._register_trace(sspromiscrx)

        ssrx = Trace("SSRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a non-promiscuous trace,")

        cls._register_trace(ssrx)

        ssrxdrop = Trace("SSRxDrop", "A packet has been dropped in the MAC layer after it has been passed up from the physical layer.")

        cls._register_trace(ssrxdrop)

        rx = Trace("Rx", "Receive trace")

        cls._register_trace(rx)

        tx = Trace("Tx", "Transmit trace")

        cls._register_trace(tx)



    def __init__(self, ec, guid):
        super(NS3SubscriberStationNetDevice, self).__init__(ec, guid)
        self._home = "ns3-subscriber-station-net-device-%s" % self.guid
