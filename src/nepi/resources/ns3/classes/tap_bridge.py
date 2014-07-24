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
class NS3TapBridge(NS3BaseNetDevice):
    _rtype = "ns3::TapBridge"

    @classmethod
    def _register_attributes(cls):
        
        attr_mtu = Attribute("Mtu",
            "The MAC-level Maximum Transmission Unit",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mtu)

        attr_devicename = Attribute("DeviceName",
            "The name of the tap device to create.",
            type = Types.String,
            default = "",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_devicename)

        attr_gateway = Attribute("Gateway",
            "The IP address of the default gateway to assign to the host machine, when in ConfigureLocal mode.",
            type = Types.String,
            default = "255.255.255.255",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_gateway)

        attr_ipaddress = Attribute("IpAddress",
            "The IP address to assign to the tap device, when in ConfigureLocal mode.  This address will override the discovered IP address of the simulated device.",
            type = Types.String,
            default = "255.255.255.255",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ipaddress)

        attr_macaddress = Attribute("MacAddress",
            "The MAC address to assign to the tap device, when in ConfigureLocal mode.  This address will override the discovered MAC address of the simulated device.",
            type = Types.String,
            default = "ff:ff:ff:ff:ff:ff",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_macaddress)

        attr_netmask = Attribute("Netmask",
            "The network mask to assign to the tap device, when in ConfigureLocal mode.  This address will override the discovered MAC address of the simulated device.",
            type = Types.String,
            default = "255.255.255.255",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_netmask)

        attr_start = Attribute("Start",
            "The simulation time at which to spin up the tap device read thread.",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_start)

        attr_stop = Attribute("Stop",
            "The simulation time at which to tear down the tap device read thread.",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_stop)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3TapBridge, self).__init__(ec, guid)
        self._home = "ns3-tap-bridge-%s" % self.guid
