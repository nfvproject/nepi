#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import functools
from nepi.util.constants import CONNECTION_DELAY
from nepi.util.tunchannel_impl import \
    crossconnect_tunchannel_peer_init, \
    crossconnect_tunchannel_peer_compl

### Connection functions ####

def connect_dummy(testbed_instance, guid1, guid2):
    pass

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
    if hasattr(phy, "GetErrorRateModel") and phy.GetErrorRateModel() == None:
        return CONNECTION_DELAY
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

def connect_station_sflow(testbed_instance, station_guid, sflow_guid):
    station = testbed_instance._elements[station_guid]
    sflow = testbed_instance._elements[sflow_guid]
    station.AddServiceFlow(sflow)

def connect_bstation_linksched(testbed_instance, bstation_guid, linksched_guid):
    bstation = testbed_instance._elements[bstation_guid]
    linksched = testbed_instance._elements[linksched_guid]
    linksched.SetBs(bstation)

def connect_classifier_sflow(testbed_instance, classifier_guid, sflow_guid):
    classifier = testbed_instance._elements[classifier_guid]
    sflow = testbed_instance._elements[sflow_guid]
    csparam = testbed_instance.ns3.CsParameters(testbed_instance.ns3.CsParameters.ADD, classifier)
    sflow.SetConvergenceSublayerParam (csparam); 

def connect_fd(testbed_instance, fdnd_guid, cross_data):
    def recvfd(sock, fdnd):
        (fd, msg) = passfd.recvfd(sock)
        # Store a reference to the endpoint to keep the socket alive
        fdnd.SetFileDescriptor(fd)
    
    import threading
    import passfd
    import socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind("")
    address = sock.getsockname()
    # Set tun standard contract attributes
    testbed_instance.set(fdnd_guid, "tun_addr", address)
    testbed_instance.set(fdnd_guid, "tun_proto", "fd")
    testbed_instance.set(fdnd_guid, "tun_port", 0)
    testbed_instance.set(fdnd_guid, "tun_key", ("\xfa"*32).encode("base64")) # unimportant, fds aren't encrypted
    fdnd = testbed_instance._elements[fdnd_guid]
    t = threading.Thread(target=recvfd, args=(sock,fdnd))
    t.start()

