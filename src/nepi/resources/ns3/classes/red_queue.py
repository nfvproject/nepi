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
from nepi.resources.ns3.ns3queue import NS3BaseQueue 

@clsinit_copy
class NS3RedQueue(NS3BaseQueue):
    _rtype = "ns3::RedQueue"

    @classmethod
    def _register_attributes(cls):
        
        attr_meanpktsize = Attribute("MeanPktSize",
            "Average of packet size",
            type = Types.Integer,
            default = "500",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_meanpktsize)

        attr_idlepktsize = Attribute("IdlePktSize",
            "Average packet size used during idle times. Used when m_cautions = 3",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_idlepktsize)

        attr_wait = Attribute("Wait",
            "True for waiting between dropped packets",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_wait)

        attr_gentle = Attribute("Gentle",
            "True to increases dropping probability slowly when average queue exceeds maxthresh",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_gentle)

        attr_minth = Attribute("MinTh",
            "Minimum average length threshold in packets/bytes",
            type = Types.Double,
            default = "5",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minth)

        attr_maxth = Attribute("MaxTh",
            "Maximum average length threshold in packets/bytes",
            type = Types.Double,
            default = "15",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxth)

        attr_queuelimit = Attribute("QueueLimit",
            "Queue limit in bytes/packets",
            type = Types.Integer,
            default = "25",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_queuelimit)

        attr_qw = Attribute("QW",
            "Queue weight related to the exponential weighted moving average (EWMA)",
            type = Types.Double,
            default = "0.002",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_qw)

        attr_linterm = Attribute("LInterm",
            "The maximum probability of dropping a packet",
            type = Types.Double,
            default = "50",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_linterm)

        attr_ns1compat = Attribute("Ns1Compat",
            "NS-1 compatibility",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ns1compat)

        attr_linkbandwidth = Attribute("LinkBandwidth",
            "The RED link bandwidth",
            type = Types.String,
            default = "1500000bps",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_linkbandwidth)

        attr_linkdelay = Attribute("LinkDelay",
            "The RED link delay",
            type = Types.String,
            default = "+20000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_linkdelay)



    @classmethod
    def _register_traces(cls):
        
        enqueue = Trace("Enqueue", "Enqueue a packet in the queue.")

        cls._register_trace(enqueue)

        dequeue = Trace("Dequeue", "Dequeue a packet from the queue.")

        cls._register_trace(dequeue)

        drop = Trace("Drop", "Drop a packet stored in the queue.")

        cls._register_trace(drop)



    def __init__(self, ec, guid):
        super(NS3RedQueue, self).__init__(ec, guid)
        self._home = "ns3-red-queue-%s" % self.guid
