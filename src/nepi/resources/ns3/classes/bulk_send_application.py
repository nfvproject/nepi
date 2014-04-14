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
class NS3BulkSendApplication(NS3BaseApplication):
    _rtype = "ns3::BulkSendApplication"

    @classmethod
    def _register_attributes(cls):
        
        attr_sendsize = Attribute("SendSize",
            "The amount of data to send each time.",
            type = Types.Integer,
            default = "512",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_sendsize)

        attr_remote = Attribute("Remote",
            "The address of the destination",
            type = Types.String,
            default = "00-00-00",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_remote)

        attr_maxbytes = Attribute("MaxBytes",
            "The total number of bytes to send. Once these bytes are sent, no data  is sent again. The value zero means that there is no limit.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxbytes)

        attr_protocol = Attribute("Protocol",
            "The type of protocol to use.",
            type = Types.String,
            default = "ns3::TcpSocketFactory",  
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
        super(NS3BulkSendApplication, self).__init__(ec, guid)
        self._home = "ns3-bulk-send-application-%s" % self.guid
