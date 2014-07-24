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
class NS3Icmpv6L4Protocol(NS3Base):
    _rtype = "ns3::Icmpv6L4Protocol"

    @classmethod
    def _register_attributes(cls):
        
        attr_dad = Attribute("DAD",
            "Always do DAD check.",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_dad)

        attr_solicitationjitter = Attribute("SolicitationJitter",
            "The jitter in ms a node is allowed to wait before sending any solicitation . Some jitter aims to prevent collisions. By default, the model will wait for a duration in ms defined by a uniform random-variable between 0 and SolicitationJitter",
            type = Types.String,
            default = "ns3::UniformRandomVariable[Min=0.0|Max=10.0]",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_solicitationjitter)

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
        pass

    def __init__(self, ec, guid):
        super(NS3Icmpv6L4Protocol, self).__init__(ec, guid)
        self._home = "ns3-icmpv6l4protocol-%s" % self.guid
