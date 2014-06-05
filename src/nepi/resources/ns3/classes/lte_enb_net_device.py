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
class NS3LteEnbNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::LteEnbNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_ulbandwidth = Attribute("UlBandwidth",
            "Uplink Transmission Bandwidth Configuration in number of Resource Blocks",
            type = Types.Integer,
            default = "25",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ulbandwidth)

        attr_dlbandwidth = Attribute("DlBandwidth",
            "Downlink Transmission Bandwidth Configuration in number of Resource Blocks",
            type = Types.Integer,
            default = "25",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_dlbandwidth)

        attr_cellid = Attribute("CellId",
            "Cell Identifier",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_cellid)

        attr_dlearfcn = Attribute("DlEarfcn",
            "Downlink E-UTRA Absolute Radio Frequency Channel Number (EARFCN) as per 3GPP 36.101 Section 5.7.3. ",
            type = Types.Integer,
            default = "100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_dlearfcn)

        attr_ulearfcn = Attribute("UlEarfcn",
            "Uplink E-UTRA Absolute Radio Frequency Channel Number (EARFCN) as per 3GPP 36.101 Section 5.7.3. ",
            type = Types.Integer,
            default = "18100",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ulearfcn)

        attr_csgid = Attribute("CsgId",
            "The Closed Subscriber Group (CSG) identity that this eNodeB belongs to",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_csgid)

        attr_csgindication = Attribute("CsgIndication",
            "If true, only UEs which are members of the CSG (i.e. same CSG ID) can gain access to the eNodeB, therefore enforcing closed access mode. Otherwise, the eNodeB operates as a non-CSG cell and implements open access mode.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_csgindication)

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
        super(NS3LteEnbNetDevice, self).__init__(ec, guid)
        self._home = "ns3-lte-enb-net-device-%s" % self.guid
