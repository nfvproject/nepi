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
class NS3OnOffApplication(NS3BaseApplication):
    _rtype = "ns3::OnOffApplication"

    @classmethod
    def _register_attributes(cls):
        
        attr_datarate = Attribute("DataRate",
            "The data rate in on state.",
            type = Types.String,
            default = "500000bps",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_datarate)

        attr_packetsize = Attribute("PacketSize",
            "The size of packets sent in on state",
            type = Types.Integer,
            default = "512",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_packetsize)

        attr_remote = Attribute("Remote",
            "The address of the destination",
            type = Types.String,
            default = "00-00-00",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_remote)

        attr_ontime = Attribute("OnTime",
            "A RandomVariableStream used to pick the duration of the \'On\' state.",
            type = Types.String,
            default = "ns3::ConstantRandomVariable[Constant=1.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ontime)

        attr_offtime = Attribute("OffTime",
            "A RandomVariableStream used to pick the duration of the \'Off\' state.",
            type = Types.String,
            default = "ns3::ConstantRandomVariable[Constant=1.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_offtime)

        attr_maxbytes = Attribute("MaxBytes",
            "The total number of bytes to send. Once these bytes are sent, no packet is sent again, even in on state. The value zero means that there is no limit.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxbytes)

        attr_protocol = Attribute("Protocol",
            "The type of protocol to use.",
            type = Types.String,
            default = "ns3::UdpSocketFactory",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_protocol)

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
        super(NS3OnOffApplication, self).__init__(ec, guid)
        self._home = "ns3-on-off-application-%s" % self.guid
