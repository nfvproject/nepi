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
class NS3LteUeNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::LteUeNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_imsi = Attribute("Imsi",
            "International Mobile Subscriber Identity assigned to this UE",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_imsi)

        attr_dlearfcn = Attribute("DlEarfcn",
            "Downlink E-UTRA Absolute Radio Frequency Channel Number (EARFCN) as per 3GPP 36.101 Section 5.7.3. ",
            type = Types.Integer,
            default = "100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_dlearfcn)

        attr_csgid = Attribute("CsgId",
            "The Closed Subscriber Group (CSG) identity that this UE is associated with, i.e., giving the UE access to cells which belong to this particular CSG. This restriction only applies to initial cell selection and EPC-enabled simulation. This does not revoke the UE\'s access to non-CSG cells. ",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_csgid)

        attr_mtu = Attribute("Mtu",
            "The MAC-level Maximum Transmission Unit",
            type = Types.Integer,
            default = "30000",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mtu)



    @classmethod
    def _register_traces(cls):
        pass

    def __init__(self, ec, guid):
        super(NS3LteUeNetDevice, self).__init__(ec, guid)
        self._home = "ns3-lte-ue-net-device-%s" % self.guid
