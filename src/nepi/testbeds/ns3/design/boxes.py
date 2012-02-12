
from nepi.design import attributes, connectors, tags
from nepi.design.boxes import TestbedBox, Box, IPAddressBox, IPAddressCapableBox, \
        RouteEntryBox, RouteEntryCapableBox, ContainerBox, TunnelBox
 
TESTBED_ID = "ns3.11"

TESTBED = "ns3::Simulation"
CONTAINER = "ns3::Container"

NODE = "ns3::Node"
PROTOCOLNODE = "ns3::nepi::ProtocolNode"

UDPPROTO = "ns3::UdpL4Protocol"
ICMP6PROTO = "ns3::Icmpv6L3Protocol"
ICMP4PROTO = "ns3::Icmpv4L3Protocol"
ARPPROTO = "ns3::ArpL3Protocol"
IP6PROTO = "ns3::Ipv6L3Protocol"
IP4PROTO = "ns3::Ipv4L3Protocol"
TCPPROTO ="ns3::TcpL4Protocol"

PACKETSINK = "ns3::PacketSink"
PING6 = "ns3::Ping6"
PING4 = "ns3::V4Ping"
ONOFF = "ns3::OnOffApplication"
UDPSERVER = "ns3::UdpServer"
UDPCLIENT = "ns3::UdpClient"
UDPECHOCLIENT = "ns3::UdpEchoClient"
UDPECHOSERVER = "ns3::UdpEchoServer"

FDNETDEV = "ns3::FdNetDevice"
TAPBRIDGE = "ns3::TapBridge"
PTPNETDEV = "ns3::PointToPointNetDevice"
SSNETDEV = "ns3::SubscriberStationNetDevice"
BSNETDEV = "ns3::BaseStationNetDevice"
CSMANETDEV = "ns3::CsmaNetDevice"
LOOPNETDEV = "ns3::LoopbackNetDevice"
EMUNETDEV = "ns3::EmuNetDevice"
BRIDGENETDEV = "ns3::BridgeNetDevice"
WIFINETDEV = "ns3::WifiNetDevice"

TUNCHAN = "ns3::nepi::TunChannel"
BRIDGECHAN = "ns3::BridgeChannel"
YANSWIFICHAN = "ns3::YansWifiChannel"
CSMACHAN = "ns3::CsmaChannel"
PTPCHAN = "ns3::PointToPointChannel"
SIMOFDMWIMAXCHAN = "ns3::SimpleOfdmWimaxChannel"

AARFWIFIMNGR = "ns3::AarfWifiManager"
CARAWIFIMNGR = "ns3::CaraWifiManager"
AARFCDWIFIMNGR = "ns3::AarfcdWifiManager"
IDEALWIFIMNGR = "ns3::IdealWifiManager"
CONSTWIFIMNGR = "ns3::ConstantRateWifiManager"
ONOEWIFIMNGR = "ns3::OnoeWifiManager"
AMRRWIFIMNGR = "ns3::AmrrWifiManager"
ARFWIFIMNGR = "ns3::ArfWifiManager"
RRAAWIFIMNGR = "ns3::RraaWifiManager"
MINSTWIFIMNGR = "ns3::MinstrelWifiManager"

CONSTVELMOB = "ns3::ConstantVelocityMobilityModel"
CONSTACCMOB = "ns3::ConstantAccelerationMobilityModel"
WAYPOINTMOB = "ns3::WaypointMobilityModel"
HIERARCHMOB = "ns3::HierarchicalMobilityModel"
RANDWAYMOB = "ns3::RandomWaypointMobilityModel"
CONSTPOSMOB = "ns3::ConstantPositionMobilityModel"
RANDWALK2DMOB = "ns3::RandomWalk2dMobilityModel"
RANDDIR2DMOB = "ns3::RandomDirection2dMobilityModel"
GAUSSMARKMOB = "ns3::GaussMarkovMobilityModel"

CONSTSPPRODELAY = "ns3::ConstantSpeedPropagationDelayModel"

LOGDISTPROPLOSS = "ns3::LogDistancePropagationLossModel"
NAKAPROPLOSS = "ns3::NakagamiPropagationLossModel"
TWORAYGRPOPLOSS = "ns3::TwoRayGroundPropagationLossModel"
FRIISPROPLOSS = "ns3::FriisPropagationLossModel"

STAWIFIMAC = "ns3::StaWifiMac"
APWIFIMAC = "ns3::ApWifiMac"

YANSWIFIPHY = "ns3::YansWifiPhy"
SIMOFDMWIMAXPHY = "ns3::SimpleOfdmWimaxPhy"

DROPTAILQUEUE = "ns3::DropTailQueue"
WIFIMACQUEUE = "ns3::WifiMacQueue"

YANSERR = "ns3::YansErrorRateModel"
NISTERR = "ns3::NistErrorRateModel"

LISTERR = "ns3::ListErrorModel"
RECLISTERR =  "ns3::ReceiveListErrorModel"
RATEERR =  "ns3::RateErrorModel"

BSSRTPS = "ns3::BSSchedulerRtps"
BSSSIMPLE = "ns3::BSSchedulerSimple"

USSIMPLE = "ns3::UplinkSchedulerSimple"
USRTPS = "ns3::UplinkSchedulerRtps"

IPCSCLASS = "ns3::IpcsClassifierRecord"

SERVICEFLOW = "ns3::ServiceFlow"

FLOWMONITOR = "ns3::FlowMonitor"

RTTTRACE = "ns3::RttTrace"
PCAPTRACE = "ns3::PcapTrace"
ASCIITRACE = "ns3::AsciiTrace"

IP4ADDRESS = "ns3::nepi::IP4Address"
ROUTE = "ns3::nepi::RouteEntry"

boxes = list()


############ CONTROLLER #############

box = TestbedBox(TESTBED_ID, TESTBED, help = "ns-3 simulation instance")
boxes.append(box)

box.add_attr(
    attributes.EnumAttribute(
        "SimulatorImplementationType", 
        "The object class to use as the simulator implementation",
        default_value = "ns3::DefaultSimulatorImpl",
        allowed = ["ns3::DefaultSimulatorImpl", "ns3::RealtimeSimulatorImpl"],
        flags = attributes.AttributeFlags.ExecReadOnly | 
               attributes.AttributeFlags.ExecImmutable
        )
    )

box.add_attr(
    attributes.EnumAttribute(
        "SchedulerType", 
        "The object class to use as the scheduler implementation. Make sure to pick a thread-safe variant.",
        default_value = "ns3::MapScheduler",
        allowed = ["ns3::MapScheduler",
                "ns3::HeapScheduler",
                "ns3::ListScheduler",
                "ns3::CalendarScheduler"
            ],
        flags = attributes.AttributeFlags.ExecReadOnly | 
               attributes.AttributeFlags.ExecImmutable
        )
    )

box.add_attr(
    attributes.BoolAttribute(
        "ChecksumEnabled",
        "A global switch to enable all checksums for all protocols",
        default_value = False,
        flags = attributes.AttributeFlags.ExecReadOnly | 
               attributes.AttributeFlags.ExecImmutable
        )
    )

box.add_attr(
    attributes.TimeAttribute(
        "StopTime",
        "Stop time for the simulation",
        default_value = None,
        )
    )


############ CONTAINER #############

# CONTAINER
box = ContainerBox(TESTBED_ID, CONTAINER, help = "Container for grouping ns3 box configurations.")
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
boxes.append(box)


############ NODE #############

class NodeBox(RouteEntryCapableBox):
    def __init__(self, testbed_id, box_id, routeentry_box_id, routeentry_connector,
            provider = None, guid = None, help = None):
        super(NodeBox, self).__init__(testbed_id, box_id, routeentry_box_id,
                routeentry_connector, provider, guid, help)

        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        self.add_tag(tags.NODE)

        conn = connectors.Connector("ifaces", "Connector from ns3::Node to ns-3 intefaces", max = -1, min = 1)
        for p in [FDNETDEV, TAPBRIDGE, PTPNETDEV, SSNETDEV, BSNETDEV, CSMANETDEV,
                LOOPNETDEV, EMUNETDEV, BRIDGENETDEV, WIFINETDEV]: 
            rule = connectors.ConnectionRule(self._box_id, "ifaces", p, "node", False)
            conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("apps", "Connector from ns3::Node to ns-3 applications", max = -1, min = 0)
        for a in [PACKETSINK, PING6, PING4, ONOFF, UDPSERVER, UDPCLIENT, UDPECHOCLIENT, UDPECHOSERVER]: 
            rule = connectors.ConnectionRule(self._box_id, "apps", a, "node", False)
            conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("protos", "Connector from ns3::Node to ns-3 protocols", max = -1, min = 1)
        for p in [UDPPROTO, ICMP6PROTO, ICMP4PROTO, ARPPROTO, IP6PROTO, IP4PROTO, TCPPROTO]: 
            rule = connectors.ConnectionRule(self._box_id, "protos", p, "node", False)
            conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("mob", "Connector from ns3::Node to ns-3 mobility models", max = 1, min = 0)
        for m in [CONSTVELMOB, CONSTACCMOB, WAYPOINTMOB, HIERARCHMOB, RANDWAYMOB, CONSTPOSMOB, 
                RANDWALK2DMOB, RANDDIR2DMOB]: 
            rule = connectors.ConnectionRule(self._box_id, "mob", m, "node", False)
            conn.add_connection_rule(rule)
        self.add_connector(conn)


