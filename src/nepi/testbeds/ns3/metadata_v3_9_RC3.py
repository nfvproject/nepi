#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
from nepi.util.constants import AF_INET, STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

wifi_standards = dict({
    "WIFI_PHY_STANDARD_holland": 5,
    "WIFI_PHY_STANDARD_80211p_SCH": 7,
    "WIFI_PHY_STANDARD_80211_5Mhz": 4,
    "WIFI_PHY_UNKNOWN": 8,
    "WIFI_PHY_STANDARD_80211_10Mhz": 3,
    "WIFI_PHY_STANDARD_80211g": 2,
    "WIFI_PHY_STANDARD_80211p_CCH": 6,
    "WIFI_PHY_STANDARD_80211a": 0,
    "WIFI_PHY_STANDARD_80211b": 1
})

### Connection functions ####

def connect_node_device(testbed_instance, node, device):
    node.AddDevice(device)

def connect_queue_device(testbed_instance, queue, device):
    device.SetQueue(queue)

def connect_manager_device(testbed_instance, manager, device):
    device.SetRemoteStationManager(manager)

def connect_phy_device(testbed_instance, phy, device):
    device.SetPhy(phy)
    phy.SetDevice(device)
    # search for the node asociated with the device
    node_guid = testbed_instance.get_connected(guid, "node", "devs")
    if len(node_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % guid)
    node = testbed_instance.elements[node_guid[0]]
    phy.SetMobility(node)

def connect_mac_device(testbed_instance, mac, device):
    device.SetMac(mac)

def connect_errormodel_device(testbed_instance, model, device):
    device.SetReceiveErrorModel(model)

def connect_errormodel_phy(testbed_instance, err, phy):
    phy.SetErrorRateModel(err)

def connect_channel_device(testbed_instance, channel, device):
    device.Attach(channel)

def connect_simple_channel_device(testbed_instance, channel, device):
    device.SetChannel(channel)

def connect_loss_channel(testbed_instance, loss, channel):
    channel.SetPropagationLossModel(loss)

def connect_next_loss(testbed_instance, prev, next):
    prev.SetNext(next)

def connect_delay_channel(testbed_instance, delay, channel):
    channel.SetPropagationDelayModel(delay)

def connect_node_application(testbed_instance, node, application):
    node.AddApplication(application)
# works for ArpL3Protocol, Ipv4L3Protocol, UdpL4Protocol, TcpL4Protocol,
# NscTcpL4Protocol, MobilityModel (every subclass), 
# RoutingProtocol (every subclass)

def connect_node_other(tesbed_instance, node, other):
    node.AggregateObject(other)

def connect_fd_tap(tesbed_instance, fd, tap):
    # TODO!
    pass

 ### create traces functions ###

def get_node_guid(testbed_instance, guid):
    node_guid = testbed_instance.get_connected(guid, "node", "devs")[0]
    return node_guid

def get_dev_number(testbed_instance, guid):
    dev_guids = testbed_instance.get_connected(node_guid, "devs", "node")
    interface_number = 0
    for guid_ in dev_guids:
        if guid_ == guid:
            break
        inteface_number += 1
    return interface_number

def p2ppcap_trace(testbed_instance, guid):
    trace_id = "p2ppcap"
    node_guid = get_node_guid(testbed_instance, guid)
    interface_number = get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-p2p-node-%d-dev-%d.pcap" % (node_name, interface_number)
    testbed_instance.follow_trace(guid, trace_id, filename)
    filepath = testbed_instance.trace_filename(self, guid, trace_id)
    helper = testbed_instance.ns3.PointToPointHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

def _csmapcap_trace(testbed_instance, guid, trace_id, promisc):
    node_guid = get_node_guid(testbed_instance, guid)
    interface_number = get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-csma-node-%d-dev-%d.pcap" % (node_name, interface_number)
    testbed_instance.follow_trace(guid, trace_id, filename)
    filepath = testbed_instance.trace_filename(self, guid, trace_id)
    helper = testbed_instance.ns3.CsmaHelper()
    helper.EnablePcap(filepath, element, promiscuous = promisc, 
            explicitFilename = True)

def csmapcap_trace(testbed_instance, guid):
    trace_id = "csmapcap"
    promisc = False
    _csmapcap_trace(testbed_instance, guid, trace_id, promisc)

def csmapcap_promisc_trace(testbed_instance, guid):
    trace_id = "csmapcap_promisc"
    promisc = True
    _csmapcap_trace(testbed_instance, guid, trace_id, promisc)

