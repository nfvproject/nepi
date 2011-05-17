#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
import os.path
import functools

from nepi.util.tunchannel_impl import \
    crossconnect_tunchannel_peer_init, \
    crossconnect_tunchannel_peer_compl


### Connection functions ####

def connect_node_device(testbed_instance, node_guid, device_guid):
    node = testbed_instance._elements[node_guid]
    device = testbed_instance._elements[device_guid]
    node.AddDevice(device)

def connect_queue_device(testbed_instance, queue_guid, device_guid):
    queue = testbed_instance._elements[queue_guid]
    device = testbed_instance._elements[device_guid]
    device.SetQueue(queue)

def connect_manager_device(testbed_instance, manager_guid, device_guid):
    manager = testbed_instance._elements[manager_guid]
    device = testbed_instance._elements[device_guid]
    device.SetRemoteStationManager(manager)

def connect_phy_device(testbed_instance, phy_guid, device_guid):
    phy = testbed_instance._elements[phy_guid]
    device = testbed_instance._elements[device_guid]
    device.SetPhy(phy)
    phy.SetDevice(device)
    # search for the node asociated with the device
    node_guid = testbed_instance.get_connected(device_guid, "node", "devs")
    if len(node_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % device_guid)
    node = testbed_instance.elements[node_guid[0]]
    phy.SetMobility(node)

def connect_mac_device(testbed_instance, mac_guid, device_guid):
    mac = testbed_instance._elements[mac_guid]
    device = testbed_instance._elements[device_guid]
    device.SetMac(mac)

def connect_errormodel_device(testbed_instance, model_guid, device_guid):
    model = testbed_instance._elements[model_guid]
    device = testbed_instance._elements[device_guid]
    device.SetReceiveErrorModel(model)

def connect_errormodel_phy(testbed_instance, err_guid, phy_guid):
    err = testbed_instance._elements[err_guid]
    phy = testbed_instance._elements[phy_guid]
    phy.SetErrorRateModel(err)

def connect_channel_device(testbed_instance, channel_guid, device_guid):
    channel = testbed_instance._elements[channel_guid]
    device = testbed_instance._elements[device_guid]
    device.Attach(channel)

def connect_simple_channel_device(testbed_instance, channel_guid, device_guid):
    channel = testbed_instance._elements[channel_guid]
    device = testbed_instance._elements[device_guid]
    device.SetChannel(channel)

def connect_loss_channel(testbed_instance, loss_guid, channel_guid):
    loss = testbed_instance._elements[loss_guid]
    channel = testbed_instance._elements[channel_guid]
    channel.SetPropagationLossModel(loss)

def connect_next_loss(testbed_instance, prev_guid, next_guid):
    prev = testbed_instance._elements[prev_guid]
    next = testbed_instance._elements[next_guid]
    prev.SetNext(next)

def connect_delay_channel(testbed_instance, delay_guid, channel_guid):
    delay = testbed_instance._elements[delay_guid]
    channel = testbed_instance._elements[channel_guid]
    channel.SetPropagationDelayModel(delay)

def connect_node_application(testbed_instance, node_guid, application_guid):
    node = testbed_instance._elements[node_guid]
    application = testbed_instance._elements[application_guid]
    node.AddApplication(application)
# works for ArpL3Protocol, Ipv4L3Protocol, UdpL4Protocol, TcpL4Protocol,
# NscTcpL4Protocol, MobilityModel (every subclass), 
# RoutingProtocol (every subclass)

def connect_node_other(testbed_instance, node_guid, other_guid):
    node = testbed_instance._elements[node_guid]
    other = testbed_instance._elements[other_guid]
    node.AggregateObject(other)

def connect_fd(testbed_instance, fdnd_guid, cross_data):
    fdnd = testbed_instance._elements[fdnd_guid]
    endpoint = fdnd.GetEndpoint()
    # XXX: check the method StringToBuffer of ns3::FileDescriptorNetDevice
    # to see how the address should be decoded
    address = endpoint.replace(":", "").decode('hex')[2:]
    testbed_instance.set(fdnd_guid, "LinuxSocketAddress", address)
    
    # If it's a non-abstract socket, add the path
    if not address.startswith('\x00'):
        address = os.path.join( testbed_instance.root_directory, address )
    
    # Set tun standard contract attributes
    testbed_instance.set(fdnd_guid, "tun_addr", address )
    testbed_instance.set(fdnd_guid, "tun_proto", "fd")
    testbed_instance.set(fdnd_guid, "tun_port", 0)
    testbed_instance.set(fdnd_guid, "tun_key", "\xfa"*32) # unimportant, fds aren't encrypted