class ProtocolNodeBox(NodeBox):
    def __init__(self, testbed_id, box_id, routeentry_box_id, routeentry_connector,
            provider = None, guid = None, help = None):
        super(ProtocolNodeBox, self).__init__(testbed_id, box_id, routeentry_box_id,
                routeentry_connector, provider, guid, help)

        conn = connectors.Connector("protos", "Connector from ns3::Node to ns-3 protocols", max = -1, min = 1,
                hidden = True)
        for p in [UDPPROTO, ICMP6PROTO, ICMP4PROTO, ARPPROTO, IP6PROTO, IP4PROTO, TCPPROTO]: 
            rule = connectors.ConnectionRule(self._box_id, "protos", p, "node", False)
            conn.add_connection_rule(rule)
        self.add_connector(conn)

    def clone(self, **kwargs):
        new = super(ProtocolNodeBox, self).clone(**kwargs)
        for p in [UDPPROTO, ICMP6PROTO, ICMP4PROTO, ARPPROTO, IP6PROTO, IP4PROTO, TCPPROTO]: 
            proto = new.provider.create(p, container = new.container)
            proto.graphical_info.hidden = True
            proto.c.node.connect(new.c.protos)
        return new


#########
box = NodeBox(TESTBED_ID, NODE, ROUTE, "node", help = "ns-3 Node")
boxes.append(box)

#########
box = ProtocolNodeBox(TESTBED_ID, PROTOCOLNODE, ROUTE, "node", 
        help = "ns-3 Node with L2, L3 and L4 protocols")
boxes.append(box)


############ PROTOCOLS #############

class ProtocolBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(ProtocolBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.PROTOCOL)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", "Connector to ns3::Node", max = 1, min = 1)
        rule = connectors.ConnectionRule(self.box_id, "node", NODE, "protos", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self.box_id, "node", PROTOCOLNODE, "protos", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

class IPProtocolBox(ProtocolBox):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(IPProtocolBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
         
        self.add_attr(
            attributes.IntegerAttribute(
                    "DeafultTtl", 
                    "The TTL value set by default on all outgoing packets generated on this node.",
                    default_value = 64
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                    "IpForward", 
                    "Globally enable or disable IP forwarding for all current and future Ipv4 devices.",
                    default_value = True
                )
            )

class OverIPProtocolBox(ProtocolBox):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(OverIPProtocolBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
 
        self.add_attr(
            attributes.IntegerAttribute(
                    "ProtocolNumber", 
                    "The Ipv4 protocol number.",
                    default_value = 0,
                    flags = attributes.AttributeFlags.ExecReadOnly | 
                            attributes.AttributeFlags.ExecImmutable
                )
            )


############
box = OverIPProtocolBox(TESTBED_ID, UDPPROTO, help = "UDP protocol model")
boxes.append(box)

############
box = OverIPProtocolBox(TESTBED_ID, ICMP6PROTO, help = "ICMP v6 protocol model")
boxes.append(box)
box.add_attr(
    attributes.BoolAttribute(
            "DAD", 
            "Always do DAD check.",
            default_value = True,
        )
    )

############
box = OverIPProtocolBox(TESTBED_ID, ICMP4PROTO, help = "ICMP v4 protocol model")
boxes.append(box)

############
box = ProtocolBox(TESTBED_ID, ARPPROTO, help = "ARP protocol model")
boxes.append(box)

############
box = IPProtocolBox(TESTBED_ID, IP6PROTO, help = "IP v6 protocol model")
boxes.append(box)

############
box = IPProtocolBox(TESTBED_ID, IP4PROTO, help = "IP v4 protocol model")
boxes.append(box)
box.add_attr(
    attributes.BoolAttribute(
            "WeakEsModel", 
            "RFC1122 term for whether host accepts datagram with a dest. address on another interface",
            default_value = True
        )
    )

############
box = OverIPProtocolBox(TESTBED_ID, TCPPROTO, help = "TCP protocol model")
boxes.append(box)
box.add_attr(
    attributes.StringAttribute(
            "RttEstimatorFactory",
            "How RttEstimator objects are created.",
            default_value = "ns3::RttMeanDeviation[]"
        )
    )


############ APPLICATIONS #############

class ApplicationBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(ApplicationBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.APPLICATION)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", "Connector to ns3::Node", max = 1, min = 1)
        rule = connectors.ConnectionRule(self.box_id, "node", NODE, "apps", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self.box_id, "node", PROTOCOLNODE, "apps", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
            attributes.TimeAttribute(
                    "StartTime", 
                    "Time at which the application will start",
                    default_value = "0s",
                    flags = attributes.AttributeFlags.ExecReadOnly | 
                            attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.TimeAttribute(
                    "StopTime", 
                    "Time at which the application will stop",
                    default_value = "0s",
                )
            )

class UdpClientBox(ApplicationBox):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(UdpClientBox, self).__init__(testbed_id, box_id, provider,
                guid, help)

        self.add_attr(
            attributes.IntegerAttribute(
                    "MaxPackets",
                    "The maximum number of packets accepted by this DropTailQueue.",
                    default_value = 100
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                    "Interval",
                    "The time to wait between packets",
                    default_value = "1000000000ns"
                )
            )

        self.add_attr(
            attributes.IPv4Attribute(
                    "RemoteAddress",
                    "The destination Ipv4Address of the outbound packets",
                    default_value = None
                )
            )

        self.add_attr(
            attributes.IntegerAttribute(
                    "RemotePort",
                    "The destination port of the outbound packets",
                    default_value = 0
                )
            )

        self.add_attr(
            attributes.IntegerAttribute(
                    "PacketSize",
                    "The size of packets sent in on state",
                    default_value = 512
                )
            )

class UdpServerBox(ApplicationBox):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(UdpServerBox, self).__init__(testbed_id, box_id, provider,
                guid, help)

        self.add_attr(
            attributes.IntegerAttribute(
                    "Port",
                    "Port on which we listen for incoming packets.",
                    default_value = 9
                )
            )


############
box = ApplicationBox(TESTBED_ID, PACKETSINK, help =  "PacketSink application model")
boxes.append(box)
box.add_attr(
    attributes.StringAttribute(
            "Local",
            "The Address on which to Bind the rx socket.",
            default_value = "None"
        )
    )

box.add_attr(
    attributes.StringAttribute(
            "Protocol",
            "The type of protocol to use.",
            default_value = "ns3::UdpSocketFactory"
        )
    )

############
box = ApplicationBox(TESTBED_ID, PING6, help = "Ping v6 application model")
boxes.append(box)
box.add_attr(
    attributes.IntegerAttribute(
            "MaxPackets",
            "The maximum number of packets accepted by this DropTailQueue.",
            default_value = 100 
        )
    )

box.add_attr(
    attributes.StringAttribute(
            "Interval",
            "The time to wait between packets",
            default_value = "1000000000ns"
        )
    )

box.add_attr(
    attributes.IntegerAttribute(
            "PacketSize",
            "The size of packets sent in on state",
            default_value = 512
        )
    )

box.add_attr(
    attributes.StringAttribute(
            "LocalIpv6",
            "Local Ipv6Address of the sender",
            default_value = "0000:0000:0000:0000:0000:0000:0000:0000"
        )
    )

box.add_attr(
    attributes.StringAttribute(
            "RemoteIpv6",
            "The Ipv6Address of the outbound packets",
            default_value = "0000:0000:0000:0000:0000:0000:0000:0000"
        )
    )

############
box = ApplicationBox(TESTBED_ID, PING4, help = "Ping v4 application model")
boxes.append(box)
box.add_attr(
    attributes.StringAttribute(
            "Interval",
            "The time to wait between packets",
            default_value = "1000000000ns"
        )
    )

box.add_attr(
    attributes.IPv4Attribute(
            "Remote",
            "The address of the destination",
            default_value = None
        )
    )

box.add_attr(
    attributes.BoolAttribute(
            "Verbose",
            "Produce usual output.",
            default_value = False
        )
    )

box.add_attr(
    attributes.IntegerAttribute(
            "Size",
            "The number of data bytes to be sent, real packet will be 8 (ICMP) + 20 (IP) bytes longer.",
            default_value = 56
        )
    )
       
conn = connectors.Connector("traces", "Connector from %s to %s " % (PING4, RTTTRACE), max = -1, min = 0)
rule = connectors.ConnectionRule(PING4, "traces", RTTTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

############
box = ApplicationBox(TESTBED_ID, ONOFF, help = "OnOff application model")
boxes.append(box)
box.add_attr(
    attributes.IntegerAttribute(
            "PacketSize",
            "The size of packets sent in on state",
            default_value = 512
        )
    )

box.add_attr(
    attributes.IPv4Attribute(
            "Remote",
            "The address of the destination",
            default_value = None
        )
    )

box.add_attr(
    attributes.StringAttribute(
            "Protocol",
            "The type of protocol to use.",
            default_value = "ns3::UdpSocketFactory"
        )
    )


############
box = UdpServerBox(TESTBED_ID, UDPSERVER, help = "UDP server application model")
boxes.append(box)
box.add_attr(
    attributes.IntegerAttribute(
            "PacketWindowSize",
            "The size of the window used to compute the packet loss. This value should be a multiple of 8.",
            default_value = 32
        )
    )

############
box = UdpClientBox(TESTBED_ID, UDPCLIENT, help = "UDP client application model")
boxes.append(box)

############
box = UdpServerBox(TESTBED_ID, UDPECHOSERVER, help = "UDP Echo server application model")
boxes.append(box)

############
box = UdpClientBox(TESTBED_ID, UDPECHOCLIENT, help = "UDP Echo client application model")
boxes.append(box)


############ NETWORK DEVICES #############

class NetDeviceBox(IPAddressCapableBox):
    def __init__(self, testbed_id, box_id, address_box_id, address_connector,
            provider = None, guid = None, help = None):
        super(NetDeviceBox, self).__init__(testbed_id, box_id, address_box_id,
                address_connector, provider, guid, help)
        
        self.add_tag(tags.INTERFACE)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
        rule = connectors.ConnectionRule(self.box_id, "node", NODE, "ifaces", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self.box_id, "node", PROTOCOLNODE, "ifaces", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


class TracesNetDeviceBox(NetDeviceBox):
    def __init__(self, testbed_id, box_id, address_box_id, address_connector, 
            provider = None, guid = None, help = None):
        super(TracesNetDeviceBox, self).__init__(testbed_id, box_id, address_box_id,
                address_connector, provider, guid, help)
        
        conn = connectors.Connector("traces", "Connector to ns3 traces", max = -1, min = 0)
        rule = connectors.ConnectionRule(self.box_id, "traces", PCAPTRACE, "iface", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self.box_id, "traces", ASCIITRACE, "iface", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

class MacAddressNetDeviceBox(TracesNetDeviceBox):
    def __init__(self, testbed_id, box_id, address_box_id, address_connector, 
            provider = None, guid = None, help = None):
        super(MacAddressNetDeviceBox, self).__init__(testbed_id, box_id, address_box_id,
                address_connector, provider, guid, help)

        conn = connectors.Connector("err", "Connector to a ns3 network interface error model", max = 1, min = 1)
        rule = connectors.ConnectionRule(self.box_id, "err", LISTERR, "iface", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self.box_id, "err", RECLISTERR, "iface", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self.box_id, "err", RATEERR, "iface", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.MacAddressAttribute(
                    "Address", 
                    "The MAC address of this device.",
                    default_value = "ff:ff:ff:ff:ff:ff"
                )
        )

        self.add_attr(
                attributes.IntegerAttribute(
                        "Mtu",
                        "The MAC-level Maximum Transmission Unit",
                        default_value = 1500 
                    )
                )

class FdNetDeviceBox(MacAddressNetDeviceBox):
    def __init__(self, testbed_id, box_id, address_box_id, address_connector,
            provider = None, guid = None, help = None):
        super(FdNetDeviceBox, self).__init__(testbed_id, box_id, address_box_id,
                address_connector, provider, guid, help)

        conn = connectors.Connector("->fd", help = "File descriptor receptor for devices with file descriptors",
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self.box_id, "->fd", None, "->fd", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.StringAttribute(
                    "tunProto", 
                    "TUNneling protocol used",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    "tunKey",
                    "Randomly selected TUNneling protocol cryptographic key. "
                     "Endpoints must agree to use the minimum (in lexicographic order) "
                     "of both the remote and local sides.",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    "tunAddr",
                    "Address (IP, unix socket, whatever) of the tunnel endpoint",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "tunPort",
                    "IP port of the tunnel endpoint",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.EnumAttribute(
                    "tunCipher",
                    "Tunnel cryptography not supported",
                    allowed = ["PLAIN", "Blowfish", "DES3", "DES", "PLAIN"],
                    default_value = "AES",
                    flags = attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )


class StationNetDeviceBox(NetDeviceBox):
    def __init__(self, testbed_id, box_id, address_box_id, address_connector,
            provider = None, guid = None, help = None):
        super(StationNetDeviceBox, self).__init__(testbed_id, box_id, address_box_id,
                address_connector, provider, guid, help)

        conn = connectors.Connector("chan", help = "Connector to a %s" % SIMOFDMWIMAXCHAN, 
                max = 1, min = 1)
        rule = connectors.ConnectionRule(SSNETDEV, "chan", SIMOFDMWIMAXCHAN, "ifaces", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("phy", help = "Connector to a %s" % SIMOFDMWIMAXPHY, 
                max = 1, min = 1)
        rule = connectors.ConnectionRule(SSNETDEV, "phy", SIMOFDMWIMAXPHY, "iface", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.IntegerAttribute(
                        "Mtu",
                        "The MAC-level Maximum Transmission Unit",
                        default_value = 1500 
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                        "RTG",
                        "receive/transmit transition gap.",
                        default_value = 0 
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                        "TTG",
                        "transmit/receive transition gap.",
                        default_value = 0 
                    )
                )

############
box = FdNetDeviceBox(TESTBED_ID, FDNETDEV, IP4ADDRESS, "iface",
        help = "Network interface associated to a file descriptor")
boxes.append(box)

############
box = TracesNetDeviceBox(TESTBED_ID, TAPBRIDGE, IP4ADDRESS, "iface",
        help = "TAP device used to connect to the oustide world as a bridge.")
boxes.append(box)
box.add_attr(
        attributes.MacAddressAttribute(
                "MacAddress",
                "The MAC address to assign to the tap device, when in ConfigureLocal mode. This address will override the discovered MAC address of the simulated device.",
                default_value = "ff:ff:ff:ff:ff:ff"
            )
        )

box.add_attr(
        attributes.StringAttribute(
                "DeviceName",
                "The name of the underlying real device (e.g. eth1).",
                default_value = "eth1"
            )
        )

box.add_attr(
        attributes.IntegerAttribute(
                "Mtu",
                "The MAC-level Maximum Transmission Unit",
                default_value = 1500 
            )
        )

box.add_attr(
        attributes.IPv4Attribute(
                "Gateway",
                "The IP address of the default gateway to assign to the host machine, when in ConfigureLocal mode.",
                default_value = None
            )
        )

box.add_attr(
        attributes.IPv4Attribute(
                "IpAddress",
                "The IP address to assign to the tap device,  when in ConfigureLocal mode. This address will override the discovered IP address of the simulated device.",
                default_value = None
            )
        )

box.add_attr(
        attributes.IPv4Attribute(
                "Netmask",
                "The network mask to assign to the tap device, when in ConfigureLocal mode. This address will override the discovered MAC address of the simulated device.",
                default_value = "255.255.255.255"
            )
        )

############
box = MacAddressNetDeviceBox(TESTBED_ID, PTPNETDEV, IP4ADDRESS, "iface",
        help = "point to point network device model")
boxes.append(box)

conn = connectors.Connector("queue", help = "Connector to a queueing discipline (mandatory)", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(PTPNETDEV, "queue", DROPTAILQUEUE, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("chan", help = "Connector to a point to point channel", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(PTPNETDEV, "chan", PTPCHAN, "ifaces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.StringAttribute(
                "DataRate",
                "The default data rate for point to point links",
                default_value = "32768bps"
            )
        )

box.add_attr(
        attributes.TimeAttribute(
                "InterframeGap",
                "The time to wait between packet (frame) transmissions",
                default_value = "0s"
            )
        )
 
############
box = StationNetDeviceBox(TESTBED_ID, SSNETDEV, IP4ADDRESS, "iface",
        help = "Subscriber station for mobile wireless network")
boxes.append(box)

conn = connectors.Connector("sflows", help = "Connector to service flows",
        max = -1, min = 0)
rule = connectors.ConnectionRule(SSNETDEV, "sflows", SERVICEFLOW, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.IntegerAttribute(
                "MaxContentionRangingRetries",
                "Number of retries on contention Ranging Requests",
                default_value = 16 
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "MaxUcdInterval",
                "Maximum time between transmission of UCD messages. Maximum is 10s",
                default_value = "10000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "MaxDcdInterval",
                "Maximum time between transmission of DCD messages. Maximum is 10s",
                default_value = "10000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "LostUlMapInterval",
                "Time since last received UL-MAP before uplink synchronization is considered lost, maximum is 600.",
                default_value = "500000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "LostDlMapInterval",
                "Time since last received DL-MAP message before downlink synchronization is considered lost. Maximum is 600ms",
                default_value = "500000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT7",
                "wait for DSA/DSC/DSD Response timeout. Maximum is 1s",
                default_value = "100000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT3",
                "ranging Response reception timeout following the transmission of a ranging request. Maximum is 200ms",
                default_value = "200000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT1",
                "Wait for DCD timeout. Maximum is 5*maxDcdInterval",
                default_value = "50000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT12",
                "Wait for UCD descriptor.Maximum is 5*MaxUcdInterval",
                default_value = "10000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT20",
                "Wait for UCD descriptor.Maximum is 5*MaxUcdInterval",
                default_value = "10000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT2",
                "Wait for broadcast ranging timeout, i.e., wait for initial ranging opportunity. Maximum is 5*Ranging interval",
                default_value = "10000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT2",
                "Wait for broadcast ranging timeout, i.e., wait for initial ranging opportunity. Maximum is 5*Ranging interval",
                default_value = "10000000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT20",
                "Time the SS searches for preambles on a given channel. Minimum is 2 MAC frames",
                default_value = "500000000ns"
            )
        )
box.add_attr(
        attributes.TimeAttribute(
                "IntervalT21",
                "Time the SS searches for (decodable) DL-MAP on a given channel",
                default_value = "10000000000ns"
            )
        )


############
box = StationNetDeviceBox(TESTBED_ID, BSNETDEV, IP4ADDRESS, "iface",
        help = "Base station for wireless mobile network")
boxes.append(box)

conn = connectors.Connector("dwnlnk", help = "Connector to a dowlink scheduler",
        max = 1, min = 0)
rule = connectors.ConnectionRule(BSNETDEV, "dwnlnk", BSSSIMPLE, "iface", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(BSNETDEV, "dwnlnk", BSSRTPS, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("uplnk", help = "Connector to a uplink scheduler",
        max = 1, min = 0)
rule = connectors.ConnectionRule(BSNETDEV, "uplnk", USSIMPLE, "iface", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(BSNETDEV, "uplnk", USRTPS, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.TimeAttribute(
            "InitialRangInterval",
            "Time between Initial Ranging regions assigned by the BS. Maximum is 2s",
            default_value = "50000000ns",
            )
        )
box.add_attr(
        attributes.TimeAttribute(
            "DcdInterval",
            "Time between transmission of DCD messages. Maximum value is 10s.",
            default_value = "3000000000ns",
            )
        )

box.add_attr(
        attributes.TimeAttribute(
            "UcdInterval",
            "Time between transmission of UCD messages. Maximum value is 10s.",
            default_value = "3000000000ns",
            )
        )
box.add_attr(
        attributes.TimeAttribute(
            "IntervalT8",
            "Wait for DSA/DSC Acknowledge timeout. Maximum 300ms.",
            default_value = "50000000ns",
            )
        )
box.add_attr(
        attributes.IntegerAttribute(
            "RangReqOppSize",
            "The ranging opportunity size in symbols",
            default_value = 8,
            )
        )
box.add_attr(
        attributes.IntegerAttribute(
            "BwReqOppSize",
            "The bandwidth request opportunity size in symbols",
            default_value = 2,
            )
        )
box.add_attr(
        attributes.TimeAttribute(
            "MaxRangCorrectionRetries",
            "Number of retries on contention Ranging Requests",
            default_value = 16,
            )
        )

############
box = MacAddressNetDeviceBox(TESTBED_ID, CSMANETDEV, IP4ADDRESS, "iface",
        help = "CSMA (carrier sense, multiple access) interface")
boxes.append(box)

conn = connectors.Connector("queue", help = "Connector to a queueing discipline (mandatory)", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(CSMANETDEV, "queue", DROPTAILQUEUE, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("chan", help = "Connector to a CSMA channel", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(CSMANETDEV, "chan", CSMACHAN, "ifaces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.BoolAttribute(
                "SendEnable",
                "Enable or disable the transmitter section of the device.",
                default_value = True
            )
        )
box.add_attr(
        attributes.BoolAttribute(
                "ReceiveEnable",
                "Enable or disable the receiver section of the device.",
                default_value = True
            )
        )

############
box = TracesNetDeviceBox(TESTBED_ID, LOOPNETDEV, IP4ADDRESS, "iface",
        help = "Loopback network device model")
boxes.append(box)

############
box = MacAddressNetDeviceBox(TESTBED_ID, EMUNETDEV, IP4ADDRESS, "iface")
boxes.append(box)

conn = connectors.Connector("queue", help = "Connector to a queueing discipline (mandatory)", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(EMUNETDEV, "queue", DROPTAILQUEUE, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.StringAttribute(
                "RxQueueSize",
                "Maximum size of the read queue.  This value limits number of packets that have been read from the network into a memory buffer but have not yet been processed by the simulator.",
                default_value = 1000,
            )
        )

############
box = TracesNetDeviceBox(TESTBED_ID, BRIDGENETDEV, IP4ADDRESS, "iface",
        help = "bridge network device model")
boxes.append(box)

conn = connectors.Connector("chan", help = "Connector to a %s" % BRIDGECHAN, 
        max = 1, min = 1)
rule = connectors.ConnectionRule(BRIDGENETDEV, "chan", BRIDGECHAN, "ifaces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.IntegerAttribute(
                "Mtu",
                "The MAC-level Maximum Transmission Unit",
                default_value = 1500 
            )
        )

box.add_attr(
        attributes.IntegerAttribute(
                "EnableLearning",
                "Enable the learning mode of the Learning Bridge",
                default_value = True
            )
        )

box.add_attr(
        attributes.IntegerAttribute(
                "ExpirationTime",
                "Time it takes for learned MAC state entry to expire.",
                default_value = "30000000000ns"
            )
        )


############
box = NetDeviceBox(TESTBED_ID, WIFINETDEV, IP4ADDRESS, "iface",
        help = "wireless network device model")
boxes.append(box)

conn = connectors.Connector("mac", help = "Connector to a MAC wifi model", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(WIFINETDEV, "mac", APWIFIMAC, "iface", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(WIFINETDEV, "mac", STAWIFIMAC, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("phy", help = "Connector to a PHY wifi model", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(WIFINETDEV, "phy", YANSWIFIPHY, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("mngr", help = "Connector to a wifi manager", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(WIFINETDEV, "phy", APWIFIMAC, "iface", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(WIFINETDEV, "phy", STAWIFIMAC, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.IntegerAttribute(
                "Mtu",
                "The MAC-level Maximum Transmission Unit",
                default_value = 1500 
            )
        )


############ CHANNELS #############

class ChannelBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(ChannelBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.CHANNEL)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)


############
box = TunnelBox(TESTBED_ID, TUNCHAN, 
        help = "Channel to forward ns3::FdNetDevice data to other TAP interfaces supporting the NEPI tunneling protocol.")
boxes.append(box)

############
box = ChannelBox(TESTBED_ID, BRIDGECHAN, help = "bridge channel model")
boxes.append(box)

conn = connectors.Connector("ifaces", help = "Connector to %s" % BRIDGENETDEV, 
        max = -1, min = 1)
rule = connectors.ConnectionRule(BRIDGECHAN, "ifaces", BRIDGENETDEV, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

############
box = ChannelBox(TESTBED_ID, YANSWIFICHAN, help = "Yans wifi channel model")
boxes.append(box)

conn = connectors.Connector("phys", help = "Connector to a wifi channel with PHY wifi models", 
        max = -1, min = 1)
rule = connectors.ConnectionRule(YANSWIFICHAN, "phys", YANSWIFIPHY, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("delay", help = "Connector to a delay model", 
        max = -1, min = 0)
rule = connectors.ConnectionRule(YANSWIFICHAN, "delay", CONSTSPPRODELAY, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("loss", help = "Connector to a loss model",
        max = -1, min = 0)
rule = connectors.ConnectionRule(YANSWIFICHAN, "phys", LOGDISTPROPLOSS, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

############
box = ChannelBox(TESTBED_ID, CSMACHAN, help = "CSMA channel model")
boxes.append(box)

conn = connectors.Connector("ifaces", help = "Connector to %s" % CSMANETDEV, 
        max = -1, min = 1)
rule = connectors.ConnectionRule(CSMACHAN, "ifaces", CSMANETDEV, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.StringAttribute(
                "Delay",
                "Transmission delay through the channel",
                default_value = "0ns"
            )
        )

box.add_attr(
        attributes.StringAttribute(
                "DataRate",
                "The default data rate for point to point links",
                default_value = "32768bps"
            )
        )

############
box = ChannelBox(TESTBED_ID, PTPCHAN, help = "Point to point channel model")
boxes.append(box)

conn = connectors.Connector("ifaces", help = "Connector to exactly 2 %s" % PTPNETDEV, 
        max = 2, min = 2)
rule = connectors.ConnectionRule(PTPCHAN, "ifaces", PTPNETDEV, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.StringAttribute(
                "Delay",
                "Transmission delay through the channel",
                default_value = "0ns"
            )
        )

############
box = ChannelBox(TESTBED_ID, SIMOFDMWIMAXCHAN, help = "Simple OFDM Wimax channel model")
boxes.append(box)

conn = connectors.Connector("ifaces", help = "Connector to %s or  %s " % (SSNETDEV, BSNETDEV), 
        max = -1, min = 1)
rule = connectors.ConnectionRule(SIMOFDMWIMAXCHAN, "ifaces", SSNETDEV, "chan", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(SIMOFDMWIMAXCHAN, "ifaces", BSNETDEV, "chan", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ RATE CONTROL MANAGERS #############

class RateControlManagerBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(RateControlManagerBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.RATE_MANAGER)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("iface", help = "Connector to exactly one network interface (mandatory)",
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "iface", WIFINETDEV, "mngr", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


        self.add_attr(
                attributes.BoolAttribute(
                    "IsLowLatency",
                    "If true, we attempt to modelize a so-called low-latency device: a device where decisions about tx parameters can be made on a per-packet basis and feedback about the transmission of each packet is obtained before sending the next. Otherwise, we modelize a  high-latency device, that is a device where we cannot update our decision about tx parameters after every packet transmission.",
                    default_value = True
                    )
                )

        self.add_attr(
                attributes.IntegerAttribute(
                    "MaxSsrc",
                    "The maximum number of retransmission attempts for an RTS. This value will not have any effect on some rate control algorithms.",
                    default_value = 7
                    )
                )

        self.add_attr(
                attributes.IntegerAttribute(
                    "MaxSlrc",
                    "The maximum number of retransmission attempts for a DATA packet. This value will not have any effect on some rate control algorithms.",
                    default_value = 7
                    )
                )

        self.add_attr(
                attributes.IntegerAttribute(
                    "RtsCtsThreshold",
                    "If  the size of the data packet + LLC header + MAC header + FCS trailer is bigger than this value, we use an RTS/CTS handshake before sending the data, as per IEEE Std. 802.11-2007, Section 9.2.6. This value will not have any effect on some rate control algorithms.",
                    default_value = 2346,
                    )
                )

        self.add_attr(
                attributes.IntegerAttribute(
                    "FragmentationThreshold",
                    "If the size of the data packet + LLC header + MAC header + FCS trailer is biggerthan this value, we fragment it such that the size of the fragments are equal or smaller than this value, as per IEEE Std. 802.11-2007, Section 9.4. This value will not have any effect on some rate control algorithms.",
                    default_value = 2346,
                    )
                )

        self.add_attr(
                attributes.IntegerAttribute(
                    "NonUnicastMode",
                    "Wifi mode used for non-unicast transmissions.",
                    default_value = "Invalid-WifiMode"
                    )
                )

class AarfRateControlManagerBox(RateControlManagerBox):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(AarfRateControlManagerBox, self).__init__(testbed_id, box_id, provider,
                guid, help)

        self.add_attr(
                attributes.DoubleAttribute(
                    "SuccessK",
                    "Multiplication factor for the success threshold in the AARF algorithm.",
                    default_value = 2.0
                    )
               )

        self.add_attr(
                attributes.IntegerAttribute(
                    "MinTimerThreshold",
                    "The minimum value for the 'timer' threshold in the AARF algorithm.",
                    default_value = 15,
                    )
               )

        self.add_attr(
                attributes.DoubleAttribute(
                    "TimerK",
                    "Multiplication factor for the timer threshold in the AARF algorithm.",
                    default_value = 2.0
                    )
               )

        self.add_attr(
                attributes.IntegerAttribute(
                    "MaxSuccessThreshold",
                    "Maximum value of the success threshold in the AARF algorithm.",
                    default_value = 60,
                    )
               )

        self.add_attr(
                attributes.IntegerAttribute(
                    "MinSuccessThreshold",
                    "The minimum value for the success threshold in the AARF algorithm.",
                    default_value = 10
                    )
               )


############
box = AarfRateControlManagerBox(TESTBED_ID, AARFWIFIMNGR, help = "AARF rate control manager model")
boxes.append(box)

############
box = RateControlManagerBox(TESTBED_ID, CARAWIFIMNGR, help = "CARA rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.IntegerAttribute(
            "ProbeThreshold",
            "The number of consecutive transmissions failure to activate the RTS probe.",
            default_value = 1
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "FailureThreshold",
            "The number of consecutive transmissions failure to decrease the rate.",
            default_value = 2
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "SuccessThreshold",
            "The minimum number of sucessfull transmissions to try a new rate.",
            default_value = 10
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "Timeout",
            "Timeout for the RRAA BASIC loss estimaton block (s)",
            default_value = "50000000ns"
            )
       )


############
box = AarfRateControlManagerBox(TESTBED_ID, AARFCDWIFIMNGR, help = "AARFCD rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.IntegerAttribute(
            "MinRtsWnd",
            "Minimum value for Rts window of Aarf-CD",
            default_value = 1
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "MaxRtsWnd",
            "Maximum value for Rts window of Aarf-CD",
            default_value = 40
            )
       )

box.add_attr(
        attributes.BoolAttribute(
            "TurnOffRtsAfterRateDecrease",
            "If true the RTS mechanism will be turned off when the rate will be decreased",
            default_value = True
            )
       )
 
box.add_attr(
        attributes.BoolAttribute(
            "TurnOnRtsAfterRateIncrease",
            "If true the RTS mechanism will be turned on when the rate will be increased",
            default_value = True
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, IDEALWIFIMNGR, help = "Ideal rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "BerThreshold",
            "The maximum Bit Error Rate acceptable at any transmission mode",
            default_value = 1.0000000000000001e-05
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, CONSTWIFIMNGR, help = "Constant rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.StringAttribute(
            "DataMode",
            "The transmission mode to use for every data packet transmission",
            default_value = "OfdmRate6Mbps"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "ControlMode",
            "The transmission mode to use for every control packet transmission.",
            default_value = "OfdmRate6Mbps"
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, ONOEWIFIMNGR, help = "ONOE rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.TimeAttribute(
            "UpdatePeriod",
            "The interval between decisions about rate control changes",
            default_value = "1000000000ns"
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "AddCreditThreshold",
            "The interval between decisions about rate control changes",
            default_value = "1000000000ns",
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "RaiseThreshold",
            "Attempt to raise the rate if we hit that threshold",
            default_value = 10
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, AMRRWIFIMNGR, help = "AMRR rate control manager model")
boxes.append(box)
box.add_attr(
        attributes.IntegerAttribute(
            "MaxSuccessThreshold",
            "Maximum value of the success threshold in the AARF algorithm.",
            default_value = 60,
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "MinSuccessThreshold",
            "The minimum value for the success threshold in the AARF algorithm.",
            default_value = 10
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "FailureRatio",
            "Ratio of minimum erroneous transmissions needed to switch to a lower rate",
            default_value = 0.33333299999999999
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "SuccessRatio",
            "Ratio of maximum erroneous transmissions needed to switch to a higher rate",
            default_value = 0.10000000000000001
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "UpdatePeriod",
            "The interval between decisions about rate control changes",
            default_value = "1000000000ns"
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, ARFWIFIMNGR, help = "ARF rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.IntegerAttribute(
            "SuccessThreshold",
            "The minimum number of sucessfull transmissions to try a new rate.",
            default_value = 10
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "TimerThreshold",
            "The 'timer' threshold in the ARF algorithm.",
            default_value = 15
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, RRAAWIFIMNGR, help = "RRAA rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.BoolAttribute(
            "Basic",
            "If true the RRAA-BASIC algorithm will be used, otherwise the RRAA wil be used",
            default_value = True
            )
       )
box.add_attr(
        attributes.StringAttribute(
            "Timeout",
            "Timeout for the RRAA BASIC loss estimaton block (s)",
            default_value = "50000000ns"
            )
    )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor6mbps",
            "ewnd parameter for 6 Mbs data mode",
            default_value = 6
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor9mbps",
            "ewnd parameter for 9 Mbs data mode",
            default_value = 10
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor12mbps",
            "ewnd parameter for 12 Mbs data mode",
            default_value = 20 
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor18mbps",
            "ewnd parameter for 18 Mbs data mode",
            default_value = 20
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor24mbps",
            "ewnd parameter for 24 Mbs data mode",
            default_value = 40
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor36mbps",
            "ewnd parameter for 36 Mbs data mode",
            default_value = 40 
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ewndFor48mbps",
            "ewnd parameter for 48 Mbs data mode",
            default_value = 40
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "ewndFor54mbps",
            "ewnd parameter for 54 Mbs data mode",
            default_value = 40
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor6mbps",
            "Pori parameter for 6 Mbs data mode",
            default_value = 0.5
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor9mbps",
            "Pori parameter for 9 Mbs data mode",
            default_value = 0.1434
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor12mbps",
            "Pori parameter for 12 Mbs data mode",
            default_value = 0.18609999999999999
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor18mbps",
            "Pori parameter for 18 Mbs data mode",
            default_value = 0.13250000000000001
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor24mbps",
            "Pori parameter for 24 Mbs data mode",
            default_value = 0.1681
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor36mbps",
            "Pori parameter for 36 Mbs data mode",
            default_value = 0.115
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "poriFor48mbps",
            "Pori parameter for 48 Mbs data mode",
            default_value = 0.047 
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor54mbps",
            "Pmtl parameter for 54 Mbs data mode",
            default_value = 0.094
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor48mbps",
            "Pmtl parameter for 48 Mbs data mode",
            default_value = 0.23000000000000001
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor36mbps",
            "Pmtl parameter for 36 Mbs data mode",
            default_value = 0.33629999999999999
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor24mbps",
            "Pmtl parameter for 24 Mbs data mode",
            default_value = 0.26500000000000001
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor18mbps",
            "Pmtl parameter for 18 Mbs data mode",
            default_value = 0.37219999999999998,
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor12mbps",
            "Pmtl parameter for 12 Mbs data mode",
            default_value = 0.2868,
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "pmtlFor9mbps",
            "Pmtl parameter for 9 Mbs data mode",
            default_value = 0.39319999999999999
            )
       )

############
box = RateControlManagerBox(TESTBED_ID, MINSTWIFIMNGR, help = "MINST rate control manager model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "LookAroundRate",
            "the percentage to try other rates",
            default_value = 10.0 
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "SegmentSize",
            "The largest allowable segment size packet",
            default_value = 6000.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "SampleColumn",
            "The number of columns used for sampling",
            default_value = 10.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "EWMA",
            "EWMA level",
            default_value = 75.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "PacketLength",
            "The packet length used for calculating mode TxTime",
            default_value = 1200.0
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "UpdateStatistics",
            "The interval between updating statistics table",
            default_value = "100000000ns"
            )
       )


############ MOBILITY MODELS #############

class MobilityModelBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(MobilityModelBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.MOBILE)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", help = "Connector to %s" % NODE,
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "node", NODE, "mob", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self._box_id, "node", PROTOCOLNODE, "mob", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.StringAttribute(
                    "Position",
                    "The current position of the mobility model.",
                    default_value = "0:0:0" 
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "Velocity",
                    "The current velocity of the mobility model.",
                    default_value = "0:0:0" 
                    )
               )


############
box = MobilityModelBox(TESTBED_ID, CONSTVELMOB, help = "Constant velocity mobility model")
boxes.append(box)

############
box = MobilityModelBox(TESTBED_ID, CONSTACCMOB, help = "Constant acceleration mobility model")
boxes.append(box)

############
box = MobilityModelBox(TESTBED_ID, WAYPOINTMOB, help = "Waypoint-based mobility model")
boxes.append(box)

box.add_attr(
        attributes.IntegerAttribute(
            "WaypointsLeft",
            "The number of waypoints remaining.",
            default_value = 0,
            flags =  attributes.AttributeFlags.ExecReadOnly | attributes.AttributeFlags.ExecImmutable
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "WaypointList",
            "Comma separated list of waypoints in format t:x:y:z. Ex: 0s:0:0:0, 1s:1:0:0",
            default_value = "",
            flags =  attributes.AttributeFlags.ExecReadOnly | attributes.AttributeFlags.ExecImmutable
            )
       )

############
box = MobilityModelBox(TESTBED_ID, HIERARCHMOB, help =  "Hierarchical mobility model")
boxes.append(box)

############
box = MobilityModelBox(TESTBED_ID, RANDWAYMOB, help = "Random waypoint mobility model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "Speed",
            "The speed (m/s)",
            default_value = 300000000.0
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "Pause",
            "A random variable used to pick the pause of a random waypoint model.",
            default_value = "Constant:2"
            )
       )

############
box = MobilityModelBox(TESTBED_ID, CONSTPOSMOB, help = "Constant position mobility model")
boxes.append(box)

############
box = MobilityModelBox(TESTBED_ID, RANDWALK2DMOB, help = "Random walk 2D mobility model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "Speed",
            "The speed (m/s)",
            default_value = 300000000.0
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "Bounds",
            "Bounds of the area to cruise.",
            default_value = "-100|100|-100|100|0|100",
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "Time",
            "Change current direction and speed after moving for this delay.",
            default_value = "1000000000ns"
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "Distance",
            "Change current direction and speed after moving for this distance.",
            default_value = 1.0
            )
       )

box.add_attr(
        attributes.EnumAttribute(
            "Mode",
            "The mode indicates the condition used to change the current speed and direction",
            allowed = ["Distance",  "Time"],
            default_value = "Distance"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "Direction",
            "A random variable used to pick the direction (gradients).",
            default_value = "Uniform:0:6.28318"
            )
       )


############
box = MobilityModelBox(TESTBED_ID, RANDDIR2DMOB, help = "Random direction 2D mobility model")
boxes.append(box)

box.add_attr(
        attributes.StringAttribute(
            "Bounds",
            "Bounds of the area to cruise.",
            default_value = "-100|100|-100|100|0|100",
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "Pause",
            "A random variable used to pick the pause of a random waypoint model.",
            default_value = "Constant:2"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "Speed",
            "Random variable to control the speed (m/s).",
            default_value = "Uniform:1:2"
            )
       )

############
box = MobilityModelBox(TESTBED_ID, GAUSSMARKMOB, help = "Gaussian Markov mobility model")
boxes.append(box)

box.add_attr(
        attributes.StringAttribute(
            "Bounds",
            "Bounds of the area to cruise.",
            default_value = "-100|100|-100|100|0|100"
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "TimeStep",
            "Change current direction and speed after moving for this time.",
            default_value = "1000000000ns"
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "Alpha",
            "A constant representing the tunable parameter in the Gauss-Markov model.",
            default_value = 1.0 
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "MeanVelocity",
            "A random variable used to assign the average velocity.",
            default_value =  "Uniform:0:1"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "MeanDirection",
            "A random variable used to assign the average direction.",
            default_value = "Uniform:0:6.28319"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "MeanPitch",
            "A random variable used to assign the average pitch.",
            default_value = "Constant:0"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "NormalVelocity",
            "A gaussian random variable used to calculate the next velocity value.",
            default_value = "Normal:0:1:10"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "NormalDirection",
            "A gaussian random variable used to calculate the next direction value.",
            default_value = "Normal:0:1:10"
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "NormalPitch",
            "A gaussian random variable used to calculate the next pitch value.",
            default_value = "Normal:0:1:10"
            )
    )


############ DELAY MODELS #############

box = Box(TESTBED_ID, CONSTSPPRODELAY, help = "Speed propagation delay model")
boxes.append(box)

conn = connectors.Connector("chan", help = "Connector to a wifi channel ",
        max = 1, min = 1)
rule = connectors.ConnectionRule(CONSTSPPRODELAY, "chan", YANSWIFICHAN, "delay", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.DoubleAttribute(
            "Speed",
            "The speed (m/s)",
            default_value = 300000000.0
            )
    )

box.add_tag(tags.DELAY_MODEL)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)


############ LOSS MODELS #############

class LossModelBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(LossModelBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.LOSS_MODEL)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("prev", help = "Connector to the previous loss model", 
                max = 1, min = 0)
        rule = connectors.ConnectionRule(self._box_id, "prev", self._box_id, "next", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self._box_id, "prev", YANSWIFICHAN, "loss", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("next", help = "Connector to the next loss model", 
                max = 1, min = 0)
        rule = connectors.ConnectionRule(self._box_id, "next", self._box_id, "prev", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


############
box = LossModelBox(TESTBED_ID, LOGDISTPROPLOSS, help = "Logaritmic distance propagation loss model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "Exponent",
            "The exponent of the Path Loss propagation model",
            default_value = 3.0 
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "ReferenceDistance",
            "The distance at which the reference loss is calculated (m)",
            default_value = 1.0 
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "ReferenceLoss",
            "The reference loss at distance d0 (dB). (Default is Friis at 1m with 5.15 GHz)",
            default_value = 46.677700000000002
            )
       )

############
box = LossModelBox(TESTBED_ID, NAKAPROPLOSS, help = "Nakagami propagation loss model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "Distance1",
            "Beginning of the second distance field. Default is 80m.",
            default_value = 80.0 
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "Distance2",
            "Beginning of the third distance field. Default is 200m.",
            default_value = 200.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "m0",
            "m0 for distances smaller than Distance1. Default is 1.5.",
            default_value = 1.5
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "m1",
            "m1 for distances smaller than Distance2. Default is 0.75.",
            default_value = 0.75 
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "m2",
            "m2 for distances greater than Distance2. Default is 0.75.",
            default_value = 0.75
            )
       )


############
box = LossModelBox(TESTBED_ID, TWORAYGRPOPLOSS, help = "Two ray ground propagation loss model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "Lambda",
            "The wavelength  (default is 5.15 GHz at 300 000 km/s).",
            default_value = 0.058252400000000003
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "SystemLoss",
            "The system loss",
            default_value = 1.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "MinDistance",
            "The distance under which the propagation model refuses to give results (m)",
            default_value = 0.5
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "HeightAboveZ",
            "The height of the antenna (m) above the node's Z coordinate",
            default_value = 0.0
            )
       )


############
box = LossModelBox(TESTBED_ID, FRIISPROPLOSS, help = "Friis propagacion loss model")
boxes.append(box)

box.add_attr(
        attributes.DoubleAttribute(
            "Lambda",
            "The wavelength  (default is 5.15 GHz at 300 000 km/s).",
            default_value = 0.058252400000000003
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "SystemLoss",
            "The system loss",
            default_value = 1.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "MinDistance",
            "The distance under which the propagation model refuses to give results (m)",
            default_value = 0.5 
            )
       )


############ LOSS MODELS #############

class WifiMacModelBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(WifiMacModelBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.MAC_MODEL)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("iface", help = "Connector to a %s" % WIFINETDEV, 
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "iface", WIFINETDEV, "mac", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.TimeAttribute(
                    "CtsTimeout",
                    "When this timeout expires, the RTS/CTS handshake has failed.",
                    default_value = "75000ns",
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "AckTimeout",
                    "When this timeout expires, the DATA/ACK handshake has failed.",
                    default_value = "75000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "BasicBlockAckTimeout",
                    "When this timeout expires, the BASIC_BLOCK_ACK_REQ/BASIC_BLOCK_ACK handshake has failed.",
                    default_value =  "281000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "CompressedBlockAckTimeout",
                    "When this timeout expires, the COMPRESSED_BLOCK_ACK_REQ/COMPRESSED_BLOCK_ACK handshake has failed.",
                    default_value = "99000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "Sifs",
                    "The value of the SIFS constant.",
                    default_value = "16000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "EifsNoDifs",
                    "The value of EIFS-DIFS",
                    default_value = "60000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "Slot",
                     "The duration of a Slot.",
                    default_value = "9000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "Pifs",
                    "The value of the PIFS constant.",
                    default_value = "25000ns"
                    )
               )

        self.add_attr(
                attributes.TimeAttribute(
                    "MaxPropagationDelay",
                    "The maximum propagation delay. Unused for now.",
                    default_value = "3333ns"
                    )
               )

        self.add_attr(
                attributes.StringAttribute(
                    "Ssid",
                    "The ssid we want to belong to.",
                    default_value = "default"
                    )
               )

        self.add_attr(
                attributes.EnumAttribute(
                    "Standard",
                    "Wifi PHY standard",
                    default_value = "WIFI_PHY_STANDARD_80211a",
                    allowed = ["WIFI_PHY_STANDARD_holland",
                        "WIFI_PHY_STANDARD_80211p_SCH",
                        "WIFI_PHY_STANDARD_80211_5Mhz",
                        "WIFI_PHY_UNKNOWN",
                        "WIFI_PHY_STANDARD_80211_10Mhz",
                        "WIFI_PHY_STANDARD_80211g",
                        "WIFI_PHY_STANDARD_80211p_CCH",
                        "WIFI_PHY_STANDARD_80211a",
                        "WIFI_PHY_STANDARD_80211b"],
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.NoDefaultValue | \
                            attributes.AttributeFlags.Metadata,
                    )
               )


############
box = WifiMacModelBox(TESTBED_ID, STAWIFIMAC, help = "Station Wifi MAC Model")
boxes.append(box)

box.add_attr(
        attributes.TimeAttribute(
            "ProbeRequestTimeout",
            "The interval between two consecutive probe request attempts.",
            default_value =  "50000000ns"
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "AssocRequestTimeout",
            "The interval between two consecutive assoc request attempts.",
            default_value = "500000000ns"
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "MaxMissedBeacons",
            "Number of beacons which much be consecutively missed before we attempt to restart association.",
            default_value = 10
            )
       )

############
box = WifiMacModelBox(TESTBED_ID, APWIFIMAC, help = "Access point Wifi MAC Model")
boxes.append(box)

box.add_attr(
        attributes.TimeAttribute(
            "BeaconInterval",
            "Delay between two beacons",
            default_value = "102400000ns"
            )
       )

box.add_attr(
        attributes.BoolAttribute(
            "BeaconGeneration",
            "Whether or not beacons are generated.",
            default_value =  True
            )
       )

############ WIFI PHY #############

box = Box(TESTBED_ID, YANSWIFIPHY, help = "Yans Wifi PHY Model")
boxes.append(box)
        
box.add_tag(tags.PHY_MODEL)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", help = "Connector to a %s" % WIFINETDEV, 
        max = 1, min = 1)
rule = connectors.ConnectionRule(YANSWIFIPHY, "iface", WIFINETDEV, "phy", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("err", help = "Connector to a error model", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(YANSWIFIPHY, "err", LISTERR, "phy", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(YANSWIFIPHY, "err", NISTERR, "phy", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("chan", help = "Connector to a %s" % YANSWIFICHAN, 
        max = 1, min = 1)
rule = connectors.ConnectionRule(YANSWIFIPHY, "chan", YANSWIFICHAN, "phy", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("traces", "Connector to ns3 traces", max = -1, min = 0)
rule = connectors.ConnectionRule(YANSWIFIPHY, "traces", PCAPTRACE, "iface", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(YANSWIFIPHY, "traces", ASCIITRACE, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.EnumAttribute(
            "Standard",
            "Wifi PHY standard",
            default_value = "WIFI_PHY_STANDARD_80211a",
            allowed = ["WIFI_PHY_STANDARD_holland",
                "WIFI_PHY_STANDARD_80211p_SCH",
                "WIFI_PHY_STANDARD_80211_5Mhz",
                "WIFI_PHY_UNKNOWN",
                "WIFI_PHY_STANDARD_80211_10Mhz",
                "WIFI_PHY_STANDARD_80211g",
                "WIFI_PHY_STANDARD_80211p_CCH",
                "WIFI_PHY_STANDARD_80211a",
                "WIFI_PHY_STANDARD_80211b"],
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.NoDefaultValue | \
                    attributes.AttributeFlags.Metadata,
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "EnergyDetectionThreshold",
            "The energy of a received signal should be higher than this threshold (dbm) to allow the PHY layer to detect the signal.",
            default_value = -96.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "CcaMode1Threshold",
            "The energy of a received signal should be higher than this threshold (dbm) to allow the PHY layer to declare CCA BUSY state",
            default_value = -99.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "TxGain",
            "Transmission gain (dB).",
            default_value = 1.0
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "RxGain",
            "Reception gain (dB).",
            default_value = 1.0
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "TxPowerLevels",
            "Number of transmission power levels available between TxPowerBase and TxPowerEnd included.",
            default_value = 1
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "TxPowerEnd",
            "Maximum available transmission level (dbm).",
            default_value = 16.020600000000002
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "TxPowerStart",
            "Minimum available transmission level (dbm).",
            default_value = 16.020600000000002

            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "RxNoiseFigure",
            "Loss (dB) in the Signal-to-Noise-Ratio due to non-idealities in the receiver. According to Wikipedia (http://en.wikipedia.org/wiki/Noise_figure), this is 'the difference in decibels (dB) between the noise output of the actual receiver to the noise output of an  ideal receiver with the same overall gain and bandwidth when the receivers  are connected to sources at the standard noise temperature T0 (usually 290 K)'.",
            default_value = 7.0
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "ChannelSwitchDelay",
            "Delay between two short frames transmitted on different frequencies. NOTE: Unused now.",
            default_value = "250000ns"
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "ChannelNumber",
            "Channel center frequency = Channel starting frequency + 5 MHz * (nch - 1)",
            default_value = 1
            )
       )


############ WIMAX PHY #############

box = Box(TESTBED_ID, SIMOFDMWIMAXPHY, help = "Simple OFDM Wimax PHY Model")
boxes.append(box)
        
box.add_tag(tags.PHY_MODEL)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", help = "Connector to a wimax network device", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(SIMOFDMWIMAXPHY, "iface", SSNETDEV, "phy", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(SIMOFDMWIMAXPHY, "iface", BSNETDEV, "phy", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ QUEUES ############

box = Box(TESTBED_ID, DROPTAILQUEUE, help = "Drop tail queue Model")
boxes.append(box)
        
box.add_tag(tags.QUEUE)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", help = "Connector to a ns3 network device", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(DROPTAILQUEUE, "iface", EMUNETDEV, "queue", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(DROPTAILQUEUE, "iface", CSMANETDEV, "queue", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(DROPTAILQUEUE, "iface", PTPNETDEV, "queue", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.IntegerAttribute(
            "MaxPackets",
            "The maximum number of packets accepted by this DropTailQueue.",
            default_value = 100
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "MaxBytes",
            "The maximum number of bytes accepted by this DropTailQueue.",
            default_value = 6553500
            )
       )


############ 

box = Box(TESTBED_ID, WIFIMACQUEUE, help = "Wifi MAC queue Model")
boxes.append(box)
        
box.add_tag(tags.QUEUE)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", help = "Connector to a wifi MAC model", 
        max = 1, min = 1)
rule = connectors.ConnectionRule(WIFIMACQUEUE, "iface", APWIFIMAC, "queue", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(WIFIMACQUEUE, "iface", STAWIFIMAC, "queue", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.IntegerAttribute(
            "MaxPacketNumber",
            "If a packet arrives when there are already this number of packets, it is dropped.",
            default_value = 400
            )
       )

box.add_attr(
        attributes.TimeAttribute(
            "MaxDelay",
            "If a packet stays longer than this delay in the queue, it is dropped.",
            default_value = "10000000000ns"
            )
    )

############ ERROR RATE MODEL #############

class ErrorRateModelBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(ErrorRateModelBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.ERROR_MODEL)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("phy", help = "Connector to a %s" % YANSWIFIPHY, 
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "phy", YANSWIFIPHY, "err", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


################
box = ErrorRateModelBox(TESTBED_ID, YANSERR, help = "Yans error rate model")
boxes.append(box)
        
###############
box = ErrorRateModelBox(TESTBED_ID, NISTERR, help = "Nist error rate model")
boxes.append(box)


############ ERROR RATE MODEL #############

class ErrorModelBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(ErrorModelBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_tag(tags.ERROR_MODEL)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("iface", help = "Connector to a ns3 network device", 
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "iface", CSMANETDEV, "err", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self._box_id, "iface", EMUNETDEV, "err", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self._box_id, "iface", PTPNETDEV, "err", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.BoolAttribute(
                    "IsEnabled",
                    "Whether this ErrorModel is enabled or not.",
                    default_value = True
                    )
               )


################
box = ErrorModelBox(TESTBED_ID, LISTERR, help = "List error model")
boxes.append(box)
        
###############
box = ErrorModelBox(TESTBED_ID, RECLISTERR, help = "Receive list error model")
boxes.append(box)

###############
box = ErrorModelBox(TESTBED_ID, RATEERR, help = "Rate error model")
boxes.append(box)

box.add_attr(
        attributes.EnumAttribute(
            "ErrorUnit",
            "The error unit",
            allowed = ["EU_BYTE", "EU_PKT", "EU_BIT"],
            default_value = "EU_BYTE"
            )
       )

box.add_attr(
        attributes.DoubleAttribute(
            "ErrorRate",
            "The error rate.",
            default_value = 0.0
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "RanVar",
            "The decision variable attached to this error model.",
            default_value = "Uniform:0:1"
            )
       )


############ DOWNLINK SCHEDULER #############

class DownlinkSchedulerBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(DownlinkSchedulerBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("iface", help ="Connector to a downlink scheduler",
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "iface", BSNETDEV, "dwnlnk", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


#########
box = DownlinkSchedulerBox(TESTBED_ID, BSSRTPS, help = "Simple downlink scheduler for rtPS flows")
boxes.append(box)
        
#########
box = DownlinkSchedulerBox(TESTBED_ID, BSSSIMPLE, help = "simple downlink scheduler for service flows")
boxes.append(box)


############ UPLINK SCHEDULER #############

class UplinkSchedulerBox(Box):
    def __init__(self, testbed_id, box_id, provider = None, guid = None,
            help = None):
        super(UplinkSchedulerBox, self).__init__(testbed_id, box_id, provider,
                guid, help)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("iface", help = "Connector to a uplink scheduler",
                max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "iface", BSNETDEV, "uplnk", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


#########
box = UplinkSchedulerBox(TESTBED_ID, USSIMPLE, help = "Simple uplink scheduler for service flows")
boxes.append(box)
        
#########
box = UplinkSchedulerBox(TESTBED_ID, USRTPS, help = "Simple uplink scheduler for rtPS flows")
boxes.append(box)
        

############  #############

box = Box(TESTBED_ID, IPCSCLASS, help = "Classifier record for service flow")
boxes.append(box)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("sflow", help = "Connector to a %s" % SERVICEFLOW, 
        max = 1, min = 1)
rule = connectors.ConnectionRule(IPCSCLASS, "sflow", SERVICEFLOW, "classif", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.StringAttribute(
            "SrcAddress",
            "The source ip address for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = ""
            )
       )
    
box.add_attr(
        attributes.StringAttribute(
            "SrcMask", 
            "The mask to apply on the source ip address for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = ""
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "DstAddress",
            "The destination ip address for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = ""
            )
       )

box.add_attr(
        attributes.StringAttribute(
            "DstMask",
            "The mask to apply on the destination ip address for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = ""
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "SrcPortLow",
            "The lower boundary of the source port range for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = 0
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "SrcPortHigh",
            "The higher boundary of the source port range for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = 65000
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "DstPortLow",
            "The lower boundary of the destination port range for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = 0
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "DstPortHigh",
            "The higher boundary of the destination port range for the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = 65000
            )
       )

box.add_attr(
        attributes.EnumAttribute(
            "Protocol",
            "The L4 protocol for the IpcsClassifierRecord",
            allowed = ["Icmpv4L4Protocol", "UdpL4Protocol", "TcpL4Protocol"],
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = "UdpL4Protocol"
            )
       )

box.add_attr(
        attributes.IntegerAttribute(
            "Priority",
            "The priority of the IpcsClassifierRecord",
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = 1
            )
       )


############ SERVICE FLOW #############

box = Box(TESTBED_ID, SERVICEFLOW, help = "Service flow for QoS")
boxes.append(box)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", help = "Connector to a %s" % SSNETDEV, 
        max = 1, min = 1)
rule = connectors.ConnectionRule(SERVICEFLOW, "iface", SSNETDEV, "sflow", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("classif", help = "Connector to a %s" % IPCSCLASS, 
        max = 1, min = 1)
rule = connectors.ConnectionRule(SERVICEFLOW, "classif", IPCSCLASS, "sflow", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
        attributes.EnumAttribute(
            "Direction", 
            "Service flow direction as described by the IEEE-802.16 standard",
            allowed = ["SF_DIRECTION_UP", "SF_DIRECTION_DOWN"],
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = "SF_DIRECTION_UP"
            )
       )

box.add_attr(
        attributes.EnumAttribute(
            "SchedulingType",
            "Service flow scheduling type",
            allowed = ["SF_TYPE_NONE",
                "SF_TYPE_UNDEF", 
                "SF_TYPE_BE",
                "SF_TYPE_NRTPS",
                "SF_TYPE_RTPS",
                "SF_TYPE_UGS", 
                "SF_TYPE_ALL"],
            flags = attributes.AttributeFlags.ExecReadOnly | \
                    attributes.AttributeFlags.ExecImmutable | \
                    attributes.AttributeFlags.Metadata,
            default_value = "SF_TYPE_RTPS"
            )
       )


############ TRACES #############

box = Box(TESTBED_ID, RTTTRACE, help = "RTT scalar trace")
boxes.append(box)
        
box.add_tag(tags.TRACE)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("app", "Connector to %s " % PING4, max = 1, min = 1)
rule = connectors.ConnectionRule(RTTTRACE, "app", PING4, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

#########
box = Box(TESTBED_ID, PCAPTRACE, help = "Pcap trace")
boxes.append(box)
        
box.add_tag(tags.TRACE)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", "Connector to a ns3 network device", max = 1, min = 1)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", CSMANETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", FDNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", TAPBRIDGE, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", EMUNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", PTPNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", LOOPNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", BRIDGENETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(PCAPTRACE, "iface", YANSWIFIPHY, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

#########
box = Box(TESTBED_ID, ASCIITRACE, help = "Ascii device trace")
boxes.append(box)
        
box.add_tag(tags.TRACE)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", "Connector to a ns3 network device", max = 1, min = 1)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", CSMANETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", FDNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", TAPBRIDGE, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", EMUNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", PTPNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", LOOPNETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", BRIDGENETDEV, "traces", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ASCIITRACE, "iface", YANSWIFIPHY, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

############ ADDRESS #############

box = IPAddressBox(TESTBED_ID, IP4ADDRESS, help = "IP v4 address box.")
boxes.append(box)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("iface", "Connector from address to interface", max = 1, min = 1)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", PTPNETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", CSMANETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", EMUNETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", LOOPNETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", FDNETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", TAPBRIDGE, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", WIFINETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", SSNETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", BSNETDEV, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", BRIDGENETDEV, "addrs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

############ ROUTE ENTRY #############

box = RouteEntryBox(TESTBED_ID, ROUTE, help = "Route entry box.")
boxes.append(box)

conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = connectors.ConnectionRule(ROUTE, "node", NODE, "routes", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ROUTE, "node", PROTOCOLNODE, "routes", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)


