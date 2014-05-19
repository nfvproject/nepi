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
from nepi.resources.ns3.ns3wifiphy import NS3BaseWifiPhy 

@clsinit_copy
class NS3YansWifiPhy(NS3BaseWifiPhy):
    _rtype = "ns3::YansWifiPhy"

    @classmethod
    def _register_attributes(cls):
        
        attr_energydetectionthreshold = Attribute("EnergyDetectionThreshold",
            "The energy of a received signal should be higher than this threshold (dbm) to allow the PHY layer to detect the signal.",
            type = Types.Double,
            default = "-96",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_energydetectionthreshold)

        attr_ccamode1threshold = Attribute("CcaMode1Threshold",
            "The energy of a received signal should be higher than this threshold (dbm) to allow the PHY layer to declare CCA BUSY state",
            type = Types.Double,
            default = "-99",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ccamode1threshold)

        attr_txgain = Attribute("TxGain",
            "Transmission gain (dB).",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_txgain)

        attr_rxgain = Attribute("RxGain",
            "Reception gain (dB).",
            type = Types.Double,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rxgain)

        attr_txpowerlevels = Attribute("TxPowerLevels",
            "Number of transmission power levels available between TxPowerStart and TxPowerEnd included.",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_txpowerlevels)

        attr_txpowerend = Attribute("TxPowerEnd",
            "Maximum available transmission level (dbm).",
            type = Types.Double,
            default = "16.0206",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_txpowerend)

        attr_txpowerstart = Attribute("TxPowerStart",
            "Minimum available transmission level (dbm).",
            type = Types.Double,
            default = "16.0206",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_txpowerstart)

        attr_rxnoisefigure = Attribute("RxNoiseFigure",
            "Loss (dB) in the Signal-to-Noise-Ratio due to non-idealities in the receiver. According to Wikipedia (http://en.wikipedia.org/wiki/Noise_figure), this is \"the difference in decibels (dB) between the noise output of the actual receiver to the noise output of an  ideal receiver with the same overall gain and bandwidth when the receivers  are connected to sources at the standard noise temperature T0 (usually 290 K)\". For",
            type = Types.Double,
            default = "7",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rxnoisefigure)

        attr_channelswitchdelay = Attribute("ChannelSwitchDelay",
            "Delay between two short frames transmitted on different frequencies.",
            type = Types.String,
            default = "+250000.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_channelswitchdelay)

        attr_channelnumber = Attribute("ChannelNumber",
            "Channel center frequency = Channel starting frequency + 5 MHz * nch",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_channelnumber)

        attr_frequency = Attribute("Frequency",
            "The operating frequency.",
            type = Types.Integer,
            default = "2407",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_frequency)

        attr_transmitters = Attribute("Transmitters",
            "The number of transmitters.",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_transmitters)

        attr_recievers = Attribute("Recievers",
            "The number of recievers.",
            type = Types.Integer,
            default = "1",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_recievers)

        attr_shortguardenabled = Attribute("ShortGuardEnabled",
            "Whether or not short guard interval is enabled.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_shortguardenabled)

        attr_ldpcenabled = Attribute("LdpcEnabled",
            "Whether or not LDPC is enabled.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_ldpcenabled)

        attr_stbcenabled = Attribute("STBCEnabled",
            "Whether or not STBC is enabled.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_stbcenabled)

        attr_greenfieldenabled = Attribute("GreenfieldEnabled",
            "Whether or not STBC is enabled.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_greenfieldenabled)

        attr_channelbonding = Attribute("ChannelBonding",
            "Whether 20MHz or 40MHz.",
            type = Types.Bool,
            default = "False",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_channelbonding)



    @classmethod
    def _register_traces(cls):
        
        phytxbegin = Trace("PhyTxBegin", "Trace source indicating a packet has begun transmitting over the channel medium")

        cls._register_trace(phytxbegin)

        phytxend = Trace("PhyTxEnd", "Trace source indicating a packet has been completely transmitted over the channel. NOTE: the only official WifiPhy implementation available to this date (YansWifiPhy) never fires this trace source.")

        cls._register_trace(phytxend)

        phytxdrop = Trace("PhyTxDrop", "Trace source indicating a packet has been dropped by the device during transmission")

        cls._register_trace(phytxdrop)

        phyrxbegin = Trace("PhyRxBegin", "Trace source indicating a packet has begun being received from the channel medium by the device")

        cls._register_trace(phyrxbegin)

        phyrxend = Trace("PhyRxEnd", "Trace source indicating a packet has been completely received from the channel medium by the device")

        cls._register_trace(phyrxend)

        phyrxdrop = Trace("PhyRxDrop", "Trace source indicating a packet has been dropped by the device during reception")

        cls._register_trace(phyrxdrop)

        monitorsnifferrx = Trace("MonitorSnifferRx", "Trace source simulating a wifi device in monitor mode sniffing all received frames")

        cls._register_trace(monitorsnifferrx)

        monitorsniffertx = Trace("MonitorSnifferTx", "Trace source simulating the capability of a wifi device in monitor mode to sniff all frames being transmitted")

        cls._register_trace(monitorsniffertx)



    def __init__(self, ec, guid):
        super(NS3YansWifiPhy, self).__init__(ec, guid)
        self._home = "ns3-yans-wifi-phy-%s" % self.guid
