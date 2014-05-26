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
class NS3AarfcdWifiManager(NS3BaseWifiRemoteStationManager):
    _rtype = "ns3::AarfcdWifiManager"

    @classmethod
    def _register_attributes(cls):
        
        attr_successk = Attribute("SuccessK",
            "Multiplication factor for the success threshold in the AARF algorithm.",
            type = Types.Double,
            default = "2",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_successk)

        attr_timerk = Attribute("TimerK",
            "Multiplication factor for the timer threshold in the AARF algorithm.",
            type = Types.Double,
            default = "2",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_timerk)

        attr_maxsuccessthreshold = Attribute("MaxSuccessThreshold",
            "Maximum value of the success threshold in the AARF algorithm.",
            type = Types.Integer,
            default = "60",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxsuccessthreshold)

        attr_mintimerthreshold = Attribute("MinTimerThreshold",
            "The minimum value for the \'timer\' threshold in the AARF algorithm.",
            type = Types.Integer,
            default = "15",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_mintimerthreshold)

        attr_minsuccessthreshold = Attribute("MinSuccessThreshold",
            "The minimum value for the success threshold in the AARF algorithm.",
            type = Types.Integer,
            default = "10",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minsuccessthreshold)

        attr_minrtswnd = Attribute("MinRtsWnd",
            "Minimum value for Rts window of Aarf-CD",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_minrtswnd)

        attr_maxrtswnd = Attribute("MaxRtsWnd",
            "Maximum value for Rts window of Aarf-CD",
            type = Types.Integer,
            default = "40",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_maxrtswnd)

        attr_turnoffrtsafterratedecrease = Attribute("TurnOffRtsAfterRateDecrease",
            "If true the RTS mechanism will be turned off when the rate will be decreased",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_turnoffrtsafterratedecrease)

        attr_turnonrtsafterrateincrease = Attribute("TurnOnRtsAfterRateIncrease",
            "If true the RTS mechanism will be turned on when the rate will be increased",
            type = Types.Bool,
            default = "True",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_turnonrtsafterrateincrease)

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
            "If  the size of the data packet + LLC header + MAC header + FCS trailer is bigger than this value, we use an RTS/CTS handshake before sending the data, as per IEEE Std. 802.11-2012, Section 9.3.5. This value will not have any effect on some rate control algorithms.",
            type = Types.Integer,
            default = "2346",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rtsctsthreshold)

        attr_fragmentationthreshold = Attribute("FragmentationThreshold",
            "If the size of the data packet + LLC header + MAC header + FCS trailer is biggerthan this value, we fragment it such that the size of the fragments are equal or smaller than this value, as per IEEE Std. 802.11-2012, Section 9.5. This value will not have any effect on some rate control algorithms.",
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
        super(NS3AarfcdWifiManager, self).__init__(ec, guid)
        self._home = "ns3-aarfcd-wifi-manager-%s" % self.guid
