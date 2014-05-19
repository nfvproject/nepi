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
class NS3BaseStationNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::BaseStationNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_initialranginterval = Attribute("InitialRangInterval",
            "Time between Initial Ranging regions assigned by the BS. Maximum is 2s",
            type = Types.String,
            default = "+50000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_initialranginterval)

        attr_dcdinterval = Attribute("DcdInterval",
            "Time between transmission of DCD messages. Maximum value is 10s.",
            type = Types.String,
            default = "+3000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_dcdinterval)

        attr_ucdinterval = Attribute("UcdInterval",
            "Time between transmission of UCD messages. Maximum value is 10s.",
            type = Types.String,
            default = "+3000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ucdinterval)

        attr_intervalt8 = Attribute("IntervalT8",
            "Wait for DSA/DSC Acknowledge timeout. Maximum 300ms.",
            type = Types.String,
            default = "+50000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_intervalt8)

        attr_rangreqoppsize = Attribute("RangReqOppSize",
            "The ranging opportunity size in symbols",
            type = Types.Integer,
            default = "8",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rangreqoppsize)

        attr_bwreqoppsize = Attribute("BwReqOppSize",
            "The bandwidth request opportunity size in symbols",
            type = Types.Integer,
            default = "2",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_bwreqoppsize)

        attr_maxrangcorrectionretries = Attribute("MaxRangCorrectionRetries",
            "Number of retries on contention Ranging Requests",
            type = Types.Integer,
            default = "16",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxrangcorrectionretries)

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
        
        bstx = Trace("BSTx", "A packet has been received from higher layers and is being processed in preparation for queueing for transmission.")

        cls._register_trace(bstx)

        bstxdrop = Trace("BSTxDrop", "A packet has been dropped in the MAC layer before being queued for transmission.")

        cls._register_trace(bstxdrop)

        bspromiscrx = Trace("BSPromiscRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a promiscuous trace,")

        cls._register_trace(bspromiscrx)

        bsrx = Trace("BSRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a non-promiscuous trace,")

        cls._register_trace(bsrx)

        bsrxdrop = Trace("BSRxDrop", "A packet has been dropped in the MAC layer after it has been passed up from the physical layer.")

        cls._register_trace(bsrxdrop)

        rx = Trace("Rx", "Receive trace")

        cls._register_trace(rx)

        tx = Trace("Tx", "Transmit trace")

        cls._register_trace(tx)



    def __init__(self, ec, guid):
        super(NS3BaseStationNetDevice, self).__init__(ec, guid)
        self._home = "ns3-base-station-net-device-%s" % self.guid