def connect_tunchannel_fd(testbed_instance, tun_guid, fdnd_guid):
    fdnd = testbed_instance._elements[fdnd_guid]
    tun = testbed_instance._elements[tun_guid]

    # Create socket pair to connect the FDND and the TunChannel with it
    import socket
    sock1, sock2 = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET)

    # Store a reference to the endpoint to keep the socket alive
    fdnd._endpoint_socket = sock1
    fdnd.SetFileDescriptor(sock1.fileno())
    
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
                "help": "Connector for file descriptor reception for devices with file descriptors",
                "name": "->fd",
                "max": 1,
                "min": 0
            }),
    "fd->": dict({
                "help": "Connector for file descriptor providing for devices with file descriptors",
                "name": "fd->",
                "max": 1,
                "min": 0
            }),
    "phy": dict({
                "help": "Connector to a PHY wifi model", 
                "name": "phy",
                "max": 1,
                "min": 0
            }),
    "phys": dict({
                "help": "Connector to a wifi channel with PHY wifi models", 
                "name": "phys",
                "max": -1,
                "min": 0
            }),
    "mac": dict({
                "help": "Connector to a MAC wifi model", 
                "name": "mac",
                "max": 1,
                "min": 0
            }),
    "manager": dict({
                "help": "Connector to a wifi manager", 
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
                "help": "Connector to a mobility model", 
                "name": "mobility",
                "max": 1,
                "min": 0
            }),
    "tcp": dict({
                "help": "Connector for ip-ip tunneling over TCP link", 
                "name": "tcp",
                "max": 1, 
                "min": 0
            }),
    "udp": dict({
                "help": "Connector for ip-ip tunneling over UDP datagrams", 
                "name": "udp",
                "max": 1, 
                "min": 0
            }),
    "sflows": dict({
                "help": "Connector to service flows",
                "name": "sflows",
                "max": -1, 
                "min": 0
            }),
    "uplnk": dict({
                "help": "Connector to a uplink scheduler",
                "name": "uplnk",
                "max": 1, 
                "min": 0
            }),
    "dwnlnk": dict({
                "help": "Connector to a dowlink scheduler",
                "name": "dwnlnk",
                "max": 1, 
                "min": 0
            }),
    "classif": dict({
                "help": "Connector to a classifier recod",
                "name": "classif",
                "max": 1, 
                "min": 0
            }),
    "sflow": dict({
                "help": "Connector to a service flow",
                "name": "sflow",
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
            "to":   ( "ns3", "ns3::FdNetDevice", "node" ),
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
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::SubscriberStationNetDevice", "node" ),
            "init_code": connect_dummy,   
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::BaseStationNetDevice", "node" ),
            "init_code": connect_dummy,   
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
            "from": ( "ns3", "ns3::AarfcdWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::AarfWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::AmrrWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::CaraWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::IdealWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::MinstrelWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::OnoeWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "init_code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::RraaWifiManager", "dev" ),
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
            "from": ( "ns3", "ns3::SimpleOfdmWimaxPhy", "dev" ),
            "to":   ( "ns3", "ns3::SubscriberStationNetDevice", "phy" ),  
            "init_code": connect_phy_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::SimpleOfdmWimaxPhy", "dev" ),
            "to":   ( "ns3", "ns3::BaseStationNetDevice", "phy" ),  
            "init_code": connect_phy_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ApWifiMac", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "mac" ),
            "init_code": connect_mac_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::StaWifiMac", "dev" ),
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
        "from": ( "ns3", "ns3::SimpleOfdmWimaxChannel", "devs" ),
        "to":   ( "ns3", "ns3::SubscriberStationNetDevice", "chan" ),
        "init_code": connect_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::SimpleOfdmWimaxChannel", "devs" ),
        "to":   ( "ns3", "ns3::BaseStationNetDevice", "chan" ),
        "init_code": connect_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::YansWifiChannel", "phys" ),
        "to":   ( "ns3", "ns3::YansWifiPhy", "chan" ),  
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
        "to":   ( "ns3", "ns3::UdpClient", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::UdpServer", "node" ),
        "init_code": connect_node_application,
        "can_cross": False
    }),    dict({
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
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::WaypointMobilityModel", "node" ),
        "init_code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::SubscriberStationNetDevice", "sflows" ),
        "to":   ( "ns3", "ns3::ServiceFlow", "dev" ),
        "init_code": connect_station_sflow,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::BaseStationNetDevice", "sflows" ),
        "to":   ( "ns3", "ns3::ServiceFlow", "dev" ),
        "init_code": connect_station_sflow,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::BaseStationNetDevice", "uplnk" ),
        "to":   ( "ns3", "ns3::UplinkSchedulerSimple", "dev" ),
        "init_code": connect_bstation_linksched,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::BaseStationNetDevice", "uplnk" ),
        "to":   ( "ns3", "ns3::UplinkSchedulerRtps", "dev" ),
        "init_code": connect_bstation_linksched,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::BaseStationNetDevice", "dwnlnk" ),
        "to":   ( "ns3", "ns3::BSSchedulerSimple", "dev" ),
        "init_code": connect_bstation_linksched,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::BaseStationNetDevice", "dwnlnk" ),
        "to":   ( "ns3", "ns3::BSSchedulerRtps", "dev" ),
        "init_code": connect_bstation_linksched,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::IpcsClassifierRecord", "sflow" ),
        "to":   ( "ns3", "ns3::ServiceFlow", "classif" ),
        "init_code": connect_classifier_sflow,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::FdNetDevice", "->fd" ),
        "to":   ( None, None, "fd->" ),
        "init_code": connect_fd,
        "can_cross": True
    }),
    dict({
        "from": ( "ns3", "ns3::Nepi::TunChannel", "fd->" ),
        "to":   ( "ns3", "ns3::FdNetDevice", "->fd" ),
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