def connect_tunchannel_fd(testbed_instance, tun_guid, fdnd_guid):
    fdnd = testbed_instance._elements[fdnd_guid]
    tun = testbed_instance._elements[tun_guid]

    # XXX: check the method StringToBuffer of ns3::FileDescriptorNetDevice
    # to see how the address should be decoded
    endpoint = fdnd.GetEndpoint()
    address = endpoint.replace(":", "").decode('hex')[2:]
    testbed_instance.set(fdnd_guid, "LinuxSocketAddress", address)
    
    # Create socket pair to connect the FDND and the TunChannel with it
    import socket
    sock1, sock2 = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET)

    # Send one endpoint to the FDND
    import passfd
    import socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.connect(address)
    passfd.sendfd(sock, sock1.fileno(), '0')
    
    # Store a reference to the endpoint to keep the socket alive
    fdnd._endpoint_socket = sock1
    
    # Send the other endpoint to the TUN channel
    tun.tun_socket = sock2
    
    # With this kind of tun_socket, NS3 will expect a PI header
    # (sockets don't support the TUNGETIFF ioctl, so it will assume
    # the default presence of PI headers)
    tun.with_pi = True


### Connector information ###

connector_types = dict({
    "node": dict({
                "help": "Connector to a ns3::Node object (mandatory)",
                "name": "node",
                "max": 1,
                "min": 1
            }),
    "devs": dict({
                "help": "Connector to network interfaces",
                "name": "devs",
                "max": -1,
                "min": 0
            }),
    "dev2": dict({
                "help": "Connector to exactly two network interfaces (mandatory)",
                "name": "dev2",
                "max": 2,
                "min": 2
            }),
    "dev": dict({
                "help": "Connector to exactly one network interface (mandatory)",
                "name": "dev",
                "max": 1,
                "min": 1
            }),
    "apps": dict({
                "help": "Connector to applications", 
                "name": "apps",
                "max": -1,
                "min": 0
            }),
    "protos": dict({
                "help": "Connector to network stacks and protocols", 
                "name": "protos",
                "max": -1,
                "min": 0
            }),
    "chan": dict({
                "help": "Connector to a channel for the device (mandatory)", 
                "name": "chan",
                "max": 1,
                "min": 1
            }),
    "queue": dict({
                "help": "Connector to a queueing discipline (mandatory)", 
                "name": "queue",
                "max": 1,
                "min": 1
            }),
    "err": dict({
                "help": "Connector to an error model for the device", 
                "name": "err",
                "max": 1,
                "min": 0
            }),
    "->fd": dict({
                "help": "File descriptor receptor for devices with file descriptors",
                "name": "->fd",
                "max": 1,
                "min": 0
            }),
    "fd->": dict({
                "help": "File descriptor provider for devices with file descriptors",
                "name": "fd->",
                "max": 1,
                "min": 0
            }),
    "phy": dict({
                "help": "Connector to interconnect elements with a PHY wifi model", 
                "name": "phy",
                "max": 1,
                "min": 0
            }),
    "phys": dict({
                "help": "Connector to interconnect a wifi channel with PHY wifi models", 
                "name": "phys",
                "max": -1,
                "min": 0
            }),
    "mac": dict({
                "help": "Connector to interconnect a device with a MAC wifi model", 
                "name": "mac",
                "max": 1,
                "min": 0
            }),
    "manager": dict({
                "help": "Connector to interconnect a wifi device with a wifi manager", 
                "name": "manager",
                "max": 1,
                "min": 0
            }),
    "delay": dict({
                "help": "Connector to a delay model", 
                "name": "delay",
                "max": 1,
                "min": 0
            }),
    "loss": dict({
                "help": "Connector to a loss model", 
                "name": "loss",
                "max": 1,
                "min": 0
            }),
    "prev": dict({
                "help": "Connector to the previous loss model", 
                "name": "prev",
                "max": 1,
                "min": 0
            }),
    "next": dict({
                "help": "Connector to the next loss model", 
                "name": "next",
                "max": 1,
                "min": 0
            }),
    "mobility": dict({
                "help": "Connector to a mobility model for the node", 
                "name": "mobility",
                "max": 1,
                "min": 0
            }),
    "tcp": dict({
                "help": "ip-ip tunneling over TCP link", 
                "name": "tcp",
                "max": 1, 
                "min": 0
            }),
    "udp": dict({
                "help": "ip-ip tunneling over UDP datagrams", 
                "name": "udp",
                "max": 1, 
                "min": 0
            }),
    })

