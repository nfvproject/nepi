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
from nepi.resources.ns3.ns3wifiremotestationmanager import NS3BaseWifiRemoteStationManager 

@clsinit_copy
class NS3RraaWifiManager(NS3BaseWifiRemoteStationManager):
    _rtype = "ns3::RraaWifiManager"

    @classmethod
    def _register_attributes(cls):
        
        attr_basic = Attribute("Basic",
            "If true the RRAA-BASIC algorithm will be used, otherwise the RRAA wil be used",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_basic)

        attr_timeout = Attribute("Timeout",
            "Timeout for the RRAA BASIC loss estimaton block (s)",
            type = Types.String,
            default = "+50000000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_timeout)

        attr_ewndfor54mbps = Attribute("ewndFor54mbps",
            "ewnd parameter for 54 Mbs data mode",
            type = Types.Integer,
            default = "40",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor54mbps)

        attr_ewndfor48mbps = Attribute("ewndFor48mbps",
            "ewnd parameter for 48 Mbs data mode",
            type = Types.Integer,
            default = "40",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor48mbps)

        attr_ewndfor36mbps = Attribute("ewndFor36mbps",
            "ewnd parameter for 36 Mbs data mode",
            type = Types.Integer,
            default = "40",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor36mbps)

        attr_ewndfor24mbps = Attribute("ewndFor24mbps",
            "ewnd parameter for 24 Mbs data mode",
            type = Types.Integer,
            default = "40",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor24mbps)

        attr_ewndfor18mbps = Attribute("ewndFor18mbps",
            "ewnd parameter for 18 Mbs data mode",
            type = Types.Integer,
            default = "20",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor18mbps)

        attr_ewndfor12mbps = Attribute("ewndFor12mbps",
            "ewnd parameter for 12 Mbs data mode",
            type = Types.Integer,
            default = "20",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor12mbps)

        attr_ewndfor9mbps = Attribute("ewndFor9mbps",
            "ewnd parameter for 9 Mbs data mode",
            type = Types.Integer,
            default = "10",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor9mbps)

        attr_ewndfor6mbps = Attribute("ewndFor6mbps",
            "ewnd parameter for 6 Mbs data mode",
            type = Types.Integer,
            default = "6",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ewndfor6mbps)

        attr_porifor48mbps = Attribute("poriFor48mbps",
            "Pori parameter for 48 Mbs data mode",
            type = Types.Double,
            default = "0.047",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor48mbps)

        attr_porifor36mbps = Attribute("poriFor36mbps",
            "Pori parameter for 36 Mbs data mode",
            type = Types.Double,
            default = "0.115",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor36mbps)

        attr_porifor24mbps = Attribute("poriFor24mbps",
            "Pori parameter for 24 Mbs data mode",
            type = Types.Double,
            default = "0.1681",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor24mbps)

        attr_porifor18mbps = Attribute("poriFor18mbps",
            "Pori parameter for 18 Mbs data mode",
            type = Types.Double,
            default = "0.1325",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor18mbps)

        attr_porifor12mbps = Attribute("poriFor12mbps",
            "Pori parameter for 12 Mbs data mode",
            type = Types.Double,
            default = "0.1861",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor12mbps)

        attr_porifor9mbps = Attribute("poriFor9mbps",
            "Pori parameter for 9 Mbs data mode",
            type = Types.Double,
            default = "0.1434",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor9mbps)

        attr_porifor6mbps = Attribute("poriFor6mbps",
            "Pori parameter for 6 Mbs data mode",
            type = Types.Double,
            default = "0.5",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_porifor6mbps)

        attr_pmtlfor54mbps = Attribute("pmtlFor54mbps",
            "Pmtl parameter for 54 Mbs data mode",
            type = Types.Double,
            default = "0.094",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor54mbps)

        attr_pmtlfor48mbps = Attribute("pmtlFor48mbps",
            "Pmtl parameter for 48 Mbs data mode",
            type = Types.Double,
            default = "0.23",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor48mbps)

        attr_pmtlfor36mbps = Attribute("pmtlFor36mbps",
            "Pmtl parameter for 36 Mbs data mode",
            type = Types.Double,
            default = "0.3363",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor36mbps)

        attr_pmtlfor24mbps = Attribute("pmtlFor24mbps",
            "Pmtl parameter for 24 Mbs data mode",
            type = Types.Double,
            default = "0.265",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor24mbps)

        attr_pmtlfor18mbps = Attribute("pmtlFor18mbps",
            "Pmtl parameter for 18 Mbs data mode",
            type = Types.Double,
            default = "0.3722",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor18mbps)

        attr_pmtlfor12mbps = Attribute("pmtlFor12mbps",
            "Pmtl parameter for 12 Mbs data mode",
            type = Types.Double,
            default = "0.2868",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor12mbps)

        attr_pmtlfor9mbps = Attribute("pmtlFor9mbps",
            "Pmtl parameter for 9 Mbs data mode",
            type = Types.Double,
            default = "0.3932",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_pmtlfor9mbps)

        attr_islowlatency = Attribute("IsLowLatency",
            "If true, we attempt to modelize a so-called low-latency device: a device where decisions about tx parameters can be made on a per-packet basis and feedback about the transmission of each packet is obtained before sending the next. Otherwise, we modelize a  high-latency device, that is a device where we cannot update our decision about tx parameters after every packet transmission.",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_islowlatency)

        attr_maxssrc = Attribute("MaxSsrc",
            "The maximum number of retransmission attempts for an RTS. This value will not have any effect on some rate control algorithms.",
            type = Types.Integer,
            default = "7",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxssrc)

        attr_maxslrc = Attribute("MaxSlrc",
            "The maximum number of retransmission attempts for a DATA packet. This value will not have any effect on some rate control algorithms.",
            type = Types.Integer,
            default = "7",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxslrc)

        attr_rtsctsthreshold = Attribute("RtsCtsThreshold",
            "If  the size of the data packet + LLC header + MAC header + FCS trailer is bigger than this value, we use an RTS/CTS handshake before sending the data, as per IEEE Std. 802.11-2007, Section 9.2.6. This value will not have any effect on some rate control algorithms.",
            type = Types.Integer,
            default = "2346",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rtsctsthreshold)

        attr_fragmentationthreshold = Attribute("FragmentationThreshold",
            "If the size of the data packet + LLC header + MAC header + FCS trailer is biggerthan this value, we fragment it such that the size of the fragments are equal or smaller than this value, as per IEEE Std. 802.11-2007, Section 9.4. This value will not have any effect on some rate control algorithms.",
            type = Types.Integer,
            default = "2346",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_fragmentationthreshold)

        attr_nonunicastmode = Attribute("NonUnicastMode",
            "Wifi mode used for non-unicast transmissions.",
            type = Types.String,
            default = "Invalid-WifiMode",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_nonunicastmode)

        attr_defaulttxpowerlevel = Attribute("DefaultTxPowerLevel",
            "Default power level to be used for transmissions. This is the power level that is used by all those WifiManagers that do notimplement TX power control.",
            type = Types.Integer,
            default = "0",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_defaulttxpowerlevel)



    @classmethod
    def _register_traces(cls):
        
        mactxrtsfailed = Trace("MacTxRtsFailed", "The transmission of a RTS by the MAC layer has failed")

        cls._register_trace(mactxrtsfailed)

        mactxdatafailed = Trace("MacTxDataFailed", "The transmission of a data packet by the MAC layer has failed")

        cls._register_trace(mactxdatafailed)

        mactxfinalrtsfailed = Trace("MacTxFinalRtsFailed", "The transmission of a RTS has exceeded the maximum number of attempts")

        cls._register_trace(mactxfinalrtsfailed)

        mactxfinaldatafailed = Trace("MacTxFinalDataFailed", "The transmission of a data packet has exceeded the maximum number of attempts")

        cls._register_trace(mactxfinaldatafailed)



    def __init__(self, ec, guid):
        super(NS3RraaWifiManager, self).__init__(ec, guid)
        self._home = "ns3-rraa-wifi-manager-%s" % self.guid
