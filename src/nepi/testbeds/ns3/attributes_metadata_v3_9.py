#!/usr/bin/env python
# -*- coding: utf-8 -*-

from factories_metadata_v3_9 import wifi_standards, l4_protocols, \
    service_flow_direction, service_flow_scheduling_type
import validation as ns3_validation
from nepi.core.attributes import Attribute
from nepi.util import validation

testbed_attributes = dict({
    "simu_impl_type": dict({
            "name": "SimulatorImplementationType",
            "help": "The object class to use as the simulator implementation",
            "type": Attribute.STRING,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_string
        }),
    "checksum": dict({
            "name": "ChecksumEnabled",
            "help": "A global switch to enable all checksums for all protocols",
            "type": Attribute.BOOL,
            "value": False,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_bool
        }),
    "simu_stop": dict({
        "name": "StopTime",
        "validation_function": validation.is_time,
        "value": None,
        "type": Attribute.STRING,
        "help": "Stop time for the simulation"
    }),
})

attributes = dict({
    "SleepCurrentA": dict({
        "name": "SleepCurrentA",
        "validation_function": validation.is_double,
        "value": 2.0000000000000002e-05,
        "type": Attribute.DOUBLE,
        "help": "The default radio Sleep current in Ampere."
    }),
    "Protocol": dict({
        "name": "Protocol",
        "validation_function": validation.is_string,
        "value": "ns3::UdpSocketFactory",
        "type": Attribute.STRING,
        "help": "The type of protocol to use."
    }),
    "TxCurrentA": dict({
        "name": "TxCurrentA",
        "validation_function": validation.is_double,
        "value": 0.017399999999999999,
        "type": Attribute.DOUBLE,
        "help": "The radio Tx current in Ampere."
    }),
    "BasicEnergySourceInitialEnergyJ": dict({
        "name": "BasicEnergySourceInitialEnergyJ",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "Initial energy stored in basic energy source."
    }),
    "FrameSize": dict({
        "name": "FrameSize",
        "validation_function": validation.is_integer,
        "value": 1000,
        "type": Attribute.INTEGER,
        "help": "Size of data frames in bytes"
    }),
    "RateStep": dict({
        "name": "RateStep",
        "validation_function": validation.is_integer,
        "value": 4,
        "type": Attribute.INTEGER,
        "help": "Increments available for rate assignment in bps"
    }),
    "Stop": dict({
        "name": "Stop",
        "validation_function": validation.is_time,
        "value": "0ns",
        "type": Attribute.STRING,
        "help": "The simulation time at which to tear down the device thread."
    }),
    "ChannelSwitchDelay": dict({
        "name": "ChannelSwitchDelay",
        "validation_function": validation.is_time,
        "value": "250000ns",
        "type": Attribute.STRING,
        "help": "Delay between two short frames transmitted on different frequencies. NOTE: Unused now."
    }),
    "Time": dict({
        "name": "Time",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "Change current direction and speed after moving for this delay."
    }),
    "ewndFor12mbps": dict({
        "name": "ewndFor12mbps",
        "validation_function": validation.is_integer,
        "value": 20,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 12 Mbs data mode"
    }),
    "BerThreshold": dict({
        "name": "BerThreshold",
        "validation_function": validation.is_double,
        "value": 1.0000000000000001e-05,
        "type": Attribute.DOUBLE,
        "help": "The maximum Bit Error Rate acceptable at any transmission mode"
    }),
    "Dot11MeshHWMPactivePathTimeout": dict({
        "name": "Dot11MeshHWMPactivePathTimeout",
        "validation_function": validation.is_time,
        "value": "5120000000ns",
        "type": Attribute.STRING,
        "help": "Lifetime of reactive routing information"
    }),
    "pmtlFor48mbps": dict({
        "name": "pmtlFor48mbps",
        "validation_function": validation.is_double,
        "value": 0.23000000000000001,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 48 Mbs data mode"
    }),
    "SystemLoss": dict({
        "name": "SystemLoss",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "The system loss"
    }),
    "ReferenceLoss": dict({
        "name": "ReferenceLoss",
        "validation_function": validation.is_double,
        "value": 46.677700000000002,
        "type": Attribute.DOUBLE,
        "help": "The reference loss at distance d0 (dB). (Default is Friis at 1m with 5.15 GHz)"
    }),
    "MaxQueueTime": dict({
        "name": "MaxQueueTime",
        "validation_function": validation.is_time,
        "value": "30000000000ns",
        "type": Attribute.STRING,
        "help": "Maximum time packets can be queued (in seconds)"
    }),
    "Dot11MeshHWMPactiveRootTimeout": dict({
        "name": "Dot11MeshHWMPactiveRootTimeout",
        "validation_function": validation.is_time,
        "value": "5120000000ns",
        "type": Attribute.STRING,
        "help": "Lifetime of poractive routing information"
    }),
    "DutyCycle": dict({
        "name": "DutyCycle",
        "validation_function": validation.is_double,
        "value": 0.5,
        "type": Attribute.DOUBLE,
        "help": "the duty cycle of the generator, i.e., the fraction of the period that is occupied by a signal"
    }),
    "DeviceName": dict({
        "name": "DeviceName",
        "validation_function": validation.is_string,
        "value": "eth1",
        "type": Attribute.STRING,
        "help": "The name of the underlying real device (e.g. eth1)."
    }),
    "Direction": dict({
        "name": "Direction",
        "validation_function": validation.is_string,
        "value": "Uniform:0:6.28318",
        "type": Attribute.STRING,
        "help": "A random variable used to pick the direction (gradients)."
    }),
    "OffTime": dict({
        "name": "OffTime",
        "validation_function": validation.is_string,
        "value": "Constant:1",
        "type": Attribute.STRING,
        "help": "A RandomVariable used to pick the duration of the 'Off' state."
    }),
    "UpdatePeriod": dict({
        "name": "UpdatePeriod",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "The interval between decisions about rate control changes"
    }),
    "DelayBinWidth": dict({
        "name": "DelayBinWidth",
        "validation_function": validation.is_double,
        "value": 0.001,
        "type": Attribute.DOUBLE,
        "help": "The width used in the delay histogram."
    }),
    "EnergyDetectionThreshold": dict({
        "name": "EnergyDetectionThreshold",
        "validation_function": validation.is_double,
        "value": -96.0,
        "type": Attribute.DOUBLE,
        "help": "The energy of a received signal should be higher than this threshold (dbm) to allow the PHY layer to detect the signal."
    }),
    "PacketSizeBinWidth": dict({
        "name": "PacketSizeBinWidth",
        "validation_function": validation.is_double,
        "value": 20.0,
        "type": Attribute.DOUBLE,
        "help": "The width used in the packetSize histogram."
    }),
    "Resolution": dict({
        "name": "Resolution",
        "validation_function": validation.is_time,
        "value": "1000000ns",
        "type": Attribute.STRING,
        "help": "the lengh of the time interval over which the power spectral density of incoming signals is averaged"
    }),
    "MaxX": dict({
        "name": "MaxX",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Maximum X value of traveling region, [m]"
    }),
    "IdleCurrentA": dict({
        "name": "IdleCurrentA",
        "validation_function": validation.is_double,
        "value": 0.000426,
        "type": Attribute.DOUBLE,
        "help": "The default radio Idle current in Ampere."
    }),
    "Netmask": dict({
        "name": "Netmask",
        "validation_function": validation.is_string,
        "value": "255.255.255.255",
        "type": Attribute.STRING,
        "help": "The network mask to assign to the tap device, when in ConfigureLocal mode. This address will override the discovered MAC address of the simulated device."
    }),
    "PathDiscoveryTime": dict({
        "name": "PathDiscoveryTime",
        "validation_function": validation.is_time,
        "value": "5599999999ns",
        "type": Attribute.STRING,
        "help": "Estimate of maximum time needed to find route in network = 2 * NetTraversalTime"
    }),
    "poriFor24mbps": dict({
        "name": "poriFor24mbps",
        "validation_function": validation.is_double,
        "value": 0.1681,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 24 Mbs data mode"
    }),
    "Exponent0": dict({
        "name": "Exponent0",
        "validation_function": validation.is_double,
        "value": 1.8999999999999999,
        "type": Attribute.DOUBLE,
        "help": "The exponent for the first field."
    }),
    "TimeStep": dict({
        "name": "TimeStep",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "Change current direction and speed after moving for this time."
    }),
    "MaxMissedBeacons": dict({
        "name": "MaxMissedBeacons",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Number of beacons which much be consecutively missed before we attempt to restart association."
    }),
    "RxGain": dict({
        "name": "RxGain",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Reception gain (dB)."
    }),
    "MaxRetries": dict({
        "name": "MaxRetries",
        "validation_function": validation.is_integer,
        "value": 4,
        "type": Attribute.INTEGER,
        "help": "Maximum number of retries"
    }),
    "pmtlFor24mbps": dict({
        "name": "pmtlFor24mbps",
        "validation_function": validation.is_double,
        "value": 0.26500000000000001,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 24 Mbs data mode"
    }),
    "TurnOnRtsAfterRateIncrease": dict({
        "name": "TurnOnRtsAfterRateIncrease",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "If true the RTS mechanism will be turned on when the rate will be increased"
    }),
    "Gain": dict({
        "name": "Gain",
        "validation_function": validation.is_double,
        "value": 0.10000000000000001,
        "type": Attribute.DOUBLE,
        "help": "XXX"
    }),
    "SuccessK": dict({
        "name": "SuccessK",
        "validation_function": validation.is_double,
        "value": 2.0,
        "type": Attribute.DOUBLE,
        "help": "Multiplication factor for the success threshold in the AARF algorithm."
    }),
    "MinTimerThreshold": dict({
        "name": "MinTimerThreshold",
        "validation_function": validation.is_integer,
        "value": 15,
        "type": Attribute.INTEGER,
        "help": "The minimum value for the 'timer' threshold in the AARF algorithm."
    }),
    "TimerThreshold": dict({
        "name": "TimerThreshold",
        "validation_function": validation.is_integer,
        "value": 15,
        "type": Attribute.INTEGER,
        "help": "The 'timer' threshold in the ARF algorithm."
    }),
    "poriFor36mbps": dict({
        "name": "poriFor36mbps",
        "validation_function": validation.is_double,
        "value": 0.115,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 36 Mbs data mode"
    }),
    "SlotTime": dict({
        "name": "SlotTime",
        "validation_function": validation.is_time,
        "value": "20000000ns",
        "type": Attribute.STRING,
        "help": "Time slot duration for MAC backoff"
    }),
    "DeltaX": dict({
        "name": "DeltaX",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "The x space between objects."
    }),
    "DeltaY": dict({
        "name": "DeltaY",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "The y space between objects."
    }),
    "Shipping": dict({
        "name": "Shipping",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "Shipping contribution to noise between 0 and 1"
    }),
    "HardLimit": dict({
        "name": "HardLimit",
        "validation_function": validation.is_time,
        "value": "100000000ns",
        "type": Attribute.STRING,
        "help": "Maximum acceptable real-time jitter (used in conjunction with SynchronizationMode=HardLimit)"
    }),
    "SupportedModesPhy2": dict({
        "name": "SupportedModesPhy2",
        "validation_function": validation.is_string,
        "value": "2|0|1|",
        "type": Attribute.STRING,
        "help": "List of modes supported by Phy2"
    }),
    "SupportedModesPhy1": dict({
        "name": "SupportedModesPhy1",
        "validation_function": validation.is_string,
        "value": "2|0|1|",
        "type": Attribute.STRING,
        "help": "List of modes supported by Phy1"
    }),
    "TxGain": dict({
        "name": "TxGain",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Transmission gain (dB)."
    }),
    "MaxPropDelay": dict({
        "name": "MaxPropDelay",
        "validation_function": validation.is_time,
        "value": "2000000000ns",
        "type": Attribute.STRING,
        "help": "Maximum possible propagation delay to gateway"
    }),
    "Alpha": dict({
        "name": "Alpha",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "A constant representing the tunable parameter in the Gauss-Markov model."
    }),
    "X": dict({
        "name": "X",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The x coordinate of the center of the  disc."
    }),
    "ExpirationTime": dict({
        "name": "ExpirationTime",
        "validation_function": validation.is_time,
        "value": "30000000000ns",
        "type": Attribute.STRING,
        "help": "Time it takes for learned MAC state entry to expire."
    }),
    "GratuitousReply": dict({
        "name": "GratuitousReply",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Indicates whether a gratuitous RREP should be unicast to the node originated route discovery."
    }),
    "CcaThreshold": dict({
        "name": "CcaThreshold",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "Aggregate energy of incoming signals to move to CCA Busy state dB"
    }),
    "AllowedHelloLoss": dict({
        "name": "AllowedHelloLoss",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "Number of hello messages which may be loss for valid link."
    }),
    "Wind": dict({
        "name": "Wind",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Wind speed in m/s"
    }),
    "Exponent1": dict({
        "name": "Exponent1",
        "validation_function": validation.is_double,
        "value": 3.7999999999999998,
        "type": Attribute.DOUBLE,
        "help": "The exponent for the second field."
    }),
    "DefaultTtl": dict({
        "name": "DefaultTtl",
        "validation_function": validation.is_integer,
        "value": 64,
        "type": Attribute.INTEGER,
        "help": "The TTL value set by default on all outgoing packets generated on this node."
    }),
    "TxPowerEnd": dict({
        "name": "TxPowerEnd",
        "validation_function": validation.is_double,
        "value": 16.020600000000002,
        "type": Attribute.DOUBLE,
        "help": "Maximum available transmission level (dbm)."
    }),
    "DataRate": dict({
        "name": "DataRate",
        "validation_function": validation.is_string,
        "value": "32768bps",
        "type": Attribute.STRING,
        "help": "The default data rate for point to point links"
    }),
    "MaxSuccessThreshold": dict({
        "name": "MaxSuccessThreshold",
        "validation_function": validation.is_integer,
        "value": 60,
        "type": Attribute.INTEGER,
        "help": "Maximum value of the success threshold in the AARF algorithm."
    }),
    "MaxRangCorrectionRetries": dict({
        "name": "MaxRangCorrectionRetries",
        "validation_function": validation.is_integer,
        "value": 16,
        "type": Attribute.INTEGER,
        "help": "Number of retries on contention Ranging Requests"
    }),
    "Dot11MeshHWMPpreqMinInterval": dict({
        "name": "Dot11MeshHWMPpreqMinInterval",
        "validation_function": validation.is_time,
        "value": "102400000ns",
        "type": Attribute.STRING,
        "help": "Minimal interval between to successive PREQs"
    }),
    "BlackListTimeout": dict({
        "name": "BlackListTimeout",
        "validation_function": validation.is_time,
        "value": "5599999999ns",
        "type": Attribute.STRING,
        "help": "Time for which the node is put into the blacklist = RreqRetries * NetTraversalTime"
    }),
    "MaxBytes": dict({
        "name": "MaxBytes",
        "validation_function": validation.is_integer,
        "value": 6553500,
        "type": Attribute.INTEGER,
        "help": "The maximum number of bytes accepted by this DropTailQueue."
    }),
    "MaxAmsduSize": dict({
        "name": "MaxAmsduSize",
        "validation_function": validation.is_integer,
        "value": 7935,
        "type": Attribute.INTEGER,
        "help": "Max length in byte of an A-MSDU"
    }),
    "Distance2": dict({
        "name": "Distance2",
        "validation_function": validation.is_double,
        "value": 200.0,
        "type": Attribute.DOUBLE,
        "help": "Beginning of the third distance field. Default is 200m."
    }),
    "MaxFrames": dict({
        "name": "MaxFrames",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "Maximum number of frames to include in a single RTS"
    }),
    "RxGainPhy2": dict({
        "name": "RxGainPhy2",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "Gain added to incoming signal at receiver of Phy2"
    }),
    "LayoutType": dict({
        "name": "LayoutType",
        "validation_function": validation.is_enum,
        "value": "RowFirst",
        "allowed": ["RowFirst",
            "ColumnFirst"],
        "type": Attribute.ENUM,
        "help": "The type of layout."
    }),
    "ewndFor54mbps": dict({
        "name": "ewndFor54mbps",
        "validation_function": validation.is_integer,
        "value": 40,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 54 Mbs data mode"
    }),
    "FailureThreshold": dict({
        "name": "FailureThreshold",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "The number of consecutive transmissions failure to decrease the rate."
    }),
    "ewndFor24mbps": dict({
        "name": "ewndFor24mbps",
        "validation_function": validation.is_integer,
        "value": 40,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 24 Mbs data mode"
    }),
    "ewndFor48mbps": dict({
        "name": "ewndFor48mbps",
        "validation_function": validation.is_integer,
        "value": 40,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 48 Mbs data mode"
    }),
    "SendEnable": dict({
        "name": "SendEnable",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Enable or disable the transmitter section of the device."
    }),
    "DataMode": dict({
        "name": "DataMode",
        "validation_function": validation.is_string,
        "value": "OfdmRate6Mbps",
        "type": Attribute.STRING,
        "help": "The transmission mode to use for every data packet transmission"
    }),
    "ErrorUnit": dict({
        "name": "ErrorUnit",
        "validation_function": validation.is_enum,
        "value": "EU_BYTE",
        "allowed": ["EU_BYTE",
     "EU_PKT",
     "EU_BIT"],
        "type": Attribute.ENUM,
        "help": "The error unit"
    }),
    "IpAddress": dict({
        "name": "IpAddress",
        "validation_function": validation.is_ip4_address,
        "value": None,
        "type": Attribute.STRING,
        "help": "The IP address to assign to the tap device,  when in ConfigureLocal mode. This address will override the discovered IP address of the simulated device."
    }),
    "MinSuccessThreshold": dict({
        "name": "MinSuccessThreshold",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "The minimum value for the success threshold in the AARF algorithm."
    }),
    "NodeTraversalTime": dict({
        "name": "NodeTraversalTime",
        "validation_function": validation.is_time,
        "value": "40000000ns",
        "type": Attribute.STRING,
        "help": "Conservative estimate of the average one hop traversal time for packets and should include queuing delays, interrupt processing times and transfer times."
    }),
    "TxPowerPhy2": dict({
        "name": "TxPowerPhy2",
        "validation_function": validation.is_double,
        "value": 190.0,
        "type": Attribute.DOUBLE,
        "help": "Transmission output power in dB of Phy2"
    }),
    "TxPowerPhy1": dict({
        "name": "TxPowerPhy1",
        "validation_function": validation.is_double,
        "value": 190.0,
        "type": Attribute.DOUBLE,
        "help": "Transmission output power in dB of Phy1"
    }),
    "ReceiveEnable": dict({
        "name": "ReceiveEnable",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Enable or disable the receiver section of the device."
    }),
    "Lambda": dict({
        "name": "Lambda",
        "validation_function": validation.is_double,
        "value": 0.058252400000000003,
        "type": Attribute.DOUBLE,
        "help": "The wavelength  (default is 5.15 GHz at 300 000 km/s)."
    }),
    "ewndFor6mbps": dict({
        "name": "ewndFor6mbps",
        "validation_function": validation.is_integer,
        "value": 6,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 6 Mbs data mode"
    }),
    "NumberOfRaysPerPath": dict({
        "name": "NumberOfRaysPerPath",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "The number of rays to use by default for compute the fading coeficent for a given path (default is 1)"
    }),
    "HnaInterval": dict({
        "name": "HnaInterval",
        "validation_function": validation.is_time,
        "value": "5000000000ns",
        "type": Attribute.STRING,
        "help": "HNA messages emission interval.  Normally it is equal to TcInterval."
    }),
    "RanVar": dict({
        "name": "RanVar",
        "validation_function": validation.is_string,
        "value": "Uniform:0:1",
        "type": Attribute.STRING,
        "help": "The decision variable attached to this error model."
    }),
    "Theta": dict({
        "name": "Theta",
        "validation_function": validation.is_string,
        "value": "Uniform:0:6.283",
        "type": Attribute.STRING,
        "help": "A random variable which represents the angle (gradients) of a position in a random disc."
    }),
    "UpdateStatistics": dict({
        "name": "UpdateStatistics",
        "validation_function": validation.is_time,
        "value": "100000000ns",
        "type": Attribute.STRING,
        "help": "The interval between updating statistics table "
    }),
    "Distance1": dict({
        "name": "Distance1",
        "validation_function": validation.is_double,
        "value": 80.0,
        "type": Attribute.DOUBLE,
        "help": "Beginning of the second distance field. Default is 80m."
    }),
    "MyRouteTimeout": dict({
        "name": "MyRouteTimeout",
        "validation_function": validation.is_time,
        "value": "11199999999ns",
        "type": Attribute.STRING,
        "help": "Value of lifetime field in RREP generating by this node = 2 * max(ActiveRouteTimeout, PathDiscoveryTime)"
    }),
    "RcvBufSize": dict({
        "name": "RcvBufSize",
        "validation_function": validation.is_integer,
        "value": 131072,
        "type": Attribute.INTEGER,
        "help": "PacketSocket maximum receive buffer size (bytes)"
    }),
    "RreqRetries": dict({
        "name": "RreqRetries",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "Maximum number of retransmissions of RREQ to discover a route"
    }),
    "MaxNumberOfPeerLinks": dict({
        "name": "MaxNumberOfPeerLinks",
        "validation_function": validation.is_integer,
        "value": 32,
        "type": Attribute.INTEGER,
        "help": "Maximum number of peer links"
    }),
    "QueueLimit": dict({
        "name": "QueueLimit",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Maximum packets to queue at MAC"
    }),
    "MinSpeed": dict({
        "name": "MinSpeed",
        "validation_function": validation.is_double,
        "value": 0.29999999999999999,
        "type": Attribute.DOUBLE,
        "help": "Minimum speed value, [m/s]"
    }),
    "MaxSpeed": dict({
        "name": "MaxSpeed",
        "validation_function": validation.is_double,
        "value": 0.69999999999999996,
        "type": Attribute.DOUBLE,
        "help": "Maximum speed value, [m/s]"
    }),
    "NumberOfRetryRates": dict({
        "name": "NumberOfRetryRates",
        "validation_function": validation.is_integer,
        "value": 100,
        "type": Attribute.INTEGER,
        "help": "Number of retry rates"
    }),
    "MaxPacketSize": dict({
        "name": "MaxPacketSize",
        "validation_function": validation.is_integer,
        "value": 1024,
        "type": Attribute.INTEGER,
        "help": "The maximum size of a packet."
    }),
    "TxPowerLevels": dict({
        "name": "TxPowerLevels",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "Number of transmission power levels available between TxPowerBase and TxPowerEnd included."
    }),
    "RandomStart": dict({
        "name": "RandomStart",
        "validation_function": validation.is_time,
        "value": "500000000ns",
        "type": Attribute.STRING,
        "help": "Window when beacon generating starts (uniform random) in seconds"
    }),
    "SampleColumn": dict({
        "name": "SampleColumn",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "The number of columns used for sampling"
    }),
    "NormalDirection": dict({
        "name": "NormalDirection",
        "validation_function": validation.is_string,
        "value": "Normal:0:1:10",
        "type": Attribute.STRING,
        "help": "A gaussian random variable used to calculate the next direction value."
    }),
    "MinPause": dict({
        "name": "MinPause",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "Minimum pause value, [s]"
    }),
    "TcInterval": dict({
        "name": "TcInterval",
        "validation_function": validation.is_time,
        "value": "5000000000ns",
        "type": Attribute.STRING,
        "help": "TC messages emission interval."
    }),
    "RfFlag": dict({
        "name": "RfFlag",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Reply and forward flag"
    }),
    "CcaThresholdPhy2": dict({
        "name": "CcaThresholdPhy2",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "Aggregate energy of incoming signals to move to CCA Busy state dB of Phy2"
    }),
    "CcaThresholdPhy1": dict({
        "name": "CcaThresholdPhy1",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "Aggregate energy of incoming signals to move to CCA Busy state dB of Phy1"
    }),
    "MaxQueueLen": dict({
        "name": "MaxQueueLen",
        "validation_function": validation.is_integer,
        "value": 64,
        "type": Attribute.INTEGER,
        "help": "Maximum number of packets that we allow a routing protocol to buffer."
    }),
    "HeightAboveZ": dict({
        "name": "HeightAboveZ",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The height of the antenna (m) above the node's Z coordinate"
    }),
    "poriFor9mbps": dict({
        "name": "poriFor9mbps",
        "validation_function": validation.is_double,
        "value": 0.1434,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 9 Mbs data mode"
    }),
    "BasicEnergySupplyVoltageV": dict({
        "name": "BasicEnergySupplyVoltageV",
        "validation_function": validation.is_double,
        "value": 3.0,
        "type": Attribute.DOUBLE,
        "help": "Initial supply voltage for basic energy source."
    }),
    "LostUlMapInterval": dict({
        "name": "LostUlMapInterval",
        "validation_function": validation.is_time,
        "value": "500000000ns",
        "type": Attribute.STRING,
        "help": "Time since last received UL-MAP before uplink synchronization is considered lost, maximum is 600."
    }),
    "UnicastPreqThreshold": dict({
        "name": "UnicastPreqThreshold",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "Maximum number of PREQ receivers, when we send a PREQ as a chain of unicasts"
    }),
    "poriFor48mbps": dict({
        "name": "poriFor48mbps",
        "validation_function": validation.is_double,
        "value": 0.047,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 48 Mbs data mode"
    }),
    "pmtlFor54mbps": dict({
        "name": "pmtlFor54mbps",
        "validation_function": validation.is_double,
        "value": 0.094,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 54 Mbs data mode"
    }),
    "BeaconInterval": dict({
        "name": "BeaconInterval",
        "validation_function": validation.is_time,
        "value": "102400000ns",
        "type": Attribute.STRING,
        "help": "Delay between two beacons"
    }),
    "IntervalT20": dict({
        "name": "IntervalT20",
        "validation_function": validation.is_time,
        "value": "500000000ns",
        "type": Attribute.STRING,
        "help": "Time the SS searches for preambles on a given channel. Minimum is 2 MAC frames"
    }),
    "IntervalT21": dict({
        "name": "IntervalT21",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "time the SS searches for (decodable) DL-MAP on a given channel"
    }),
    "MeanPitch": dict({
        "name": "MeanPitch",
        "validation_function": validation.is_string,
        "value": "Constant:0",
        "type": Attribute.STRING,
        "help": "A random variable used to assign the average pitch."
    }),
    "Dot11MeshHWMPrannInterval": dict({
        "name": "Dot11MeshHWMPrannInterval",
        "validation_function": validation.is_time,
        "value": "5120000000ns",
        "type": Attribute.STRING,
        "help": "Lifetime of poractive routing information"
    }),
    "Distribution": dict({
        "name": "Distribution",
        "validation_function": validation.is_string,
        "value": "Constant:1",
        "type": Attribute.STRING,
        "help": "The distribution to choose the initial phases."
    }),
    "RxThreshold": dict({
        "name": "RxThreshold",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "Required SNR for signal acquisition in dB"
    }),
    "WaypointsLeft": dict({
        "name": "WaypointsLeft",
        "validation_function": validation.is_integer,
        "value": 0,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The number of waypoints remaining."
    }),
    "ConfirmTimeout": dict({
        "name": "ConfirmTimeout",
        "validation_function": validation.is_time,
        "value": "40960000ns",
        "type": Attribute.STRING,
        "help": "Confirm timeout"
    }),
    "ActiveRouteTimeout": dict({
        "name": "ActiveRouteTimeout",
        "validation_function": validation.is_time,
        "value": "3000000000ns",
        "type": Attribute.STRING,
        "help": "Period of time during which the route is considered to be valid"
    }),
    "InitialRangInterval": dict({
        "name": "InitialRangInterval",
        "validation_function": validation.is_time,
        "value": "50000000ns",
        "type": Attribute.STRING,
        "help": "Time between Initial Ranging regions assigned by the BS. Maximum is 2s"
    }),
    "ewndFor18mbps": dict({
        "name": "ewndFor18mbps",
        "validation_function": validation.is_integer,
        "value": 20,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 18 Mbs data mode"
    }),
    "FlowInterruptionsBinWidth": dict({
        "name": "FlowInterruptionsBinWidth",
        "validation_function": validation.is_double,
        "value": 0.25,
        "type": Attribute.DOUBLE,
        "help": "The width used in the flowInterruptions histogram."
    }),
    "MinY": dict({
        "name": "MinY",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The y coordinate where the grid starts."
    }),
    "poriFor12mbps": dict({
        "name": "poriFor12mbps",
        "validation_function": validation.is_double,
        "value": 0.18609999999999999,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 12 Mbs data mode"
    }),
    "UnicastDataThreshold": dict({
        "name": "UnicastDataThreshold",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "Maximum number ofbroadcast receivers, when we send a broadcast as a chain of unicasts"
    }),
    "SuccessRatio": dict({
        "name": "SuccessRatio",
        "validation_function": validation.is_double,
        "value": 0.10000000000000001,
        "type": Attribute.DOUBLE,
        "help": "Ratio of maximum erroneous transmissions needed to switch to a higher rate"
    }),
    "SupportedModes": dict({
        "name": "SupportedModes",
        "validation_function": validation.is_string,
        "value": "2|0|1|",
        "type": Attribute.STRING,
        "help": "List of modes supported by this PHY"
    }),
    "CaptureSize": dict({
        "name": "CaptureSize",
        "validation_function": validation.is_integer,
        "value": 65535,
        "type": Attribute.INTEGER,
        "help": "Maximum length of captured packets (cf. pcap snaplen)"
    }),
    "NetTraversalTime": dict({
        "name": "NetTraversalTime",
        "validation_function": validation.is_time,
        "value": "2799999999ns",
        "type": Attribute.STRING,
        "help": "Estimate of the average net traversal time = 2 * NodeTraversalTime * NetDiameter"
    }),
    "Lifetime": dict({
        "name": "Lifetime",
        "validation_function": validation.is_time,
        "value": "120000000000ns",
        "type": Attribute.STRING,
        "help": "The lifetime of the routing enrty"
    }),
    "DeletePeriod": dict({
        "name": "DeletePeriod",
        "validation_function": validation.is_time,
        "value": "15000000000ns",
        "type": Attribute.STRING,
        "help": "DeletePeriod is intended to provide an upper bound on the time for which an upstream node A can have a neighbor B as an active next hop for destination D, while B has invalidated the route to D. = 5 * max (HelloInterval, ActiveRouteTimeout)"
    }),
    "MaxPerHopDelay": dict({
        "name": "MaxPerHopDelay",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "The maximum per-hop delay that should be considered.  Packets still not received after this delay are to be considered lost."
    }),
    "NumberOfOscillatorsPerRay": dict({
        "name": "NumberOfOscillatorsPerRay",
        "validation_function": validation.is_integer,
        "value": 4,
        "type": Attribute.INTEGER,
        "help": "The number of oscillators to use by default for compute the coeficent for a given ray of a given path (default is 4)"
    }),
    "MinRetryRate": dict({
        "name": "MinRetryRate",
        "validation_function": validation.is_double,
        "value": 0.01,
        "type": Attribute.DOUBLE,
        "help": "Smallest allowed RTS retry rate"
    }),
    "Pause": dict({
        "name": "Pause",
        "validation_function": validation.is_string,
        "value": "Constant:2",
        "type": Attribute.STRING,
        "help": "A random variable used to pick the pause of a random waypoint model."
    }),
    "Exponent": dict({
        "name": "Exponent",
        "validation_function": validation.is_double,
        "value": 3.0,
        "type": Attribute.DOUBLE,
        "help": "The exponent of the Path Loss propagation model"
    }),
    "MidInterval": dict({
        "name": "MidInterval",
        "validation_function": validation.is_time,
        "value": "5000000000ns",
        "type": Attribute.STRING,
        "help": "MID messages emission interval.  Normally it is equal to TcInterval."
    }),
    "pmtlFor9mbps": dict({
        "name": "pmtlFor9mbps",
        "validation_function": validation.is_double,
        "value": 0.39319999999999999,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 9 Mbs data mode"
    }),
    "Dot11MeshHWMPnetDiameterTraversalTime": dict({
        "name": "Dot11MeshHWMPnetDiameterTraversalTime",
        "validation_function": validation.is_time,
        "value": "102400000ns",
        "type": Attribute.STRING,
        "help": "Time we suppose the packet to go from one edge of the network to another"
    }),
    "TxPowerStart": dict({
        "name": "TxPowerStart",
        "validation_function": validation.is_double,
        "value": 16.020600000000002,
        "type": Attribute.DOUBLE,
        "help": "Minimum available transmission level (dbm)."
    }),
    "ewndFor9mbps": dict({
        "name": "ewndFor9mbps",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 9 Mbs data mode"
    }),
    "IntervalT12": dict({
        "name": "IntervalT12",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "Wait for UCD descriptor.Maximum is 5*MaxUcdInterval"
    }),
    "NormalPitch": dict({
        "name": "NormalPitch",
        "validation_function": validation.is_string,
        "value": "Normal:0:1:10",
        "type": Attribute.STRING,
        "help": "A gaussian random variable used to calculate the next pitch value."
    }),
    "PacketWindowSize": dict({
        "name": "PacketWindowSize",
        "validation_function": validation.is_integer,
        "value": 32,
        "type": Attribute.INTEGER,
        "help": "The size of the window used to compute the packet loss. This value should be a multiple of 8."
    }),
    "Start": dict({
        "name": "Start",
        "validation_function": validation.is_time,
        "value": "0ns",
        "type": Attribute.STRING,
        "help": "The simulation time at which to spin up the device thread."
    }),
    "MaxDcdInterval": dict({
        "name": "MaxDcdInterval",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "Maximum time between transmission of DCD messages. Maximum is 10s"
    }),
    "ChannelNumber": dict({
        "name": "ChannelNumber",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "Channel center frequency = Channel starting frequency + 5 MHz * (nch - 1)"
    }),
    "MaxPacketFailure": dict({
        "name": "MaxPacketFailure",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "Maximum number of failed packets before link will be closed"
    }),
    "AddCreditThreshold": dict({
        "name": "AddCreditThreshold",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Add credit threshold"
    }),
    "Basic": dict({
        "name": "Basic",
        "validation_function": validation.is_bool,
        "value": False,
        "type": Attribute.BOOL,
        "help": "If true the RRAA-BASIC algorithm will be used, otherwise the RRAA wil be used"
    }),
    "UcdInterval": dict({
        "name": "UcdInterval",
        "validation_function": validation.is_time,
        "value": "3000000000ns",
        "type": Attribute.STRING,
        "help": "Time between transmission of UCD messages. Maximum value is 10s."
    }),
    "DestinationOnly": dict({
        "name": "DestinationOnly",
        "validation_function": validation.is_bool,
        "value": False,
        "type": Attribute.BOOL,
        "help": "Indicates only the destination may respond to this RREQ."
    }),
    "Local": dict({
        "name": "Local",
        "validation_function": ns3_validation.is_address,
        "value": None,
        "type": Attribute.STRING,
        "help": "The Address on which to Bind the rx socket."
    }),
    "NumberOfNodes": dict({
        "name": "NumberOfNodes",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Number of non-gateway nodes in this gateway's neighborhood"
    }),
    "MaxPause": dict({
        "name": "MaxPause",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "Maximum pause value, [s]"
    }),
    "MaxBeaconLoss": dict({
        "name": "MaxBeaconLoss",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "Maximum number of lost beacons before link will be closed"
    }),
    "MaxY": dict({
        "name": "MaxY",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Maximum Y value of traveling region, [m]"
    }),
    "MaxReservations": dict({
        "name": "MaxReservations",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Maximum number of reservations to accept per cycle"
    }),
    "OnTime": dict({
        "name": "OnTime",
        "validation_function": validation.is_string,
        "value": "Constant:1",
        "type": Attribute.STRING,
        "help": "A RandomVariable used to pick the duration of the 'On' state."
    }),
    "RxGainPhy1": dict({
        "name": "RxGainPhy1",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "Gain added to incoming signal at receiver of Phy1"
    }),
    "Gateway": dict({
        "name": "Gateway",
        "validation_function": validation.is_ip4_address,
        "value": None,
        "type": Attribute.STRING,
        "help": "The IP address of the default gateway to assign to the host machine, when in ConfigureLocal mode."
    }),
    "GridWidth": dict({
        "name": "GridWidth",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "The number of objects layed out on a line."
    }),
    "NormalVelocity": dict({
        "name": "NormalVelocity",
        "validation_function": validation.is_string,
        "value": "Normal:0:1:10",
        "type": Attribute.STRING,
        "help": "A gaussian random variable used to calculate the next velocity value."
    }),
    "ReferenceDistance": dict({
        "name": "ReferenceDistance",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "The distance at which the reference loss is calculated (m)"
    }),
    "m1": dict({
        "name": "m1",
        "validation_function": validation.is_double,
        "value": 0.75,
        "type": Attribute.DOUBLE,
        "help": "m1 for distances smaller than Distance2. Default is 0.75."
    }),
    "m0": dict({
        "name": "m0",
        "validation_function": validation.is_double,
        "value": 1.5,
        "type": Attribute.DOUBLE,
        "help": "m0 for distances smaller than Distance1. Default is 1.5."
    }),
    "BroadcastInterval": dict({
        "name": "BroadcastInterval",
        "validation_function": validation.is_time,
        "value": "5000000000ns",
        "type": Attribute.STRING,
        "help": "How often we must send broadcast packets"
    }),
    "Variable": dict({
        "name": "Variable",
        "validation_function": validation.is_string,
        "value": "Uniform:0:1",
        "type": Attribute.STRING,
        "help": "The random variable which generates random delays (s)."
    }),
    "MacAddress": dict({
        "name": "MacAddress",
        "validation_function": validation.is_string,
        "value": "ff:ff:ff:ff:ff:ff",
        "type": Attribute.STRING,
        "help": "The MAC address to assign to the tap device, when in ConfigureLocal mode. This address will override the discovered MAC address of the simulated device."
    }),
    "MaxBeaconShiftValue": dict({
        "name": "MaxBeaconShiftValue",
        "validation_function": validation.is_integer,
        "value": 15,
        "type": Attribute.INTEGER,
        "help": "Maximum number of TUs for beacon shifting"
    }),
    "MeanDirection": dict({
        "name": "MeanDirection",
        "validation_function": validation.is_string,
        "value": "Uniform:0:6.28319",
        "type": Attribute.STRING,
        "help": "A random variable used to assign the average direction."
    }),
    "NextHopWait": dict({
        "name": "NextHopWait",
        "validation_function": validation.is_time,
        "value": "50000000ns",
        "type": Attribute.STRING,
        "help": "Period of our waiting for the neighbour's RREP_ACK = 10 ms + NodeTraversalTime"
    }),
    "EnableBeaconCollisionAvoidance": dict({
        "name": "EnableBeaconCollisionAvoidance",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Enable/Disable Beacon collision avoidance."
    }),
    "TimeoutBuffer": dict({
        "name": "TimeoutBuffer",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "Its purpose is to provide a buffer for the timeout so that if the RREP is delayed due to congestion, a timeout is less likely to occur while the RREP is still en route back to the source."
    }),
    "PeriodicEnergyUpdateInterval": dict({
        "name": "PeriodicEnergyUpdateInterval",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "Time between two consecutive periodic energy updates."
    }),
    "RxCurrentA": dict({
        "name": "RxCurrentA",
        "validation_function": validation.is_double,
        "value": 0.019699999999999999,
        "type": Attribute.DOUBLE,
        "help": "The radio Rx current in Ampere."
    }),
    "LocalIpv6": dict({
        "name": "LocalIpv6",
        "validation_function": validation.is_string,
        "value": "0000:0000:0000:0000:0000:0000:0000:0000",
        "type": Attribute.STRING,
        "help": "Local Ipv6Address of the sender"
    }),
    "Remote": dict({
        "name": "Remote",
        "validation_function": ns3_validation.is_address,
        "value": None,
        "type": Attribute.STRING,
        "help": "The address of the destination"
    }),
    "SSAntennaHeight": dict({
        "name": "SSAntennaHeight",
        "validation_function": validation.is_double,
        "value": 3.0,
        "type": Attribute.DOUBLE,
        "help": " SS Antenna Height (default is 3m)."
    }),
    "MeanVelocity": dict({
        "name": "MeanVelocity",
        "validation_function": validation.is_string,
        "value": "Uniform:0:1",
        "type": Attribute.STRING,
        "help": "A random variable used to assign the average velocity."
    }),
    "NumberOfRates": dict({
        "name": "NumberOfRates",
        "validation_function": validation.is_integer,
        "value": 0,
        "type": Attribute.INTEGER,
        "help": "Number of rate divisions supported by each PHY"
    }),
    "BSAntennaHeight": dict({
        "name": "BSAntennaHeight",
        "validation_function": validation.is_double,
        "value": 50.0,
        "type": Attribute.DOUBLE,
        "help": " BS Antenna Height (default is 50m)."
    }),
    "Interval": dict({
        "name": "Interval",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "The time to wait between packets"
    }),
    "CcaMode1Threshold": dict({
        "name": "CcaMode1Threshold",
        "validation_function": validation.is_double,
        "value": -99.0,
        "type": Attribute.DOUBLE,
        "help": "The energy of a received signal should be higher than this threshold (dbm) to allow the PHY layer to declare CCA BUSY state"
    }),
    "Mtu": dict({
        "name": "Mtu",
        "validation_function": validation.is_integer,
        "value": 1500,
        "type": Attribute.INTEGER,
        "help": "The MAC-level Maximum Transmission Unit"
    }),
    "pmtlFor12mbps": dict({
        "name": "pmtlFor12mbps",
        "validation_function": validation.is_double,
        "value": 0.2868,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 12 Mbs data mode"
    }),
    "MaxRtsWnd": dict({
        "name": "MaxRtsWnd",
        "validation_function": validation.is_integer,
        "value": 40,
        "type": Attribute.INTEGER,
        "help": "Maximum value for Rts window of Aarf-CD"
    }),
    "HoldingTimeout": dict({
        "name": "HoldingTimeout",
        "validation_function": validation.is_time,
        "value": "40960000ns",
        "type": Attribute.STRING,
        "help": "Holding timeout"
    }),
    "AssocRequestTimeout": dict({
        "name": "AssocRequestTimeout",
        "validation_function": validation.is_time,
        "value": "500000000ns",
        "type": Attribute.STRING,
        "help": "The interval between two consecutive assoc request attempts."
    }),
    "Timeout": dict({
        "name": "Timeout",
        "validation_function": validation.is_time,
        "value": "50000000ns",
        "type": Attribute.STRING,
        "help": "Timeout for the RRAA BASIC loss estimaton block (s)"
    }),
    "Dot11MeshHWMPmaxPREQretries": dict({
        "name": "Dot11MeshHWMPmaxPREQretries",
        "validation_function": validation.is_integer,
        "value": 3,
        "type": Attribute.INTEGER,
        "help": "Maximum number of retries before we suppose the destination to be unreachable"
    }),
    "Z": dict({
        "name": "Z",
        "validation_function": validation.is_string,
        "value": "Uniform:0:1",
        "type": Attribute.STRING,
        "help": "A random variable which represents the z coordinate of a position in a random box."
    }),
    "CW": dict({
        "name": "CW",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "The MAC parameter CW"
    }),
    "MaxPacketNumber": dict({
        "name": "MaxPacketNumber",
        "validation_function": validation.is_integer,
        "value": 400,
        "type": Attribute.INTEGER,
        "help": "If a packet arrives when there are already this number of packets, it is dropped."
    }),
    "RemoteIpv6": dict({
        "name": "RemoteIpv6",
        "validation_function": validation.is_string,
        "value": "0000:0000:0000:0000:0000:0000:0000:0000",
        "type": Attribute.STRING,
        "help": "The Ipv6Address of the outbound packets"
    }),
    "RttEstimatorFactory": dict({
        "name": "RttEstimatorFactory",
        "validation_function": validation.is_string,
        "value": "ns3::RttMeanDeviation[]",
        "type": Attribute.STRING,
        "help": "How RttEstimator objects are created."
    }),
    "TxPower": dict({
        "name": "TxPower",
        "validation_function": validation.is_double,
        "value": 190.0,
        "type": Attribute.DOUBLE,
        "help": "Transmission output power in dB"
    }),
    "pmtlFor36mbps": dict({
        "name": "pmtlFor36mbps",
        "validation_function": validation.is_double,
        "value": 0.33629999999999999,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 36 Mbs data mode"
    }),
    "MinRtsWnd": dict({
        "name": "MinRtsWnd",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "Minimum value for Rts window of Aarf-CD"
    }),
    "Frequency": dict({
        "name": "Frequency",
        "validation_function": validation.is_double,
        "value": 2300000000.0,
        "type": Attribute.DOUBLE,
        "help": "The Frequency  (default is 2.3 GHz)."
    }),
    "Willingness": dict({
        "name": "Willingness",
        "validation_function": validation.is_enum,
        "value": "default",
        "allowed": ["never",
     "low",
     "default",
     "high",
     "always"],
        "type": Attribute.ENUM,
        "help": "Willingness of a node to carry and forward traffic for other nodes."
    }),
    "DoFlag": dict({
        "name": "DoFlag",
        "validation_function": validation.is_bool,
        "value": False,
        "type": Attribute.BOOL,
        "help": "Destination only HWMP flag"
    }),
    "BlockAckThreshold": dict({
        "name": "BlockAckThreshold",
        "validation_function": validation.is_integer,
        "value": 0,
        "type": Attribute.INTEGER,
        "help": "If number of packets in this queue reaches this value, block ack mechanism is used. If this value is 0, block ack is never used."
    }),
    "TimerK": dict({
        "name": "TimerK",
        "validation_function": validation.is_double,
        "value": 2.0,
        "type": Attribute.DOUBLE,
        "help": "Multiplication factor for the timer threshold in the AARF algorithm."
    }),
    "Period": dict({
        "name": "Period",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "the period (=1/frequency)"
    }),
    "Library": dict({
        "name": "Library",
        "validation_function": validation.is_string,
        "value": "liblinux2.6.26.so",
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "Set the linux library to be used to create the stack"
    }),
    "DcdInterval": dict({
        "name": "DcdInterval",
        "validation_function": validation.is_time,
        "value": "3000000000ns",
        "type": Attribute.STRING,
        "help": "Time between transmission of DCD messages. Maximum value is 10s."
    }),
    "SpreadCoef": dict({
        "name": "SpreadCoef",
        "validation_function": validation.is_double,
        "value": 1.5,
        "type": Attribute.DOUBLE,
        "help": "Spreading coefficient used in calculation of Thorp's approximation"
    }),
    "ewndFor36mbps": dict({
        "name": "ewndFor36mbps",
        "validation_function": validation.is_integer,
        "value": 40,
        "type": Attribute.INTEGER,
        "help": "ewnd parameter for 36 Mbs data mode"
    }),
    "MaxTtl": dict({
        "name": "MaxTtl",
        "validation_function": validation.is_integer,
        "value": 32,
        "type": Attribute.INTEGER,
        "help": "Initial value of Time To Live field"
    }),
    "MinDistance": dict({
        "name": "MinDistance",
        "validation_function": validation.is_double,
        "value": 0.5,
        "type": Attribute.DOUBLE,
        "help": "The distance under which the propagation model refuses to give results (m)"
    }),
    "RxNoiseFigure": dict({
        "name": "RxNoiseFigure",
        "validation_function": validation.is_double,
        "value": 7.0,
        "type": Attribute.DOUBLE,
        "help": "Loss (dB) in the Signal-to-Noise-Ratio due to non-idealities in the receiver. According to Wikipedia (http://en.wikipedia.org/wiki/Noise_figure), this is 'the difference in decibels (dB) between the noise output of the actual receiver to the noise output of an  ideal receiver with the same overall gain and bandwidth when the receivers  are connected to sources at the standard noise temperature T0 (usually 290 K)'."
    }),
    "DopplerFreq": dict({
        "name": "DopplerFreq",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The doppler frequency in Hz (f_d = v / lambda = v * f / c), the default is 0)"
    }),
    "RetryTimeout": dict({
        "name": "RetryTimeout",
        "validation_function": validation.is_time,
        "value": "40960000ns",
        "type": Attribute.STRING,
        "help": "Retry timeout"
    }),
    "ControlMode": dict({
        "name": "ControlMode",
        "validation_function": validation.is_string,
        "value": "OfdmRate6Mbps",
        "type": Attribute.STRING,
        "help": "The transmission mode to use for every control packet transmission."
    }),
    "Size": dict({
        "name": "Size",
        "validation_function": validation.is_integer,
        "value": 56,
        "type": Attribute.INTEGER,
        "help": "The number of data bytes to be sent, real packet will be 8 (ICMP) + 20 (IP) bytes longer."
    }),
    "ErrorRate": dict({
        "name": "ErrorRate",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The error rate."
    }),
    "PacketLength": dict({
        "name": "PacketLength",
        "validation_function": validation.is_double,
        "value": 1200.0,
        "type": Attribute.DOUBLE,
        "help": "The packet length used for calculating mode TxTime"
    }),
    "MaxCost": dict({
        "name": "MaxCost",
        "validation_function": validation.is_integer,
        "value": 32,
        "type": Attribute.INTEGER,
        "help": "Cost threshold after which packet will be dropped"
    }),
    "SegmentSize": dict({
        "name": "SegmentSize",
        "validation_function": validation.is_double,
        "value": 6000.0,
        "type": Attribute.DOUBLE,
        "help": "The largest allowable segment size packet"
    }),
    "poriFor18mbps": dict({
        "name": "poriFor18mbps",
        "validation_function": validation.is_double,
        "value": 0.13250000000000001,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 18 Mbs data mode"
    }),
    "UnicastPerrThreshold": dict({
        "name": "UnicastPerrThreshold",
        "validation_function": validation.is_integer,
        "value": 32,
        "type": Attribute.INTEGER,
        "help": "Maximum number of PERR receivers, when we send a PERR as a chain of unicasts"
    }),
    "EnableHello": dict({
        "name": "EnableHello",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Indicates whether a hello messages enable."
    }),
    "BeaconGeneration": dict({
        "name": "BeaconGeneration",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Whether or not beacons are generated."
    }),
    "MaxUcdInterval": dict({
        "name": "MaxUcdInterval",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "Maximum time between transmission of UCD messages. Maximum is 10s"
    }),
    "Dot11MeshHWMPperrMinInterval": dict({
        "name": "Dot11MeshHWMPperrMinInterval",
        "validation_function": validation.is_time,
        "value": "102400000ns",
        "type": Attribute.STRING,
        "help": "Minimal interval between to successive PREQs"
    }),
    "Delay": dict({
        "name": "Delay",
        "validation_function": validation.is_time,
        "value": "0ns",
        "type": Attribute.STRING,
        "help": "Transmission delay through the channel"
    }),
    "SIFS": dict({
        "name": "SIFS",
        "validation_function": validation.is_time,
        "value": "200000000ns",
        "type": Attribute.STRING,
        "help": "Spacing to give between frames (this should match gateway)"
    }),
    "MaxRange": dict({
        "name": "MaxRange",
        "validation_function": validation.is_double,
        "value": 250.0,
        "type": Attribute.DOUBLE,
        "help": "Maximum Transmission Range (meters)"
    }),
    "LostDlMapInterval": dict({
        "name": "LostDlMapInterval",
        "validation_function": validation.is_time,
        "value": "500000000ns",
        "type": Attribute.STRING,
        "help": "Time since last received DL-MAP message before downlink synchronization is considered lost. Maximum is 600ms"
    }),
    "IntervalT2": dict({
        "name": "IntervalT2",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "Wait for broadcast ranging timeout, i.e., wait for initial ranging opportunity. Maximum is 5*Ranging interval"
    }),
    "TurnOffRtsAfterRateDecrease": dict({
        "name": "TurnOffRtsAfterRateDecrease",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "If true the RTS mechanism will be turned off when the rate will be decreased"
    }),
    "MaxContentionRangingRetries": dict({
        "name": "MaxContentionRangingRetries",
        "validation_function": validation.is_integer,
        "value": 16,
        "type": Attribute.INTEGER,
        "help": "Number of retries on contention Ranging Requests"
    }),
    "DAD": dict({
        "name": "DAD",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Always do DAD check."
    }),
    "RemotePort": dict({
        "name": "RemotePort",
        "validation_function": validation.is_integer,
        "value": 0,
        "type": Attribute.INTEGER,
        "help": "The destination port of the outbound packets"
    }),
    "Distance0": dict({
        "name": "Distance0",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Beginning of the first (near) distance field"
    }),
    "FlowInterruptionsMinTime": dict({
        "name": "FlowInterruptionsMinTime",
        "validation_function": validation.is_time,
        "value": "500000000ns",
        "type": Attribute.STRING,
        "help": "The minimum inter-arrival time that is considered a flow interruption."
    }),
    "PacketSize": dict({
        "name": "PacketSize",
        "validation_function": validation.is_integer,
        "value": 512,
        "type": Attribute.INTEGER,
        "help": "The size of packets sent in on state"
    }),
    "LookAroundRate": dict({
        "name": "LookAroundRate",
        "validation_function": validation.is_double,
        "value": 10.0,
        "type": Attribute.DOUBLE,
        "help": "the percentage to try other rates"
    }),
    "NumberOfHops": dict({
        "name": "NumberOfHops",
        "validation_function": validation.is_integer,
        "value": 13,
        "type": Attribute.INTEGER,
        "help": "Number of frequencies in hopping pattern"
    }),
    "Dot11MeshHWMPpathToRootInterval": dict({
        "name": "Dot11MeshHWMPpathToRootInterval",
        "validation_function": validation.is_time,
        "value": "2048000000ns",
        "type": Attribute.STRING,
        "help": "Interval between two successive proactive PREQs"
    }),
    "ProbeRequestTimeout": dict({
        "name": "ProbeRequestTimeout",
        "validation_function": validation.is_time,
        "value": "50000000ns",
        "type": Attribute.STRING,
        "help": "The interval between two consecutive probe request attempts."
    }),
    "RreqRateLimit": dict({
        "name": "RreqRateLimit",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Maximum number of RREQ per second."
    }),
    "RangReqOppSize": dict({
        "name": "RangReqOppSize",
        "validation_function": validation.is_integer,
        "value": 8,
        "type": Attribute.INTEGER,
        "help": "The ranging opportunity size in symbols"
    }),
    "BwReqOppSize": dict({
        "name": "BwReqOppSize",
        "validation_function": validation.is_integer,
        "value": 2,
        "type": Attribute.INTEGER,
        "help": "The bandwidth request opportunity size in symbols"
    }),
    "Rho": dict({
        "name": "Rho",
        "validation_function": validation.is_string,
        "value": "Uniform:0:200",
        "type": Attribute.STRING,
        "help": "A random variable which represents the radius of a position in a random disc."
    }),
    "Address": dict({
        "name": "Address",
        "validation_function": validation.is_string,
        "value": "ff:ff:ff:ff:ff:ff",
        "type": Attribute.STRING,
        "help": "The MAC address of this device."
    }),
    "RetryStep": dict({
        "name": "RetryStep",
        "validation_function": validation.is_double,
        "value": 0.01,
        "type": Attribute.DOUBLE,
        "help": "Retry rate increment"
    }),
    "m2": dict({
        "name": "m2",
        "validation_function": validation.is_double,
        "value": 0.75,
        "type": Attribute.DOUBLE,
        "help": "m2 for distances greater than Distance2. Default is 0.75."
    }),
    "Distance": dict({
        "name": "Distance",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "Change current direction and speed after moving for this distance."
    }),
    "InterframeGap": dict({
        "name": "InterframeGap",
        "validation_function": validation.is_time,
        "value": "0ns",
        "type": Attribute.STRING,
        "help": "The time to wait between packet (frame) transmissions"
    }),
    "EnableBroadcast": dict({
        "name": "EnableBroadcast",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Indicates whether a broadcast data packets forwarding enable."
    }),
    "HelloInterval": dict({
        "name": "HelloInterval",
        "validation_function": validation.is_time,
        "value": "2000000000ns",
        "type": Attribute.STRING,
        "help": "HELLO messages emission interval."
    }),
    "RemoteAddress": dict({
        "name": "RemoteAddress",
        "validation_function": validation.is_ip4_address,
        "value": None,
        "type": Attribute.STRING,
        "help": "The destination Ipv4Address of the outbound packets"
    }),
    "Rss": dict({
        "name": "Rss",
        "validation_function": validation.is_double,
        "value": -150.0,
        "type": Attribute.DOUBLE,
        "help": "The fixed receiver Rss."
    }),
    "EWMA": dict({
        "name": "EWMA",
        "validation_function": validation.is_double,
        "value": 75.0,
        "type": Attribute.DOUBLE,
        "help": "EWMA level"
    }),
    "FailureRatio": dict({
        "name": "FailureRatio",
        "validation_function": validation.is_double,
        "value": 0.33333299999999999,
        "type": Attribute.DOUBLE,
        "help": "Ratio of minimum erroneous transmissions needed to switch to a lower rate"
    }),
    "Bounds": dict({
        "name": "Bounds",
        "validation_function": validation.is_string,
        "value": "-100|100|-100|100|0|100",
        "type": Attribute.STRING,
        "help": "Bounds of the area to cruise."
    }),
    "pmtlFor18mbps": dict({
        "name": "pmtlFor18mbps",
        "validation_function": validation.is_double,
        "value": 0.37219999999999998,
        "type": Attribute.DOUBLE,
        "help": "Pmtl parameter for 18 Mbs data mode"
    }),
    "MinX": dict({
        "name": "MinX",
        "validation_function": validation.is_double,
        "value": 1.0,
        "type": Attribute.DOUBLE,
        "help": "The x coordinate where the grid starts."
    }),
    "TotalRate": dict({
        "name": "TotalRate",
        "validation_function": validation.is_integer,
        "value": 4096,
        "type": Attribute.INTEGER,
        "help": "Total available channel rate in bps (for a single channel, without splitting reservation channel)"
    }),
    "Exponent2": dict({
        "name": "Exponent2",
        "validation_function": validation.is_double,
        "value": 3.7999999999999998,
        "type": Attribute.DOUBLE,
        "help": "The exponent for the third field."
    }),
    "MaxDelay": dict({
        "name": "MaxDelay",
        "validation_function": validation.is_time,
        "value": "10000000000ns",
        "type": Attribute.STRING,
        "help": "If a packet stays longer than this delay in the queue, it is dropped."
    }),
    "MaxQueueSize": dict({
        "name": "MaxQueueSize",
        "validation_function": validation.is_integer,
        "value": 255,
        "type": Attribute.INTEGER,
        "help": "Maximum number of packets we can store when resolving route"
    }),
    "Mode": dict({
        "name": "Mode",
        "validation_function": validation.is_enum,
        "value": "Distance",
        "allowed": ["Distance",
     "Time"],
        "type": Attribute.ENUM,
        "help": "The mode indicates the condition used to change the current speed and direction"
    }),
    "rho": dict({
        "name": "rho",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The radius of the disc"
    }),
    "ProbeThreshold": dict({
        "name": "ProbeThreshold",
        "validation_function": validation.is_integer,
        "value": 1,
        "type": Attribute.INTEGER,
        "help": "The number of consecutive transmissions failure to activate the RTS probe."
    }),
    "Y": dict({
        "name": "Y",
        "validation_function": validation.is_double,
        "value": 0.0,
        "type": Attribute.DOUBLE,
        "help": "The y coordinate of the center of the  disc."
    }),
    "poriFor6mbps": dict({
        "name": "poriFor6mbps",
        "validation_function": validation.is_double,
        "value": 0.5,
        "type": Attribute.DOUBLE,
        "help": "Pori parameter for 6 Mbs data mode"
    }),
    "Root": dict({
        "name": "Root",
        "validation_function": validation.is_string,
        "value": "ff:ff:ff:ff:ff:ff",
        "type": Attribute.STRING,
        "help": "The MAC address of root mesh point."
    }),
    "RxQueueSize": dict({
        "name": "RxQueueSize",
        "validation_function": validation.is_integer,
        "value": 1000,
        "type": Attribute.INTEGER,
        "help": "Maximum size of the read queue.  This value limits number of packets that have been read from the network into a memory buffer but have not yet been processed by the simulator."
    }),
    "IntervalT8": dict({
        "name": "IntervalT8",
        "validation_function": validation.is_time,
        "value": "50000000ns",
        "type": Attribute.STRING,
        "help": "Wait for DSA/DSC Acknowledge timeout. Maximum 300ms."
    }),
    "NetDiameter": dict({
        "name": "NetDiameter",
        "validation_function": validation.is_integer,
        "value": 35,
        "type": Attribute.INTEGER,
        "help": "Net diameter measures the maximum possible number of hops between two nodes in the network"
    }),
    "Dot11sMeshHeaderLength": dict({
        "name": "Dot11sMeshHeaderLength",
        "validation_function": validation.is_integer,
        "value": 6,
        "type": Attribute.INTEGER,
        "help": "Length of the mesh header"
    }),
    "JitterBinWidth": dict({
        "name": "JitterBinWidth",
        "validation_function": validation.is_double,
        "value": 0.001,
        "type": Attribute.DOUBLE,
        "help": "The width used in the jitter histogram."
    }),
    "IntervalT7": dict({
        "name": "IntervalT7",
        "validation_function": validation.is_time,
        "value": "100000000ns",
        "type": Attribute.STRING,
        "help": "wait for DSA/DSC/DSD Response timeout. Maximum is 1s"
    }),
    "Verbose": dict({
        "name": "Verbose",
        "validation_function": validation.is_bool,
        "value": False,
        "type": Attribute.BOOL,
        "help": "Produce usual output."
    }),
    "IntervalT1": dict({
        "name": "IntervalT1",
        "validation_function": validation.is_time,
        "value": "50000000000ns",
        "type": Attribute.STRING,
        "help": "Wait for DCD timeout. Maximum is 5*maxDcdInterval"
    }),
    "DefaultLoss": dict({
        "name": "DefaultLoss",
        "validation_function": validation.is_double,
        "value": 1.7976900000000001e+308,
        "type": Attribute.DOUBLE,
        "help": "The default value for propagation loss, dB."
    }),
    "IntervalT3": dict({
        "name": "IntervalT3",
        "validation_function": validation.is_time,
        "value": "200000000ns",
        "type": Attribute.STRING,
        "help": "ranging Response reception timeout following the transmission of a ranging request. Maximum is 200ms"
    }),
    "MaxPackets": dict({
        "name": "MaxPackets",
        "validation_function": validation.is_integer,
        "value": 100,
        "type": Attribute.INTEGER,
        "help": "The maximum number of packets accepted by this DropTailQueue."
    }),
    "EnableLearning": dict({
        "name": "EnableLearning",
        "validation_function": validation.is_bool,
        "value": True,
        "type": Attribute.BOOL,
        "help": "Enable the learning mode of the Learning Bridge"
    }),
    "Rate": dict({
        "name": "Rate",
        "validation_function": validation.is_string,
        "value": "1000000bps",
        "type": Attribute.STRING,
        "help": "The PHY rate used by this device"
    }),
    "RetryRate": dict({
        "name": "RetryRate",
        "validation_function": validation.is_double,
        "value": 0.20000000000000001,
        "type": Attribute.DOUBLE,
        "help": "Number of retry attempts per second (of RTS/GWPING)"
    }),
    "Threshold": dict({
        "name": "Threshold",
        "validation_function": validation.is_double,
        "value": 8.0,
        "type": Attribute.DOUBLE,
        "help": "SINR cutoff for good packet reception"
    }),
    "SuccessThreshold": dict({
        "name": "SuccessThreshold",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "The minimum number of sucessfull transmissions to try a new rate."
    }),
    "Speed": dict({
        "name": "Speed",
        "validation_function": validation.is_double,
        "value": 300000000.0,
        "type": Attribute.DOUBLE,
        "help": "The speed (m/s)"
    }),
    "RndSpeed": dict({
        "name": "Speed",
        "validation_function": validation.is_string,
        "value": "Uniform:1:2",
        "type": Attribute.STRING,
        "help": "Random variable to control the speed (m/s)."
    }),
    "Port": dict({
        "name": "Port",
        "validation_function": validation.is_integer,
        "value": 9,
        "type": Attribute.INTEGER,
        "help": "Port on which we listen for incoming packets."
    }),
    "NoisePowerSpectralDensity": dict({
        "name": "NoisePowerSpectralDensity",
        "validation_function": validation.is_double,
        "value": 4.1400000000000002e-21,
        "type": Attribute.DOUBLE,
        "help": "the power spectral density of the measuring instrument noise, in Watt/Hz. Mostly useful to make spectrograms look more similar to those obtained by real devices. Defaults to the value for thermal noise at 300K."
    }),
    "RaiseThreshold": dict({
        "name": "RaiseThreshold",
        "validation_function": validation.is_integer,
        "value": 10,
        "type": Attribute.INTEGER,
        "help": "Attempt to raise the rate if we hit that threshold"
     }),
    "ProtocolNumber": dict({
        "name": "ProtocolNumber",
        "validation_function": validation.is_integer,
        "value": 0,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The Ipv4 protocol number."
     }),
    "Position": dict({
        "name": "Position",
        "validation_function": validation.is_string,
        "value": "0:0:0",
        "type": Attribute.STRING,
        "help": "The current position of the mobility model."
     }),
    "Velocity": dict({
        "name": "Velocity",
        "validation_function": validation.is_string,
        "value": "0:0:0", 
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "The current velocity of the mobility model."
     }),
    "StartTime": dict({
        "name": "StartTime",
        "validation_function": validation.is_string,
        "value": "0ns", 
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "Time at which the application will start"
     }),
     "StopTime": dict({
        "name": "StopTime",
        "validation_function": validation.is_string,
        "value": "0ns", 
 
 
        "type": Attribute.STRING,
        "help": "Time at which the application will stop"
     }),
    "IsLowLatency": dict({
        "name": "IsLowLatency",
        "validation_function": validation.is_bool,
        "value": True, 
 
 
        "type": Attribute.BOOL,
        "help": "If true, we attempt to modelize a so-called low-latency device: a device where decisions about tx parameters can be made on a per-packet basis and feedback about the transmission of each packet is obtained before sending the next. Otherwise, we modelize a  high-latency device, that is a device where we cannot update our decision about tx parameters after every packet transmission."
     }),
     "MaxSsrc": dict({
        "name": "MaxSsrc",
        "validation_function": validation.is_integer,
        "value": 7,
        "type": Attribute.INTEGER,
        "help": "The maximum number of retransmission attempts for an RTS. This value will not have any effect on some rate control algorithms."
    }),
    "MaxSlrc": dict({
        "name": "MaxSlrc",
        "validation_function": validation.is_integer,
        "value": 7,
        "type": Attribute.INTEGER,
        "help": "The maximum number of retransmission attempts for a DATA packet. This value will not have any effect on some rate control algorithms."
    }),
    "NonUnicastMode": dict({
        "name": "NonUnicastMode",
        "validation_function": validation.is_string,
        "value": "Invalid-WifiMode",
        "type": Attribute.STRING,
        "help": "Wifi mode used for non-unicast transmissions."
    }),
    "RtsCtsThreshold": dict({
        "name": "RtsCtsThreshold",
        "validation_function": validation.is_integer,
        "value": 2346,
        "type": Attribute.INTEGER,
        "help": "If  the size of the data packet + LLC header + MAC header + FCS trailer is bigger than this value, we use an RTS/CTS handshake before sending the data, as per IEEE Std. 802.11-2007, Section 9.2.6. This value will not have any effect on some rate control algorithms."
    }),
    "FragmentationThreshold": dict({
        "name": "FragmentationThreshold",
        "validation_function": validation.is_integer,
        "value": 2346,
        "type": Attribute.INTEGER,
        "help": "If the size of the data packet + LLC header + MAC header + FCS trailer is biggerthan this value, we fragment it such that the size of the fragments are equal or smaller than this value, as per IEEE Std. 802.11-2007, Section 9.4. This value will not have any effect on some rate control algorithms."
    }),
    "Ssid": dict({
        "name": "Ssid",
        "validation_function": validation.is_string,
        "value": "default",
        "type": Attribute.STRING,
        "help": "The ssid we want to belong to."
    }),
    "AckTimeout": dict({
        "name": "AckTimeout",
        "validation_function": validation.is_time,
        "value": "75000ns",
        "type": Attribute.STRING,
        "help": "When this timeout expires, the DATA/ACK handshake has failed."
    }),
    "Sifs": dict({
        "name": "Sifs",
        "validation_function": validation.is_time,
        "value": "16000ns",
        "type": Attribute.STRING,
        "help": "The value of the SIFS constant."
    }),
    "MinCw": dict({
        "name": "MinCw",
        "validation_function": validation.is_integer,
        "value": 15,
        "type": Attribute.INTEGER,
        "help": "The minimum value of the contention window."
    }),
    "IsEnabled": dict({
        "name": "IsEnabled",
        "validation_function": validation.is_bool,
        "value": True, 
        "type": Attribute.BOOL,
        "help": "Whether this ErrorModel is enabled or not."
    }),
    "CompressedBlockAckTimeout": dict({
        "name": "CompressedBlockAckTimeout",
        "validation_function": validation.is_time,
        "value": "99000ns",
        "type": Attribute.STRING,
        "help": "When this timeout expires, the COMPRESSED_BLOCK_ACK_REQ/COMPRESSED_BLOCK_ACK handshake has failed."
    }),
    "MaxCw": dict({
        "name": "MaxCw",
        "validation_function": validation.is_integer,
        "value": 1023, 
        "type": Attribute.INTEGER,
        "help": "The maximum value of the contention window."
    }),
    "RTG": dict({
        "name": "RTG",
        "validation_function": validation.is_integer,
        "value": 0, 
        "type": Attribute.INTEGER,
        "help": "receive/transmit transition gap."
    }),
    "TTG": dict({
        "name": "TTG",
        "validation_function": validation.is_integer,
        "value": 0, 
        "type": Attribute.INTEGER,
        "help": "transmit/receive transition gap."
    }),
    "MinRTO": dict({
        "name": "MinRTO",
        "validation_function": validation.is_time,
        "value": "200000000ns",
        "type": Attribute.STRING,
        "help": "Minimum retransmit timeout value"
    }),
    "Pifs": dict({
        "name": "Pifs",
        "validation_function": validation.is_time,
        "value": "25000ns",
        "type": Attribute.STRING,
        "help": "The value of the PIFS constant."
    }),
    "InitialEstimation": dict({
        "name": "InitialEstimation",
        "validation_function": validation.is_time,
        "value": "1000000000ns",
        "type": Attribute.STRING,
        "help": "XXX"
    }),
    "BasicBlockAckTimeout": dict({
        "name": "BasicBlockAckTimeout",
        "validation_function": validation.is_time,
        "value": "281000ns",
        "type": Attribute.STRING,
        "help": "When this timeout expires, the BASIC_BLOCK_ACK_REQ/BASIC_BLOCK_ACK handshake has failed."
    }),
    "MaxMultiplier": dict({
        "name": "MaxMultiplier",
        "validation_function": validation.is_double,
        "value": 64.0,
        "type": Attribute.DOUBLE,
        "help": "XXX"
    }),
    "Aifsn": dict({
        "name": "Aifsn",
        "validation_function": validation.is_integer,
        "value": 2, 
        "type": Attribute.INTEGER,
        "help": "The AIFSN: the default value conforms to simple DCA."
    }),
    "OptionNumber": dict({
        "name": "OptionNumber",
        "validation_function": validation.is_integer,
        "value": 0,
        "type": Attribute.INTEGER,
        "help": "The IPv6 option number."
    }),
    "Slot": dict({
        "name": "Slot",
        "validation_function": validation.is_time,
        "value": "9000ns",
        "type": Attribute.STRING,
        "help": "The duration of a Slot."
    }),
    "IpForward": dict({
        "name": "IpForward",
        "validation_function": validation.is_bool,
        "value": True, 
        "type": Attribute.BOOL,
        "help": "Globally enable or disable IP forwarding for all current and future Ipv4 devices."
    }),
    "WeakEsModel": dict({
        "name": "WeakEsModel",
        "validation_function": validation.is_bool,
        "value": True, 
        "type": Attribute.BOOL,
        "help": "RFC1122 term for whether host accepts datagram with a dest. address on another interface"
    }),
    "MaxPropagationDelay": dict({
        "name": "MaxPropagationDelay",
        "validation_function": validation.is_time,
        "value": "3333ns",
        "type": Attribute.STRING,
        "help": "The maximum propagation delay. Unused for now."
    }),
    "ExtensionNumber": dict({
        "name": "ExtensionNumber",
        "validation_function": validation.is_integer,
        "value": 0, 
        "type": Attribute.INTEGER,
        "help": "The IPv6 extension number."
    }),
    "EifsNoDifs": dict({
        "name": "EifsNoDifs",
        "validation_function": validation.is_time,
        "value": "60000ns",
        "type": Attribute.STRING,
        "help": "The value of EIFS-DIFS"
    }),
    "CtsTimeout": dict({
        "name": "CtsTimeout",
        "validation_function": validation.is_time,
        "value": "75000ns",
        "type": Attribute.STRING,
        "help": "When this timeout expires, the RTS/CTS handshake has failed."
    }),
    "Standard": dict({
        "name": "Standard",
        "validation_function": validation.is_string,
        "value": "WIFI_PHY_STANDARD_80211a",
        "flags": Attribute.ExecReadOnly | \
                Attribute.ExecImmutable | \
                Attribute.NoDefaultValue,
        "type": Attribute.ENUM,
        "allowed": wifi_standards.keys(),
        "help": "Wifi PHY standard"
    }),
    "LinuxSocketAddress": dict({
        "name": "LinuxSocketAddress",
        "validation_function": None,
        "value": "",
        "flags": Attribute.DesignInvisible | \
                Attribute.ExecInvisible | \
                Attribute.ExecReadOnly | \
                Attribute.ExecImmutable | \
                Attribute.Metadata,
        "type": Attribute.STRING,
        "help": "Socket address assigned to the Linux socket created to recive file descriptor"
    }),
    "ClassifierSrcAddress": dict({
        "name": "SrcAddress",
        "validation_function": validation.is_string, # TODO:! Address + Netref
        "value": "",
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "The source ip address for the IpcsClassifierRecord"
    }),
    "ClassifierSrcMask": dict({
        "name": "SrcMask",
        "validation_function": validation.is_string, # TODO:! NetworkMask
        "value": "",
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "The mask to apply on the source ip address for the IpcsClassifierRecord"
    }),
    "ClassifierDstAddress": dict({
        "name": "DstAddress",
        "validation_function": validation.is_string, # TODO:! Address + Netref
        "value": "",
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "The destination ip address for the IpcsClassifierRecord"
    }),
    "ClassifierDstMask": dict({
        "name": "DstMask",
        "validation_function": validation.is_string, # TODO:! NetworkMask
        "value": "",
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.STRING,
        "help": "The mask to apply on the destination ip address for the IpcsClassifierRecord"
    }),
    "ClassifierSrcPortLow": dict({
        "name": "SrcPortLow",
        "validation_function": validation.is_integer,
        "value": 0,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The lower boundary of the source port range for the IpcsClassifierRecord"
    }),
    "ClassifierSrcPortHigh": dict({
        "name": "SrcPortHigh",
        "validation_function": validation.is_integer,
        "value": 65000,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The higher boundary of the source port range for the IpcsClassifierRecord"
    }),
    "ClassifierDstPortLow": dict({
        "name": "DstPortLow",
        "validation_function": validation.is_integer,
        "value": 0,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The lower boundary of the destination port range for the IpcsClassifierRecord"
    }),
    "ClassifierDstPortHigh": dict({
        "name": "DstPortHigh",
        "validation_function": validation.is_integer,
        "value": 65000,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The higher boundary of the destination port range for the IpcsClassifierRecord"
    }),
    "ClassifierProtocol": dict({
        "name": "Protocol",
        "validation_function": validation.is_string,
        "value": "UdpL4Protocol",
        "allowed": l4_protocols.keys(),
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.ENUM,
        "help": "The L4 protocol for the IpcsClassifierRecord"
    }),
    "ClassifierPriority": dict({
        "name": "Priority",
        "validation_function": validation.is_integer,
        "value": 1,
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.INTEGER,
        "help": "The priority of the IpcsClassifierRecord"
    }),
    "ServiceFlowDirection": dict({
        "name": "Direction",
        "validation_function": validation.is_string,
        "value": "SF_DIRECTION_UP",
        "allowed": service_flow_direction.keys(),
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.ENUM,
        "help": "Service flow direction as described by the IEEE-802.16 standard"
    }),
    "ServiceFlowSchedulingType": dict({
        "name": "SchedulingType",
        "validation_function": validation.is_string,
        "value": "SF_TYPE_RTPS",
        "allowed": service_flow_scheduling_type.keys(),
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
        "type": Attribute.ENUM,
        "help": "Service flow scheduling type",
    }),
   "WaypointList": dict({
        "name": "WaypointList",
        "validation_function": validation.is_string, # TODO: SPECIAL VALIDATION FUNC
        "value": "",
        "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.Metadata,
        "type": Attribute.STRING,
        "help": "Comma separated list of waypoints in format t:x:y:z. Ex: 0s:0:0:0, 1s:1:0:0"
    }),
})
