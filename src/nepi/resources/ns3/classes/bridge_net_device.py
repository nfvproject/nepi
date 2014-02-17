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
class NS3BridgeNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::BridgeNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_mtu = Attribute("Mtu",
            "The MAC-level Maximum Transmission Unit",
            type = Types.Integer,
            default = "1500",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mtu)

        attr_enablelearning = Attribute("EnableLearning",
            "Enable the learning mode of the Learning Bridge",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_enablelearning)

        attr_expirationtime = Attribute("ExpirationTime",
            "Time it takes for learned MAC state entry to expire.",
            type = Types.String,
            default = "+300000000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_expirationtime)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3BridgeNetDevice, self).__init__(ec, guid)
        self._home = "ns3-bridge-net-device-%s" % self.guid