def fdpcap_trace(testbed_instance, guid):
    trace_id = "fdpcap"
    node_guid = get_node_guid(testbed_instance, guid)
    interface_number = get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-fd-node-%d-dev-%d.pcap" % (node_name, interface_number)
    testbed_instance.follow_trace(guid, trace_id, filename)
    filepath = testbed_instance.trace_filename(self, guid, trace_id)
    helper = testbed_instance.ns3.FileDescriptorHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

def yanswifipcap_trace(testbed_instance, guid):
    trace_id = "yanswifipcap"
    dev_guid = testbed_instance.get_connected(guid, "dev", "phy")[0]
    node_guid = get_node_guid(testbed_instance, dev_guid)
    interface_number = get_dev_number(testbed_instance, dev_guid)
    element = testbed_instance._elements[dev_guid]
    filename = "trace-yanswifi-node-%d-dev-%d.pcap" % (node_name, interface_number)
    testbed_instance.follow_trace(guid, trace_id, filename)
    filepath = testbed_instance.trace_filename(self, guid, trace_id)
    helper = testbed_instance.ns3.YansWifiPhyHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

trace_functions = dict({
    "p2ppcap": p2ppcap_trace,
    "csmapcap": csmapcap_trace,
    "csmapcap_promisc": csmapcap_promisc_trace,
    "fdpcap": fdpcap_trace,
    "yanswifipcap": yanswifipcap_trace
    })

### Creation functions ###

def create_element(testbed_instance, guid):
    element_factory = testbed_instance.ns3.ObjectFactory()
    factory_id = testbed_instance._create[guid]
    element_factory.SetTypeId(factory_id) 
    construct_parameters = testbed_instance._get_construct_parameters(guid)
    for name, value in construct_parameters.iteritems():
        ns3_value = testbed_instance._to_ns3_value(factory_id, name, value)
        element_factory.Set(name, ns3_value)
    element = element_factory.Create()
    testbed_instance._elements[guid] = element
    traces = testbed_instance._get_traces(guid)
    for trace_id in traces:
        trace_func = trace_functions[trace_id]
        trace_func(testbed_instance, guid)

