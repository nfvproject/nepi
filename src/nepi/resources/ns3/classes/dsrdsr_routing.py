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
from nepi.resources.ns3.ns3base import NS3Base

@clsinit_copy
class NS3dsrDsrRouting(NS3Base):
    _rtype = "ns3::dsr::DsrRouting"

    @classmethod
    def _register_attributes(cls):
        
        attr_maxsendbufflen = Attribute("MaxSendBuffLen",
            "Maximum number of packets that can be stored in send buffer.",
            type = Types.Integer,
            default = "64",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxsendbufflen)

        attr_maxsendbufftime = Attribute("MaxSendBuffTime",
            "Maximum time packets can be queued in the send buffer .",
            type = Types.String,
            default = "+30000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxsendbufftime)

        attr_maxmaintlen = Attribute("MaxMaintLen",
            "Maximum number of packets that can be stored in maintenance buffer.",
            type = Types.Integer,
            default = "50",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxmaintlen)

        attr_maxmainttime = Attribute("MaxMaintTime",
            "Maximum time packets can be queued in maintenance buffer.",
            type = Types.String,
            default = "+30000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxmainttime)

        attr_maxcachelen = Attribute("MaxCacheLen",
            "Maximum number of route entries that can be stored in route cache.",
            type = Types.Integer,
            default = "64",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxcachelen)

        attr_routecachetimeout = Attribute("RouteCacheTimeout",
            "Maximum time the route cache can be queued in route cache.",
            type = Types.String,
            default = "+300000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_routecachetimeout)

        attr_maxentrieseachdst = Attribute("MaxEntriesEachDst",
            "Maximum number of route entries for a single destination to respond.",
            type = Types.Integer,
            default = "20",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxentrieseachdst)

        attr_sendbuffinterval = Attribute("SendBuffInterval",
            "How often to check send buffer for packet with route.",
            type = Types.String,
            default = "+500000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_sendbuffinterval)

        attr_nodetraversaltime = Attribute("NodeTraversalTime",
            "The time it takes to traverse two neighboring nodes.",
            type = Types.String,
            default = "+40000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_nodetraversaltime)

        attr_rreqretries = Attribute("RreqRetries",
            "Maximum number of retransmissions for request discovery of a route.",
            type = Types.Integer,
            default = "16",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rreqretries)

        attr_maintenanceretries = Attribute("MaintenanceRetries",
            "Maximum number of retransmissions for data packets from maintenance buffer.",
            type = Types.Integer,
            default = "2",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maintenanceretries)

        attr_requesttablesize = Attribute("RequestTableSize",
            "Maximum number of request entries in the request table, set this as the number of nodes in the simulation.",
            type = Types.Integer,
            default = "64",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_requesttablesize)

        attr_requestidsize = Attribute("RequestIdSize",
            "Maximum number of request source Ids in the request table.",
            type = Types.Integer,
            default = "16",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_requestidsize)

        attr_uniquerequestidsize = Attribute("UniqueRequestIdSize",
            "Maximum number of request Ids in the request table for a single destination.",
            type = Types.Integer,
            default = "256",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_uniquerequestidsize)

        attr_nonproprequesttimeout = Attribute("NonPropRequestTimeout",
            "The timeout value for non-propagation request.",
            type = Types.String,
            default = "+30000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_nonproprequesttimeout)

        attr_discoveryhoplimit = Attribute("DiscoveryHopLimit",
            "The max discovery hop limit for route requests.",
            type = Types.Integer,
            default = "255",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_discoveryhoplimit)

        attr_maxsalvagecount = Attribute("MaxSalvageCount",
            "The max salvage count for a single data packet.",
            type = Types.Integer,
            default = "15",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxsalvagecount)

        attr_blacklisttimeout = Attribute("BlacklistTimeout",
            "The time for a neighbor to stay in blacklist.",
            type = Types.String,
            default = "+3000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_blacklisttimeout)

        attr_gratreplyholdoff = Attribute("GratReplyHoldoff",
            "The time for gratuitous reply entry to expire.",
            type = Types.String,
            default = "+1000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_gratreplyholdoff)

        attr_broadcastjitter = Attribute("BroadcastJitter",
            "The jitter time to avoid collision for broadcast packets.",
            type = Types.Integer,
            default = "10",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_broadcastjitter)

        attr_linkacktimeout = Attribute("LinkAckTimeout",
            "The time a packet in maintenance buffer wait for link acknowledgment.",
            type = Types.String,
            default = "+100000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_linkacktimeout)

        attr_trylinkacks = Attribute("TryLinkAcks",
            "The number of link acknowledgment to use.",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_trylinkacks)

        attr_passiveacktimeout = Attribute("PassiveAckTimeout",
            "The time a packet in maintenance buffer wait for passive acknowledgment.",
            type = Types.String,
            default = "+100000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_passiveacktimeout)

        attr_trypassiveacks = Attribute("TryPassiveAcks",
            "The number of passive acknowledgment to use.",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_trypassiveacks)

        attr_requestperiod = Attribute("RequestPeriod",
            "The base time interval between route requests.",
            type = Types.String,
            default = "+500000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_requestperiod)

        attr_maxrequestperiod = Attribute("MaxRequestPeriod",
            "The max time interval between route requests.",
            type = Types.String,
            default = "+10000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxrequestperiod)

        attr_grareplytablesize = Attribute("GraReplyTableSize",
            "The gratuitous reply table size.",
            type = Types.Integer,
            default = "64",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_grareplytablesize)

        attr_cachetype = Attribute("CacheType",
            "Use Link Cache or use Path Cache",
            type = Types.String,
            default = "LinkCache",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_cachetype)

        attr_stabilitydecrfactor = Attribute("StabilityDecrFactor",
            "The stability decrease factor for link cache",
            type = Types.Integer,
            default = "2",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_stabilitydecrfactor)

        attr_stabilityincrfactor = Attribute("StabilityIncrFactor",
            "The stability increase factor for link cache",
            type = Types.Integer,
            default = "4",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_stabilityincrfactor)

        attr_initstability = Attribute("InitStability",
            "The initial stability factor for link cache",
            type = Types.String,
            default = "+25000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_initstability)

        attr_minlifetime = Attribute("MinLifeTime",
            "The minimal life time for link cache",
            type = Types.String,
            default = "+1000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minlifetime)

        attr_useextends = Attribute("UseExtends",
            "The extension time for link cache",
            type = Types.String,
            default = "+120000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_useextends)

        attr_enablesubroute = Attribute("EnableSubRoute",
            "Enables saving of sub route when receiving route error messages, only available when using path route cache",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_enablesubroute)

        attr_retransincr = Attribute("RetransIncr",
            "The increase time for retransmission timer when facing network congestion",
            type = Types.String,
            default = "+20000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_retransincr)

        attr_maxnetworkqueuesize = Attribute("MaxNetworkQueueSize",
            "The max number of packet to save in the network queue.",
            type = Types.Integer,
            default = "400",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxnetworkqueuesize)

        attr_maxnetworkqueuedelay = Attribute("MaxNetworkQueueDelay",
            "The max time for a packet to stay in the network queue.",
            type = Types.String,
            default = "+30000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxnetworkqueuedelay)

        attr_numpriorityqueues = Attribute("NumPriorityQueues",
            "The max number of packet to save in the network queue.",
            type = Types.Integer,
            default = "2",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_numpriorityqueues)

        attr_linkacknowledgment = Attribute("LinkAcknowledgment",
            "Enable Link layer acknowledgment mechanism",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_linkacknowledgment)

        attr_protocolnumber = Attribute("ProtocolNumber",
            "The Ip protocol number.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_protocolnumber)



    @classmethod
    def _register_traces(cls):
        
        tx = Trace("Tx", "Send DSR packet.")

        cls._register_trace(tx)

        drop = Trace("Drop", "Drop DSR packet")

        cls._register_trace(drop)



    def __init__(self, ec, guid):
        super(NS3dsrDsrRouting, self).__init__(ec, guid)
        self._home = "ns3-dsr-dsr-routing-%s" % self.guid
