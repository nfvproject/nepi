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
class NS3UdpEchoClient(NS3BaseApplication):
    _rtype = "ns3::UdpEchoClient"

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

        attr_remoteaddress = Attribute("RemoteAddress",
            "The destination Address of the outbound packets",
            type = Types.String,
            default = "00-00-00",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_remoteaddress)

        attr_remoteport = Attribute("RemotePort",
            "The destination port of the outbound packets",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_remoteport)

        attr_packetsize = Attribute("PacketSize",
            "Size of echo data in outbound packets",
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
        
        tx = Trace("Tx", "A new packet is created and is sent")

        cls._register_trace(tx)



    def __init__(self, ec, guid):
        super(NS3UdpEchoClient, self).__init__(ec, guid)
        self._home = "ns3-udp-echo-client-%s" % self.guid
