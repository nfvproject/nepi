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
from nepi.resources.ns3.ns3application import NS3BaseApplication 

@clsinit_copy
class NS3Ping6(NS3BaseApplication):
    _rtype = "ns3::Ping6"

    @classmethod
    def _register_attributes(cls):
        
        attr_maxpackets = Attribute("MaxPackets",
            "The maximum number of packets the application will send",
            type = Types.Integer,
            default = "100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxpackets)

        attr_interval = Attribute("Interval",
            "The time to wait between packets",
            type = Types.String,
            default = "+1000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_interval)

        attr_remoteipv6 = Attribute("RemoteIpv6",
            "The Ipv6Address of the outbound packets",
            type = Types.String,
            default = "0000:0000:0000:0000:0000:0000:0000:0000",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_remoteipv6)

        attr_localipv6 = Attribute("LocalIpv6",
            "Local Ipv6Address of the sender",
            type = Types.String,
            default = "0000:0000:0000:0000:0000:0000:0000:0000",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_localipv6)

        attr_packetsize = Attribute("PacketSize",
            "Size of packets generated",
            type = Types.Integer,
            default = "100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_packetsize)

        attr_starttime = Attribute("StartTime",
            "Time at which the application will start",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_starttime)

        attr_stoptime = Attribute("StopTime",
            "Time at which the application will stop",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_stoptime)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3Ping6, self).__init__(ec, guid)
        self._home = "ns3-ping6-%s" % self.guid