def create_node(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    element.AggregateObject(testbed_instance.PacketSocketFactory())

def create_device(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    if "macAddress" in parameters:
        address = parameters["macAddress"]
        macaddr = testbed_instance.ns3.Mac48Address(address)
    else:
        macaddr = testbed_instance.ns3.Mac48Address.Allocate()
    element.SetAddress(macaddr)

def create_wifi_standard_model(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    if "standard" in parameters:
        standard = parameters["standard"]
        if standard:
            elements.ConfigureStandard(wifi_standards[standard])

def create_ipv4stack(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    list_routing = testbed_instance.ns3.Ipv4ListRouting()
    element.SetRoutingProtocol(list_routing)
    static_routing = testbed_instance.ns3.Ipv4StaticRouting()
    list_routing.AddRoutingProtocol(static_routing, 1)

### Start/Stop functions ###

def start_application(testbed_instance, guid):
    element = testbed_instance.elements[guid]
    element.Start()

def stop_application(testbed_instance, guid):
    element = testbed_instance.elements[guid]
    element.Stop()

### Status functions ###

def status_application(testbed_instance, guid):
    if guid not in testbed_instance.elements.keys():
        return STATUS_NOT_STARTED
    app = testbed_instance.elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    if "stopTime" in parameters:
        stop = parameters["stopTime"]
        if stop:
            simTime = testbed_instance.ns3.Simulator.Now()
            if simTime.Compare(stopTime) > 0:
                return STATUS_RUNNING
    return STATUS_FINISHED

### Factory information ###

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
    "fd": dict({
                "help": "Connector to interconnect devices with file descriptors",
                "name": "fd",
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
    })

connections = [
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::BridgeNetDevice", "node" ),
            "code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "node" ),
            "code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::EmuNetDevice", "node" ),
            "code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "node" ),
            "code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::SimpleNetDevice", "node" ),
            "code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::FileDescriptorNetDevice", "node" ),
            "code": connect_node_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::Node", "devs" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "node" ),
            "code": connect_node_device,   
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::DropTailQueue", "dev" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "queue" ),
            "code": connect_queue_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::DropTailQueue", "dev" ),
            "to":   ( "ns3", "ns3::EmuNetDevice", "queue" ),
            "code": connect_queue_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::DropTailQueue", "dev" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "queue" ),
            "code": connect_queue_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ArfWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ConstantRateWifiManager", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "manager" ),  
            "code": connect_manager_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::YansWifiPhy", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "phy" ),  
            "code": connect_phy_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::QapWifiMac", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "mac" ),
            "code": connect_mac_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::QstaWifiMac", "dev" ),
            "to":   ( "ns3", "ns3::WifiNetDevice", "mac" ),
            "code": connect_mac_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::RateErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "err" ),
            "code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::RateErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "err" ),
            "code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ListErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::CsmaNetDevice", "err" ),
            "code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
            "from": ( "ns3", "ns3::ListErrorModel", "dev" ),
            "to":   ( "ns3", "ns3::PointToPointNetDevice", "err" ),
            "code": connect_errormodel_device,
            "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::NistErrorRateModel", "phy" ),        
        "to":   ( "ns3", "ns3::YansWifiPhy", "err" ),
        "code": connect_errormodel_phy,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::CsmaChannel", "devs" ),
        "to":   ( "ns3", "ns3::CsmaNetDevice", "chan" ),
        "code": connect_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::PointToPointChannel", "dev2" ),
        "to":   ( "ns3", "ns3::PointToPointNetDevice", "chan" ),
        "code": connect_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::SimpleChannel", "devs" ),
        "to":   ( "ns3", "ns3::SimpleNetDevice", "chan" ),
        "code": connect_simple_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::YansWifiChannel", "phys" ),
        "to":   ( "ns3", "ns3::YansWifiPhy", "chan" ),  
        "code": connect_simple_channel_device,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::LogDistancePropagationLossModel", "prev" ),
        "to":   ( "ns3", "ns3::YansWifiChannel", "loss" ),  
        "code": connect_loss_channel,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::LogDistancePropagationLossModel", "prev" ),
        "to":   ( "ns3", "ns3::LogDistancePropagationLossModel", "next" ),  
        "code": connect_next_loss,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::ConstantSpeedPropagationDelayModel", "chan" ),
        "to":   ( "ns3", "ns3::YansWifiChannel", "delay" ),  
        "code": connect_delay_channel,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::OnOffApplication", "node" ),
        "code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::PacketSink", "node" ),
        "code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::UdpEchoClient", "node" ),
        "code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::UdpEchoServer", "node" ),
        "code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "apps" ),
        "to":   ( "ns3", "ns3::V4Ping", "node" ),
        "code": connect_node_application,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::ArpL3Protocol", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::Icmpv4L4Protocol", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::Ipv4L3Protocol", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::UdpL4Protocol", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "protos" ),
        "to":   ( "ns3", "ns3::TcpL4Protocol", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::ConstantAccelerationMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::ConstantPositionMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::ConstantVelocityMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::HierarchicalMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::RandomDirection2dMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::RandomWalk2dMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::Node", "mobility" ),
        "to":   ( "ns3", "ns3::RandomWaypointMobilityModel", "node" ),
        "code": connect_node_other,
        "can_cross": False
    }),
    dict({
        "from": ( "ns3", "ns3::FileDescriptorNetDevice", "fd" ),
        "to":   ( "netns", "TapNodeInterface", "fd" ),
        "code": connect_fd_tap,
        "can_cross": False
    }),
]

traces = dict({
    "p2ppcap": dict({
                "name": "P2PPcapTrace",
                "help": "Trace to sniff packets from a P2P network device"
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
        "ns3_bindings": dict({
                "name": "ns3Bindings",
                "help": "Location of the ns-3 python binding",
                "type": Attribute.STRING,
                "value": None,
                "range": None,
                "allowed": None,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string # TODO: validation.is_path
            }),
         "ns3_library": dict({
                "name": "ns3Library",
                "help": "Location of the ns-3 library .so file",
                "type": Attribute.STRING,
                "value": None,
                "range": None,
                "allowed": None,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string # TODO: validation.is_path
            }),
         "simu_impl_type": dict({
                "name": "SimulatorImplementationType",
                "help": "The object class to use as the simulator implementation",
                "type": Attribute.STRING,
                "value": None,
                "range": None,
                "allowed": None,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
          "checksum": dict({
                "name": "ChecksumEnabled",
                "help": "A global switch to enable all checksums for all protocols",
                "type": Attribute.BOOL,
                "value": False,
                "range": None,
                "allowed": None,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_bool
            })
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
    def factories_order(self):
        return factories_order

    @property
    def factories_info(self):
        from factories_metadata_v3_9_RC3 import factories_info
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

