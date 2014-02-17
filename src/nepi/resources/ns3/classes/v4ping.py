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
class NS3V4Ping(NS3BaseApplication):
    _rtype = "ns3::V4Ping"

    @classmethod
    def _register_attributes(cls):
        
        attr_remote = Attribute("Remote",
            "The address of the machine we want to ping.",
            type = Types.String,
            default = "102.102.102.102",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_remote)

        attr_verbose = Attribute("Verbose",
            "Produce usual output.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_verbose)

        attr_interval = Attribute("Interval",
            "Wait  interval  seconds between sending each packet.",
            type = Types.String,
            default = "+1000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_interval)

        attr_size = Attribute("Size",
            "The number of data bytes to be sent, real packet will be 8 (ICMP) + 20 (IP) bytes longer.",
            type = Types.Integer,
            default = "56",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_size)

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
        
        rtt = Trace("Rtt", "The rtt calculated by the ping.")

        cls._register_trace(rtt)



    def __init__(self, ec, guid):
        super(NS3V4Ping, self).__init__(ec, guid)
        self._home = "ns3-v4ping-%s" % self.guid