connections = [
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::BridgeNetDevice", "node" ),
            "init_code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "node" ),
            "init_code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::EmuNetDevice", "node" ),
            "init_code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "node" ),
            "init_code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::SimpleNetDevice", "node" ),
            "init_code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::FileDescriptorNetDevice", "node" ),
            "init_code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "node" ),
            "init_code": connect_node_device,   
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::DropTailQueue", "dev" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "queue" ),
            "init_code": connect_queue_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::DropTailQueue", "dev" ),
            "to":   ( "ns3", "ns3::EmuNetDevice", "queue" ),
            "init_code": connect_queue_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::DropTailQueue", "dev" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "queue" ),
            "init_code": connect_queue_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ArfWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ConstantRateWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::YansWifiPhy", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "phy" ),  
            "init_code": connect_phy_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::QapWifiMac", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "mac" ),
            "init_code": connect_mac_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::QstaWifiMac", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "mac" ),
            "init_code": connect_mac_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::RateErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "err" ),
            "init_code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::RateErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "err" ),
            "init_code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ListErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "err" ),
            "init_code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ListErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "err" ),
            "init_code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::NistErrorRateModel", "phy" ),        
        "to":   ( "ns3", "ns3::YansWifiPhy", "err" ),
        "init_code": connect_errormodel_phy,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::CsmaChannel", "devs" ),
        "to":   ( "ns3", "ns3::CsmaNetDevice", "chan" ),
        "init_code": connect_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::PointToPointChannel", "dev2" ),
        "to":   ( "ns3", "ns3::PointToPointNetDevice", "chan" ),
        "init_code": connect_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::SimpleChannel", "devs" ),
        "to":   ( "ns3", "ns3::SimpleNetDevice", "chan" ),
        "init_code": connect_simple_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::YansWifiChannel", "phys" ),
        "to":   ( "ns3", "ns3::YansWifiPhy", "chan" ),  
        "init_code": connect_simple_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::LogDistancePropagationLossModel", "prev" ),
        "to":   ( "ns3", "ns3::YansWifiChannel", "loss" ),  
        "init_code": connect_loss_channel,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::LogDistancePropagationLossModel", "prev" ),
        "to":   ( "ns3", "ns3::LogDistancePropagationLossModel", "next" ),  
        "init_code": connect_next_loss,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::ConstantSpeedPropagationDelayModel", "chan" ),
        "to":   ( "ns3", "ns3::YansWifiChannel", "delay" ),  
        "init_code": connect_delay_channel,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::OnOffApplication", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::PacketSink", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::UdpEchoClient", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::UdpEchoServer", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::V4Ping", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::ArpL3Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::Icmpv4L4Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::Icmpv6L4Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::Ipv4L3Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::Ipv6L3Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::UdpL4Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::TcpL4Protocol", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::ConstantAccelerationMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::ConstantPositionMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::ConstantVelocityMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::HierarchicalMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::RandomDirection2dMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::RandomWalk2dMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::RandomWaypointMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::FileDescriptorNetDevice", "->fd" ),
        "to":   ( None, None, "fd->" ),
        "init_code": connect_fd,
        "can_cross": True
    }),
    dict({
        "from": ( "ns3", "ns3::Nepi::TunChannel", "fd->" ),
        "to":   ( "ns3", "ns3::FileDescriptorNetDevice", "->fd" ),
        "init_code": connect_tunchannel_fd,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Nepi::TunChannel", "tcp"),
        "to":   (None, None, "tcp"),
        "init_code": functools.partial(crossconnect_tunchannel_peer_init,"tcp"),
        "compl_code": functools.partial(crossconnect_tunchannel_peer_compl,"tcp"),
        "can_cross": True
    }),
    dict({
        "from": ( "ns3", "ns3::Nepi::TunChannel", "udp"),
        "to":   (None, None, "udp"),
        "init_code": functools.partial(crossconnect_tunchannel_peer_init,"udp"),
        "compl_code": functools.partial(crossconnect_tunchannel_peer_compl,"udp"),
        "can_cross": True
    }),
]

traces = dict({
    "p2ppcap": dict({
                "name": "P2PPcapTrace",
                "help": "Trace to sniff packets from a P2P network device"
              }),
    "p2pascii": dict({
                "name": "P2PAsciiTrace",
                "help": "Ascii trace from a P2P network device"
              }),
    "csmapcap_promisc": dict({
                "name": "CsmaPromiscPcapTrace",
                "help": "Trace to sniff packets from a Csma network device in promiscuous mode"
              }),
    "csmapcap": dict({
                "name": "CsmaPcapTrace",
                "help": "Trace to sniff packets from a Csma network device"
              }),
    "fdpcap": dict({
                "name": "FileDescriptorPcapTrace",
                "help": "Trace to sniff packets from a FileDescriptor network device"
              }),
    "yanswifipcap": dict({
                "name": "YansWifiPhyPcapTrace",
                "help": "Trace to sniff packets from a Wifi network device"
              }),
})

factories_order = ["ns3::BasicEnergySource",
    "ns3::WifiRadioEnergyModel",
    "ns3::BSSchedulerRtps",
    "ns3::BSSchedulerSimple",
    "ns3::SubscriberStationNetDevice",
    "ns3::BaseStationNetDevice",
    "ns3::UdpTraceClient",
    "ns3::UdpServer",
    "ns3::UdpClient",
    "ns3::FlowMonitor",
    "ns3::Radvd",
    "ns3::Ping6",
    "ns3::flame::FlameProtocol",
    "ns3::flame::FlameRtable",
    "ns3::dot11s::AirtimeLinkMetricCalculator",
    "ns3::dot11s::HwmpProtocol",
    "ns3::dot11s::HwmpRtable",
    "ns3::dot11s::PeerManagementProtocol",
    "ns3::dot11s::PeerLink",
    "ns3::MeshWifiInterfaceMac",
    "ns3::MeshPointDevice",
    "ns3::UanMacRcGw",
    "ns3::UanMacRc",
    "ns3::UanPhyCalcSinrDual",
    "ns3::UanPhyPerGenDefault",
    "ns3::UanPhyDual",
    "ns3::UanPropModelThorp",
    "ns3::UanMacCw",
    "ns3::UanNoiseModelDefault",
    "ns3::UanMacAloha",
    "ns3::UanPropModelIdeal",
    "ns3::UanTransducerHd",
    "ns3::UanPhyCalcSinrDefault",
    "ns3::UanPhyGen",
    "ns3::UanPhyCalcSinrFhFsk",
    "ns3::UanPhyPerUmodem",
    "ns3::UanChannel",
    "ns3::V4Ping",
    "ns3::AthstatsWifiTraceSink",
    "ns3::FlameStack",
    "ns3::Dot11sStack",
    "ns3::NonCommunicatingNetDevice",
    "ns3::HalfDuplexIdealPhy",
    "ns3::AlohaNoackNetDevice",
    "ns3::SpectrumAnalyzer",
    "ns3::WaveformGenerator",
    "ns3::MultiModelSpectrumChannel",
    "ns3::SingleModelSpectrumChannel",
    "ns3::MsduStandardAggregator",
    "ns3::EdcaTxopN",
    "ns3::QstaWifiMac",
    "ns3::QapWifiMac",
    "ns3::QadhocWifiMac",
    "ns3::MinstrelWifiManager",
    "ns3::CaraWifiManager",
    "ns3::AarfcdWifiManager",
    "ns3::OnoeWifiManager",
    "ns3::AmrrWifiManager",
    "ns3::ConstantRateWifiManager",
    "ns3::IdealWifiManager",
    "ns3::AarfWifiManager",
    "ns3::ArfWifiManager",
    "ns3::WifiNetDevice",
    "ns3::NqstaWifiMac",
    "ns3::NqapWifiMac",
    "ns3::AdhocWifiMac",
    "ns3::DcaTxop",
    "ns3::WifiMacQueue",
    "ns3::YansWifiChannel",
    "ns3::YansWifiPhy",
    "ns3::NistErrorRateModel",
    "ns3::YansErrorRateModel",
    "ns3::WaypointMobilityModel",
    "ns3::ConstantAccelerationMobilityModel",
    "ns3::RandomDirection2dMobilityModel",
    "ns3::RandomWalk2dMobilityModel",
    "ns3::SteadyStateRandomWaypointMobilityModel",
    "ns3::RandomWaypointMobilityModel",
    "ns3::GaussMarkovMobilityModel",
    "ns3::ConstantVelocityMobilityModel",
    "ns3::ConstantPositionMobilityModel",
    "ns3::ListPositionAllocator",
    "ns3::GridPositionAllocator",
    "ns3::RandomRectanglePositionAllocator",
    "ns3::RandomBoxPositionAllocator",
    "ns3::RandomDiscPositionAllocator",
    "ns3::UniformDiscPositionAllocator",
    "ns3::HierarchicalMobilityModel",
    "ns3::aodv::RoutingProtocol",
    "ns3::UdpEchoServer",
    "ns3::UdpEchoClient",
    "ns3::PacketSink",
    "ns3::OnOffApplication",
    "ns3::VirtualNetDevice",
    "ns3::FileDescriptorNetDevice",
    "ns3::Nepi::TunChannel",
    "ns3::TapBridge",
    "ns3::BridgeChannel",
    "ns3::BridgeNetDevice",
    "ns3::EmuNetDevice",
    "ns3::CsmaChannel",
    "ns3::CsmaNetDevice",
    "ns3::PointToPointRemoteChannel",
    "ns3::PointToPointChannel",
    "ns3::PointToPointNetDevice",
    "ns3::NscTcpL4Protocol",
    "ns3::Icmpv6L4Protocol",
    "ns3::Ipv6OptionPad1",
    "ns3::Ipv6OptionPadn",
    "ns3::Ipv6OptionJumbogram",
    "ns3::Ipv6OptionRouterAlert",
    "ns3::Ipv6ExtensionHopByHop",
    "ns3::Ipv6ExtensionDestination",
    "ns3::Ipv6ExtensionFragment",
    "ns3::Ipv6ExtensionRouting",
    "ns3::Ipv6ExtensionLooseRouting",
    "ns3::Ipv6ExtensionESP",
    "ns3::Ipv6ExtensionAH",
    "ns3::Ipv6L3Protocol",
    "ns3::LoopbackNetDevice",
    "ns3::Icmpv4L4Protocol",
    "ns3::RttMeanDeviation",
    "ns3::ArpL3Protocol",
    "ns3::TcpL4Protocol",
    "ns3::UdpL4Protocol",
    "ns3::Ipv4L3Protocol",
    "ns3::SimpleNetDevice",
    "ns3::SimpleChannel",
    "ns3::PacketSocket",
    "ns3::DropTailQueue",
    "ns3::Node",
    "ns3::FriisSpectrumPropagationLossModel",
    "ns3::Cost231PropagationLossModel",
    "ns3::JakesPropagationLossModel",
    "ns3::RandomPropagationLossModel",
    "ns3::FriisPropagationLossModel",
    "ns3::TwoRayGroundPropagationLossModel",
    "ns3::LogDistancePropagationLossModel",
    "ns3::ThreeLogDistancePropagationLossModel",
    "ns3::NakagamiPropagationLossModel",
    "ns3::FixedRssLossModel",
    "ns3::MatrixPropagationLossModel",
    "ns3::RangePropagationLossModel",
    "ns3::RandomPropagationDelayModel",
    "ns3::ConstantSpeedPropagationDelayModel",
    "ns3::RateErrorModel",
    "ns3::ListErrorModel",
    "ns3::ReceiveListErrorModel",
    "ns3::PacketBurst",
    "ns3::EnergySourceContainer"
 ]

testbed_attributes = dict({
     "simu_impl_type": dict({
            "name": "SimulatorImplementationType",
            "help": "The object class to use as the simulator implementation",
            "type": Attribute.STRING,
            "flags": Attribute.DesignOnly,
            "validation_function": validation.is_string
        }),
      "checksum": dict({
            "name": "ChecksumEnabled",
            "help": "A global switch to enable all checksums for all protocols",
            "type": Attribute.BOOL,
            "value": False,
            "flags": Attribute.DesignOnly,
            "validation_function": validation.is_bool
        }),
})

class VersionedMetadataInfo(metadata.VersionedMetadataInfo):
    @property
    def connector_types(self):
        return connector_types

    @property
    def connections(self):
        return connections

    @property
    def attributes(self):
        from attributes_metadata_v3_9_RC3 import attributes
        return attributes

    @property
    def traces(self):
        return traces

    @property
    def create_order(self):
        return factories_order

    @property
    def configure_order(self):
        return factories_order

    @property
    def factories_info(self):
        from factories_metadata_v3_9_RC3 import factories_info
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

