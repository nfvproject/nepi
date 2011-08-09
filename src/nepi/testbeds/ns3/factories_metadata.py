#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util import tags
from nepi.util.constants import AF_INET, ApplicationStatus as AS, \
        FactoryCategories as FC
from nepi.util.tunchannel_impl import \
    preconfigure_tunchannel, postconfigure_tunchannel, \
    wait_tunchannel, create_tunchannel
import re

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

l4_protocols = dict({
    "Icmpv4L4Protocol": 1,
    "UdpL4Protocol": 17,
    "TcpL4Protocol": 6,
})

service_flow_direction = dict({
    "SF_DIRECTION_UP": 1,
    "SF_DIRECTION_DOWN": 0,
})

service_flow_scheduling_type = dict ({
    "SF_TYPE_NONE": 0,
    "SF_TYPE_UNDEF": 1, 
    "SF_TYPE_BE": 2,
    "SF_TYPE_NRTPS": 3,
    "SF_TYPE_RTPS": 4,
    "SF_TYPE_UGS": 6, 
    "SF_TYPE_ALL": 255
})

def _get_ipv4_protocol_guid(testbed_instance, node_guid):
    # search for the Ipv4L3Protocol asociated with the device
    protos_guids = testbed_instance.get_connected(node_guid, "protos", "node")
    if len(protos_guids) == 0:
        raise RuntimeError("No protocols where found for the node %d" % node_guid)
    ipv4_guid = None
    for proto_guid in protos_guids:
        proto_factory_id = testbed_instance._create[proto_guid]
        if proto_factory_id == "ns3::Ipv4L3Protocol":
            ipv4_guid = proto_guid
            break
    if not ipv4_guid:
        raise RuntimeError("No Ipv4L3Protocol associated to node %d. Can't add Ipv4 addresses" % node_guid)
    return ipv4_guid

def _get_node_guid(testbed_instance, guid):
    # search for the node asociated with the device
    node_guids = testbed_instance.get_connected(guid, "node", "devs")
    if len(node_guids) == 0:
        raise RuntimeError("Can't instantiate interface %d outside node" % guid)
    node_guid = node_guids[0]
    return node_guid

def _get_dev_number(testbed_instance, guid):
    node_guid = _get_node_guid(testbed_instance, guid)
    dev_guids = testbed_instance.get_connected(node_guid, "devs", "node")
    interface_number = 0
    for guid_ in dev_guids:
        if guid_ == guid:
            break
        interface_number += 1
    return interface_number

def _follow_trace(testbed_instance, guid, trace_id, filename):
    testbed_instance.follow_trace(guid, trace_id, filename)
    filepath = testbed_instance.trace_filepath(guid, trace_id)
    return filepath

### create traces functions ###

def p2pascii_trace(testbed_instance, guid, trace_id):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-p2p-node-%d-dev-%d.tr" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.PointToPointHelper()
    asciiHelper = testbed_instance.ns3.AsciiTraceHelper()
    stream = asciiHelper.CreateFileStream(filepath)
    helper.EnableAscii(stream, element)

def p2ppcap_trace(testbed_instance, guid, trace_id):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-p2p-node-%d-dev-%d.pcap" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.PointToPointHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

def _csmapcap_trace(testbed_instance, guid, trace_id, promisc):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-csma-node-%d-dev-%d.pcap" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.CsmaHelper()
    helper.EnablePcap(filepath, element, promiscuous = promisc, 
            explicitFilename = True)

def csmapcap_trace(testbed_instance, guid, trace_id):
    promisc = False
    _csmapcap_trace(testbed_instance, guid, trace_id, promisc)

def csmapcap_promisc_trace(testbed_instance, guid, trace_id):
    promisc = True
    _csmapcap_trace(testbed_instance, guid, trace_id, promisc)

def fdpcap_trace(testbed_instance, guid, trace_id):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-fd-node-%d-dev-%d.pcap" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.FdNetDeviceHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

def fdascii_trace(testbed_instance, guid, trace_id):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-fd-node-%d-dev-%d.tr" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.FdNetDeviceHelper()
    asciiHelper = testbed_instance.ns3.AsciiTraceHelper()
    stream = asciiHelper.CreateFileStream(filepath)
    helper.EnableAscii(stream, element)

def yanswifipcap_trace(testbed_instance, guid, trace_id):
    dev_guid = testbed_instance.get_connected(guid, "dev", "phy")[0]
    node_guid = _get_node_guid(testbed_instance, dev_guid)
    interface_number = _get_dev_number(testbed_instance, dev_guid)
    element = testbed_instance._elements[dev_guid]
    filename = "trace-yanswifi-node-%d-dev-%d.pcap" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.YansWifiPhyHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

def wimaxascii_trace(testbed_instance, guid, trace_id):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-wimax-node-%d-dev-%d.tr" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.WimaxHelper()
    asciiHelper = testbed_instance.ns3.AsciiTraceHelper()
    stream = asciiHelper.CreateFileStream (filepath)
    helper.EnableAscii(stream, element)
    #helper.EnableLogComponents()

def wimaxpcap_trace(testbed_instance, guid, trace_id):
    node_guid = _get_node_guid(testbed_instance, guid)
    interface_number = _get_dev_number(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    filename = "trace-wimax-node-%d-dev-%d.pcap" % (node_guid, interface_number)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    helper = testbed_instance.ns3.WimaxHelper()
    helper.EnablePcap(filepath, element, explicitFilename = True)

def rtt_trace(testbed_instance, guid, trace_id):
    element = testbed_instance._elements[guid]
    helper = testbed_instance.ns3.ScalarTraceHelper()
    prefix = "trace-app-%d" % (guid, )
    filename = helper.GetFilenameFromSource(prefix, element, trace_id)
    filepath = _follow_trace(testbed_instance, guid, trace_id, filename)
    prefix = filepath[:filepath.find(prefix)+len(prefix)]
    helper.EnableTrace(element, trace_id, prefix, "T")

trace_functions = dict({
    "P2PPcapTrace": p2ppcap_trace,
    "P2PAsciiTrace": p2pascii_trace,
    "CsmaPcapTrace": csmapcap_trace,
    "CsmaPcapPromiscTrace": csmapcap_promisc_trace,
    "FdPcapTrace": fdpcap_trace,
    "FdAsciiTrace": fdascii_trace,
    "YansWifiPhyPcapTrace": yanswifipcap_trace,
    "WimaxPcapTrace": wimaxpcap_trace,
    "WimaxAsciiTrace": wimaxascii_trace,
    "Rtt": rtt_trace,
    })

### Creation functions ###

def create_element(testbed_instance, guid):
    element_factory = testbed_instance.ns3.ObjectFactory()
    factory_id = testbed_instance._create[guid]
    element_factory.SetTypeId(factory_id) 
    construct_parameters = testbed_instance._get_construct_parameters(guid)
    for name, value in construct_parameters.iteritems():
        ns3_value = testbed_instance._to_ns3_value(guid, name, value)
        element_factory.Set(name, ns3_value)
    element = element_factory.Create()
    testbed_instance._elements[guid] = element

def create_node(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    element.AggregateObject(testbed_instance.ns3.PacketSocketFactory())

def create_wifi_standard_model(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    standard = parameters.get("Standard")
    if not standard:
        raise RuntimeError("No wifi standard set for %d" % guid)
    element.ConfigureStandard(wifi_standards[standard])

def create_waypoint_mobility(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    ns3 = testbed_instance.ns3
    waypoints = parameters.get("WaypointList", "")
    waypoints = re.sub(" |\(|\)", "", waypoints)
    for swp in waypoints.split(","):
        dwp = swp.split(":")
        t = str(dwp[0])
        time = ns3.Time(t)
        pos = ns3.Vector(float(dwp[1]), float(dwp[2]), float(dwp[3]))
        waypoint = ns3.Waypoint(time, pos)
        element.AddWaypoint(waypoint)

def create_ipv4protocol(testbed_instance, guid):
    create_element(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    list_routing = testbed_instance.ns3.Ipv4ListRouting()
    element.SetRoutingProtocol(list_routing)
    static_routing = testbed_instance.ns3.Ipv4StaticRouting()
    list_routing.AddRoutingProtocol(static_routing, 1)

def create_element_no_constructor(testbed_instance, guid):
    """ Create function for ns3 classes for which 
        TypeId.HasConstructor == False"""
    factory_id = testbed_instance._create[guid]
    factory_name = factory_id.replace("ns3::", "")
    constructor = getattr(testbed_instance.ns3, factory_name)
    element = constructor()
    testbed_instance._elements[guid] = element

def create_base_station(testbed_instance, guid):
    node_guid = _get_node_guid(testbed_instance, guid)
    node = testbed_instance._elements[node_guid]
    phy_guids = testbed_instance.get_connected(guid, "phy", "dev")
    if len(phy_guids) == 0:
        raise RuntimeError("No PHY was found for station %d" % guid)
    phy = testbed_instance._elements[phy_guids[0]]
    uplnk_guids = testbed_instance.get_connected(guid, "uplnk", "dev")
    if len(uplnk_guids) == 0:
        raise RuntimeError("No uplink scheduler was found for station %d" % guid)
    uplnk = testbed_instance._elements[uplnk_guids[0]]
    dwnlnk_guids = testbed_instance.get_connected(guid, "dwnlnk", "dev")
    if len(dwnlnk_guids) == 0:
        raise RuntimeError("No downlink scheduler was found for station %d" % guid)
    dwnlnk = testbed_instance._elements[dwnlnk_guids[0]]
    element = testbed_instance.ns3.BaseStationNetDevice(node, phy, uplnk, dwnlnk)
    testbed_instance._elements[guid] = element

def create_subscriber_station(testbed_instance, guid):
    node_guid = _get_node_guid(testbed_instance, guid)
    node = testbed_instance._elements[node_guid]
    phy_guids = testbed_instance.get_connected(guid, "phy", "dev")
    if len(phy_guids) == 0:
        raise RuntimeError("No PHY was found for station %d" % guid)
    phy = testbed_instance._elements[phy_guids[0]]
    element = testbed_instance.ns3.SubscriberStationNetDevice(node, phy)
    element.SetModulationType(testbed_instance.ns3.WimaxPhy.MODULATION_TYPE_QAM16_12)
    testbed_instance._elements[guid] = element

def create_wimax_channel(testbed_instance, guid):
    element = testbed_instance.ns3.SimpleOfdmWimaxChannel(testbed_instance.ns3.SimpleOfdmWimaxChannel.COST231_PROPAGATION)
    testbed_instance._elements[guid] = element

def create_wimax_phy(testbed_instance, guid):
    element = testbed_instance.ns3.SimpleOfdmWimaxPhy()
    testbed_instance._elements[guid] = element

def create_service_flow(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    direction = parameters.get("Direction")
    if direction == None:
        raise RuntimeError("No SchedulingType was found for service flow %d" % guid)
    sched = parameters.get("SchedulingType")
    if sched == None:
        raise RuntimeError("No SchedulingType was found for service flow %d" % guid)
    ServiceFlow = testbed_instance.ns3.ServiceFlow
    direction = service_flow_direction[direction]
    sched = service_flow_scheduling_type[sched]
    element = ServiceFlow(direction)
    element.SetCsSpecification(ServiceFlow.IPV4)
    element.SetServiceSchedulingType(sched) 
    element.SetMaxSustainedTrafficRate(100)
    element.SetMinReservedTrafficRate(1000000)
    element.SetMinTolerableTrafficRate(1000000)
    element.SetMaximumLatency(100)
    element.SetMaxTrafficBurst(2000)
    element.SetTrafficPriority(1)
    element.SetUnsolicitedGrantInterval(1)
    element.SetMaxSustainedTrafficRate(70)
    element.SetToleratedJitter(10)
    element.SetSduSize(49)
    element.SetRequestTransmissionPolicy(0)
    testbed_instance._elements[guid] = element

def create_ipcs_classifier_record(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    src_address = parameters.get("SrcAddress")
    if src_address == None:
        raise RuntimeError("No SrcAddress was found for classifier %d" % guid)
    src_address = testbed_instance.ns3.Ipv4Address(src_address)
    src_mask = parameters.get("SrcMask")
    if src_mask == None:
        raise RuntimeError("No SrcMask was found for classifier %d" % guid)
    src_mask = testbed_instance.ns3.Ipv4Mask(src_mask)
    dst_address = parameters.get("DstAddress")
    if dst_address == None:
        raise RuntimeError("No Dstddress was found for classifier %d" % guid)
    dst_address = testbed_instance.ns3.Ipv4Address(dst_address)
    dst_mask = parameters.get("DstMask")
    if dst_mask == None:
        raise RuntimeError("No DstMask was found for classifier %d" % guid)
    dst_mask = testbed_instance.ns3.Ipv4Mask(dst_mask)
    src_port_low = parameters.get("SrcPortLow")
    if src_port_low == None:
        raise RuntimeError("No SrcPortLow was found for classifier %d" % guid)
    src_port_high = parameters.get("SrcPortHigh")
    if src_port_high == None:
        raise RuntimeError("No SrcPortHigh was found for classifier %d" % guid)
    dst_port_low = parameters.get("DstPortLow")
    if dst_port_low == None:
        raise RuntimeError("No DstPortLow was found for classifier %d" % guid)
    dst_port_high = parameters.get("DstPortHigh")
    if dst_port_high == None:
        raise RuntimeError("No DstPortHigh was found for classifier %d" % guid)
    protocol = parameters.get("Protocol")
    if protocol == None or protocol not in l4_protocols:
        raise RuntimeError("No Protocol was found for classifier %d" % guid)
    priority = parameters.get("Priority")
    if priority == None:
        raise RuntimeError("No Priority was found for classifier %d" % guid)
    element = testbed_instance.ns3.IpcsClassifierRecord(src_address, src_mask,
        dst_address, dst_mask, src_port_low, src_port_high, dst_port_low, 
        dst_port_high, l4_protocols[protocol], priority)
    testbed_instance._elements[guid] = element

### Start/Stop functions ###

def start_application(testbed_instance, guid):
    element = testbed_instance.elements[guid]
    # BUG: without doing this explicit call it doesn't start!!!
    # Shouldn't be enough to set the StartTime?
    element.Start()

def stop_application(testbed_instance, guid):
    element = testbed_instance.elements[guid]
    now = testbed_instance.ns3.Simulator.Now()
    element.SetStopTime(now)

### Status functions ###

def status_application(testbed_instance, guid):
    if guid not in testbed_instance.elements.keys():
        raise RuntimeError("Can't get status on guid %d" % guid )
    now = testbed_instance.ns3.Simulator.Now()
    if now.IsZero():
        return AS.STATUS_NOT_STARTED
    app = testbed_instance.elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    start_value = parameters.get("StartTime")
    if start_value != None:
        start_time = testbed_instance.ns3.Time(start_value)
        if now.Compare(start_time) < 0:
            return AS.STATUS_NOT_STARTED
    stop_value = parameters.get("StopTime")
    if stop_value != None:
        stop_time = testbed_instance.ns3.Time(stop_value)
        if now.Compare(stop_time) < 0:
            return AS.STATUS_RUNNING
        else:
            return AS.STATUS_FINISHED
    return AS.STATUS_UNDETERMINED

### Configure functions ###

def configure_traces(testbed_instance, guid):
    traces = testbed_instance._get_traces(guid)
    for trace_id in traces:
        trace_func = trace_functions[trace_id]
        trace_func(testbed_instance, guid, trace_id)

def configure_element(testbed_instance, guid):
    configure_traces(testbed_instance, guid)

def configure_device(testbed_instance, guid):
    configure_traces(testbed_instance, guid)

    element = testbed_instance._elements[guid]

    parameters = testbed_instance._get_parameters(guid)
    address = parameters.get("macAddress")
    if address:
        macaddr = testbed_instance.ns3.Mac48Address(address)
    else:
        macaddr = testbed_instance.ns3.Mac48Address.Allocate()
    element.SetAddress(macaddr)

    if not guid in testbed_instance._add_address:
        return
    # search for the node asociated with the device
    node_guid = _get_node_guid(testbed_instance, guid)
    node = testbed_instance.elements[node_guid]
    # search for the Ipv4L3Protocol asociated with the device
    ipv4_guid = _get_ipv4_protocol_guid(testbed_instance, node_guid)
    ipv4 = testbed_instance._elements[ipv4_guid]
    ns3 = testbed_instance.ns3
    # add addresses 
    addresses = testbed_instance._add_address[guid]
    for address in addresses:
        (address, netprefix, broadcast) = address
        # TODO: missing IPV6 addresses!!
        ifindex = ipv4.AddInterface(element)
        inaddr = ns3.Ipv4InterfaceAddress(ns3.Ipv4Address(address),
                ns3.Ipv4Mask("/%d" % netprefix))
        ipv4.AddAddress(ifindex, inaddr)
        ipv4.SetMetric(ifindex, 1)
        ipv4.SetUp(ifindex)

def _add_static_route(ns3, static_routing, 
        address, netprefix, nexthop_address, ifindex):
    if netprefix == 0:
        # Default route: 0.0.0.0/0
        static_routing.SetDefaultRoute(nexthop_address, ifindex) 
    elif netprefix == 32:
        # Host route: x.y.z.w/32
        static_routing.AddHostRouteTo(address, nexthop_address, ifindex) 
    else:
        # Network route: x.y.z.w/n
        mask = ns3.Ipv4Mask("/%d" % netprefix) 
        static_routing.AddNetworkRouteTo(address, mask, nexthop_address, 
                ifindex) 

def _add_static_route_if(ns3, static_routing, address, netprefix, ifindex):
    if netprefix == 0:
        # Default route: 0.0.0.0/0
        static_routing.SetDefaultRoute(ifindex) 
    elif netprefix == 32:
        # Host route: x.y.z.w/32
        static_routing.AddHostRouteTo(address, ifindex) 
    else:
        # Network route: x.y.z.w/n
        mask = ns3.Ipv4Mask("/%d" % netprefix) 
        static_routing.AddNetworkRouteTo(address, mask, ifindex) 

def configure_node(testbed_instance, guid):
    configure_traces(testbed_instance, guid)

    element = testbed_instance._elements[guid]
    if not guid in testbed_instance._add_route:
        return
    # search for the Ipv4L3Protocol asociated with the device
    ipv4_guid = _get_ipv4_protocol_guid(testbed_instance, guid)
    ipv4 = testbed_instance._elements[ipv4_guid]
    list_routing = ipv4.GetRoutingProtocol()
    (static_routing, priority) = list_routing.GetRoutingProtocol(0)
    ns3 = testbed_instance.ns3
    routes = testbed_instance._add_route[guid]
    for route in routes:
        (destination, netprefix, nexthop, metric) = route
        address = ns3.Ipv4Address(destination)
        if nexthop:
            nexthop_address = ns3.Ipv4Address(nexthop)
            ifindex = -1
            # TODO: HACKISH way of getting the ifindex... improve this
            nifaces = ipv4.GetNInterfaces()
            for ifidx in xrange(nifaces):
                iface = ipv4.GetInterface(ifidx)
                naddress = iface.GetNAddresses()
                for addridx in xrange(naddress):
                    ifaddr = iface.GetAddress(addridx)
                    ifmask = ifaddr.GetMask()
                    ifindex = ipv4.GetInterfaceForPrefix(nexthop_address, ifmask)
                    if ifindex == ifidx:
                        break
            if ifindex < 0:
                # Check previous ptp routes
                for chaindest, chainprefix, chainhop in routes:
                    if chaindest == nexthop and chainprefix == 32:
                        chainhop_address = ns3.Ipv4Address(chainhop)
                        for ifidx in xrange(nifaces):
                            iface = ipv4.GetInterface(ifidx)
                            naddress = iface.GetNAddresses()
                            for addridx in xrange(naddress):
                                ifaddr = iface.GetAddress(addridx)
                                ifmask = ifaddr.GetMask()
                                ifindex = ipv4.GetInterfaceForPrefix(chainhop_address, ifmask)
                                if ifindex == ifidx:
                                    break
            if ifindex < 0:
                raise RuntimeError, "Cannot associate interface for routing entry:" \
                    "%s/%s -> %s. At node %s" % (destination, netprefix, nexthop, guid)
            _add_static_route(ns3, static_routing, 
                address, netprefix, nexthop_address, ifindex)
        else:
            mask = ns3.Ipv4Mask("/%d" % netprefix) 
            ifindex = ipv4.GetInterfaceForPrefix(address, mask)
            if ifindex < 0:
                raise RuntimeError, "Cannot associate interface for routing entry:" \
                    "%s/%s -> %s. At node %s" % (destination, netprefix, nexthop, guid)
            _add_static_route_if(ns3, static_routing, 
                address, netprefix, nexthop_address, ifindex)

def configure_station(testbed_instance, guid):
    configure_device(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    element.Start()

###  Factories  ###

factories_order = ["ns3::BasicEnergySource",
    "ns3::WifiRadioEnergyModel",
    "ns3::BSSchedulerRtps",
    "ns3::BSSchedulerSimple",
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
    "ns3::StaWifiMac",
    "ns3::ApWifiMac",
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
    "ns3::FdNetDevice",
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
    "ns3::EnergySourceContainer",
    "ns3::BSSchedulerRtps",
    "ns3::BSSchedulerSimple",
    "ns3::SimpleOfdmWimaxChannel",
    "ns3::SimpleOfdmWimaxPhy",
    "ns3::UplinkSchedulerMBQoS",
    "ns3::UplinkSchedulerRtps",
    "ns3::UplinkSchedulerSimple",
    "ns3::IpcsClassifierRecord",
    "ns3::ServiceFlow",
    "ns3::BaseStationNetDevice",
    "ns3::SubscriberStationNetDevice",
 ]

factories_info = dict({
    "ns3::Ping6": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxPackets",
            "Interval",
            "RemoteIpv6",
            "LocalIpv6",
            "PacketSize",
            "StartTime",
            "StopTime"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::UdpL4Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["ProtocolNumber"],
        "tags": [tags.PROTOCOL],
    }),
     "ns3::RandomDiscPositionAllocator": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Theta",
            "Rho",
            "X",
            "Y"],
        "tags": [tags.MOBILE],
    }),
     "ns3::Node": dict({
        "category": FC.CATEGORY_NODES,
        "create_function": create_node,
        "configure_function": configure_node,
        "help": "",
        "connector_types": ["devs", "apps", "protos", "mobility"],
        "tags": [tags.NODE, tags.ALLOW_ROUTES],
    }),
     "ns3::GridPositionAllocator": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["GridWidth",
            "MinX",
            "MinY",
            "DeltaX",
            "DeltaY",
            "LayoutType"],
    }),
     "ns3::TapBridge": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Mtu",
            "DeviceName",
            "Gateway",
            "IpAddress",
            "MacAddress",
            "Netmask",
            "Start",
            "Stop"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::FlowMonitor": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxPerHopDelay",
            "DelayBinWidth",
            "JitterBinWidth",
            "PacketSizeBinWidth",
            "FlowInterruptionsBinWidth",
            "FlowInterruptionsMinTime"],
    }),
     "ns3::ConstantVelocityMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Position",
           "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::V4Ping": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["Remote",
            "Verbose",
            "Interval",
            "Size",
            "StartTime",
            "StopTime"],
        "traces": ["rtt"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::dot11s::PeerLink": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["RetryTimeout",
            "HoldingTimeout",
            "ConfirmTimeout",
            "MaxRetries",
            "MaxBeaconLoss",
            "MaxPacketFailure"],
    }),
     "ns3::PointToPointNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_device,
        "help": "",
        "connector_types": ["node", "err", "queue", "chan"],
        "attributes": ["Mtu",
            "Address",
            "DataRate",
            "InterframeGap"],
        "traces": ["p2ppcap", "p2pascii"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::NakagamiPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Distance1",
            "Distance2",
            "m0",
            "m1",
            "m2"],
    }),
     "ns3::AarfWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["SuccessK",
            "TimerK",
            "MaxSuccessThreshold",
            "MinTimerThreshold",
            "MinSuccessThreshold",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::Ipv6OptionJumbogram": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["OptionNumber"],
    }),
     "ns3::TwoRayGroundPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Lambda",
            "SystemLoss",
            "MinDistance",
            "HeightAboveZ"],
    }),
     "ns3::OnOffApplication": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["DataRate",
            "PacketSize",
            "Remote",
            "OnTime",
            "OffTime",
            "MaxBytes",
            "Protocol",
            "StartTime",
            "StopTime"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::AdhocWifiMac": dict({
        "category": FC.CATEGORY_MAC_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["CtsTimeout",
            "AckTimeout",
            "BasicBlockAckTimeout",
            "CompressedBlockAckTimeout",
            "Sifs",
            "EifsNoDifs",
            "Slot",
            "Pifs",
            "MaxPropagationDelay",
            "Ssid"],
    }),
     "ns3::ConstantAccelerationMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::GaussMarkovMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Bounds",
            "TimeStep",
            "Alpha",
            "MeanVelocity",
            "MeanDirection",
            "MeanPitch",
            "NormalVelocity",
            "NormalDirection",
            "NormalPitch",
            "Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::dot11s::HwmpProtocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["RandomStart",
            "MaxQueueSize",
            "Dot11MeshHWMPmaxPREQretries",
            "Dot11MeshHWMPnetDiameterTraversalTime",
            "Dot11MeshHWMPpreqMinInterval",
            "Dot11MeshHWMPperrMinInterval",
            "Dot11MeshHWMPactiveRootTimeout",
            "Dot11MeshHWMPactivePathTimeout",
            "Dot11MeshHWMPpathToRootInterval",
            "Dot11MeshHWMPrannInterval",
            "MaxTtl",
            "UnicastPerrThreshold",
            "UnicastPreqThreshold",
            "UnicastDataThreshold",
            "DoFlag",
            "RfFlag"],
    }),
     "ns3::NscTcpL4Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Library",
          "ProtocolNumber"],
    }),
     "ns3::dot11s::AirtimeLinkMetricCalculator": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Dot11sMeshHeaderLength"],
    }),
     "ns3::UanMacCw": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["CW",
           "SlotTime"],
    }),
     "ns3::AthstatsWifiTraceSink": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Interval"],
    }),
     "ns3::FlameStack": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::UanMacRc": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["RetryRate",
            "MaxFrames",
            "QueueLimit",
            "SIFS",
            "NumberOfRates",
            "MinRetryRate",
            "RetryStep",
            "NumberOfRetryRates",
            "MaxPropDelay"],
    }),
     "ns3::WaypointMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_waypoint_mobility,
        "configure_function": configure_element,
        "help": "Waypoint-based mobility model.",
        "connector_types": ["node"],
        "attributes": ["WaypointsLeft",
            "Position",
            "Velocity",
            "WaypointList"],
        "tags": [tags.MOBILE],
    }),
     "ns3::FdNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_device,
        "help": "Network interface associated to a file descriptor",
        "connector_types": ["node", "->fd"],
        "attributes": ["Address", 
            "tun_proto", "tun_addr", "tun_port", "tun_key"],
        "traces": ["fdpcap", "fdascii"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::Nepi::TunChannel": dict({
        "category": FC.CATEGORY_TUNNELS,
        "create_function": create_tunchannel,
        "preconfigure_function": preconfigure_tunchannel,
        "configure_function": postconfigure_tunchannel,
        "prestart_function": wait_tunchannel,
        "help": "Channel to forward FdNetDevice data to "
                "other TAP interfaces supporting the NEPI tunneling protocol.",
        "connector_types": ["fd->", "udp", "tcp"],
        "allow_addresses": False,
        "attributes": ["tun_proto", "tun_addr", "tun_port", "tun_key"],
        "tags": [tags.TUNNEL],
 
    }),
     "ns3::CsmaNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_device,
        "help": "CSMA (carrier sense, multiple access) interface",
        "connector_types": ["node", "chan", "err", "queue"],
        "attributes": ["Address",
            "Mtu",
            "SendEnable",
            "ReceiveEnable"],
        "traces": ["csmapcap", "csmapcap_promisc"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::UanPropModelThorp": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["SpreadCoef"],
    }),
     "ns3::Icmpv6L4Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["DAD",
            "ProtocolNumber"],
    }),
     "ns3::SimpleNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node", "chan"],
        "attributes": [],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::FriisPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Lambda",
            "SystemLoss",
            "MinDistance"],
    }),
     "ns3::Ipv6OptionRouterAlert": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["OptionNumber"],
    }),
     "ns3::UniformDiscPositionAllocator": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["rho",
            "X",
            "Y"],
        "tags": [tags.MOBILE],
    }),
     "ns3::RandomBoxPositionAllocator": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["X",
            "Y",
            "Z"],
        "tags": [tags.MOBILE],
    }),
     "ns3::Ipv6ExtensionDestination": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::LoopbackNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::ConstantSpeedPropagationDelayModel": dict({
        "category": FC.CATEGORY_DELAY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["chan"],
        "attributes": ["Speed"],
    }),
     "ns3::Ipv6ExtensionHopByHop": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::BridgeChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::Radvd": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["StartTime",
            "StopTime"],
    }),
     "ns3::PacketSocket": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["RcvBufSize"],
    }),
     "ns3::flame::FlameProtocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["BroadcastInterval",
            "MaxCost"],
    }),
     "ns3::Cost231PropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Lambda",
            "Frequency",
            "BSAntennaHeight",
            "SSAntennaHeight",
            "MinDistance"],
    }),
     "ns3::Ipv6ExtensionESP": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::CaraWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["ProbeThreshold",
            "FailureThreshold",
            "SuccessThreshold",
            "Timeout",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    
    }),
     "ns3::RttMeanDeviation": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Gain",
            "MaxMultiplier",
            "InitialEstimation",
            "MinRTO"],
    }),
     "ns3::Icmpv4L4Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["ProtocolNumber"],
    }),
     "ns3::WaveformGenerator": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Period",
            "DutyCycle"],
    }),
     "ns3::YansWifiChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["phys", "delay", "loss"],
        "attributes": [],
    }),
     "ns3::SimpleChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["devs"],
        "attributes": [],
    }),
     "ns3::Ipv6ExtensionFragment": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::Dot11sStack": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Root"],
    }),
     "ns3::FriisSpectrumPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::RandomRectanglePositionAllocator": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["X",
           "Y"],
        "tags": [tags.MOBILE],
    }),
     "ns3::HierarchicalMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::ThreeLogDistancePropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Distance0",
            "Distance1",
            "Distance2",
            "Exponent0",
            "Exponent1",
            "Exponent2",
            "ReferenceLoss"],
    }),
     "ns3::UanNoiseModelDefault": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Wind",
            "Shipping"],
    }),
     "ns3::dot11s::HwmpRtable": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::PacketBurst": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::RandomPropagationDelayModel": dict({
        "category": FC.CATEGORY_DELAY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Variable"],
    }),
     "ns3::ArpL3Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": [],
    }),
     "ns3::SteadyStateRandomWaypointMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MinSpeed",
            "MaxSpeed",
            "MinPause",
            "MaxPause",
            "MinX",
            "MaxX",
            "MinY",
            "MaxY",
            "Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::BaseStationNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_base_station,
        "configure_function": configure_station,
        "help": "Base station for wireless mobile network",
        "connector_types": ["node", "chan", "phy", "uplnk", "dwnlnk"],
        "attributes": ["InitialRangInterval",
            "DcdInterval",
            "UcdInterval",
            "IntervalT8",
            "RangReqOppSize",
            "BwReqOppSize",
            "MaxRangCorrectionRetries",
            "Mtu",
            "RTG",
            "TTG"],
        "traces": ["wimaxpcap", "wimaxascii"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::UdpServer": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["Port",
            "PacketWindowSize",
            "StartTime",
            "StopTime"],
    }),
     "ns3::AarfcdWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["SuccessK",
            "TimerK",
            "MaxSuccessThreshold",
            "MinTimerThreshold",
            "MinSuccessThreshold",
            "MinRtsWnd",
            "MaxRtsWnd",
            "TurnOffRtsAfterRateDecrease",
            "TurnOnRtsAfterRateIncrease",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::UanTransducerHd": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::LogDistancePropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["prev", "next"],
        "attributes": ["Exponent",
            "ReferenceDistance",
            "ReferenceLoss"],
    }),
     "ns3::EmuNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node", "queue"],
        "attributes": ["Mtu",
            "Address",
            "DeviceName",
            "Start",
            "Stop",
            "RxQueueSize"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::Ipv6ExtensionLooseRouting": dict({
        "category": FC.CATEGORY_ROUTING,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::RandomWaypointMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Speed",
            "Pause",
            "Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::RangePropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxRange"],
    }),
     "ns3::AlohaNoackNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Address",
            "Mtu"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::MatrixPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["DefaultLoss"],
    }),
     "ns3::WifiNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_device,
        "help": "",
        "connector_types": ["node", "mac", "phy", "manager"],
        "attributes": ["Mtu"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::CsmaChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["devs"],
        "attributes": ["DataRate",
            "Delay"],
    }),
     "ns3::BridgeNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Mtu",
           "EnableLearning",
           "ExpirationTime"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::Ipv6ExtensionRouting": dict({
        "category": FC.CATEGORY_ROUTING,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::StaWifiMac": dict({
        "category": FC.CATEGORY_MAC_MODELS,
        "create_function": create_wifi_standard_model,
        "configure_function": configure_element,
        "help": "Station Wifi MAC Model",
        "connector_types": ["dev"],
        "attributes": ["ProbeRequestTimeout",
            "AssocRequestTimeout",
            "MaxMissedBeacons",
            "CtsTimeout",
            "AckTimeout",
            "BasicBlockAckTimeout",
            "CompressedBlockAckTimeout",
            "Sifs",
            "EifsNoDifs",
            "Slot",
            "Pifs",
            "MaxPropagationDelay",
            "Ssid",
            "Standard"],
    }),
     "ns3::UdpEchoClient": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["MaxPackets",
            "Interval",
            "RemoteAddress",
            "RemotePort",
            "PacketSize",
            "StartTime",
            "StopTime"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::UdpClient": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["MaxPackets",
            "Interval",
            "RemoteAddress",
            "RemotePort",
            "PacketSize",
            "StartTime",
            "StopTime"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::PointToPointChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev2"],
        "attributes": ["Delay"],
    }),
     "ns3::Ipv6StaticRouting": dict({
        "category": FC.CATEGORY_ROUTING,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::DropTailQueue": dict({
        "category": FC.CATEGORY_QUEUES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["MaxPackets",
           "MaxBytes"],
    }),
     "ns3::ConstantPositionMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::FixedRssLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Rss"],
    }),
     "ns3::EnergySourceContainer": dict({
        "category": FC.CATEGORY_ENERGY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::RandomWalk2dMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Bounds",
            "Time",
            "Distance",
            "Mode",
            "Direction",
            "Speed",
            "Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::ListPositionAllocator": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::dot11s::PeerManagementProtocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxNumberOfPeerLinks",
            "MaxBeaconShiftValue",
            "EnableBeaconCollisionAvoidance"],
    }),
     "ns3::MeshPointDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Mtu"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::BasicEnergySource": dict({
        "category": FC.CATEGORY_ENERGY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["BasicEnergySourceInitialEnergyJ",
            "BasicEnergySupplyVoltageV",
            "PeriodicEnergyUpdateInterval"],
    }),
     "ns3::Ipv6OptionPadn": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["OptionNumber"],
    }),
     "ns3::ApWifiMac": dict({
        "category": FC.CATEGORY_MAC_MODELS,
        "create_function": create_wifi_standard_model,
        "configure_function": configure_element,
        "help": "Access point Wifi MAC Model",
        "connector_types": ["dev"],
        "attributes": ["BeaconInterval",
            "BeaconGeneration",
            "CtsTimeout",
            "AckTimeout",
            "BasicBlockAckTimeout",
            "CompressedBlockAckTimeout",
            "Sifs",
            "EifsNoDifs",
            "Slot",
            "Pifs",
            "MaxPropagationDelay",
            "Ssid",
            "Standard"],
    }),
     "ns3::YansErrorRateModel": dict({
        "category": FC.CATEGORY_ERROR_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::WifiMacQueue": dict({
        "category": FC.CATEGORY_QUEUES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxPacketNumber",
           "MaxDelay"],
    }),
     "ns3::NonCommunicatingNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::RateErrorModel": dict({
        "category": FC.CATEGORY_ERROR_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ErrorUnit",
            "ErrorRate",
            "RanVar",
            "IsEnabled"],
    }),
     "ns3::MeshWifiInterfaceMac": dict({
        "category": FC.CATEGORY_MAC_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["BeaconInterval",
            "RandomStart",
            "BeaconGeneration",
            "CtsTimeout",
            "AckTimeout",
            "BasicBlockAckTimeout",
            "CompressedBlockAckTimeout",
            "Sifs",
            "EifsNoDifs",
            "Slot",
            "Pifs",
            "MaxPropagationDelay",
            "Ssid"],
    }),
     "ns3::UanPhyCalcSinrDual": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::Ipv6ExtensionAH": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["ExtensionNumber"],
    }),
     "ns3::SingleModelSpectrumChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::YansWifiPhy": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_wifi_standard_model,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev", "err", "chan"],
        "attributes": ["EnergyDetectionThreshold",
            "CcaMode1Threshold",
            "TxGain",
            "RxGain",
            "TxPowerLevels",
            "TxPowerEnd",
            "TxPowerStart",
            "RxNoiseFigure",
            "ChannelSwitchDelay",
            "ChannelNumber",
            "Standard"],
        "traces": ["yanswifipcap"]
    }),
     "ns3::WifiRadioEnergyModel": dict({
        "category": FC.CATEGORY_ENERGY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["TxCurrentA",
            "RxCurrentA",
            "IdleCurrentA",
            "SleepCurrentA"],
    }),
     "ns3::EdcaTxopN": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["BlockAckThreshold",
            "MinCw",
            "MaxCw",
            "Aifsn"],
    }),
     "ns3::UanPhyPerGenDefault": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Threshold"],
    }),
     "ns3::IdealWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["BerThreshold",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::MultiModelSpectrumChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::HalfDuplexIdealPhy": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Rate"],
    }),
     "ns3::UanPhyCalcSinrDefault": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::ReceiveListErrorModel": dict({
        "category": FC.CATEGORY_ERROR_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["IsEnabled"],
    }),
     "ns3::SpectrumAnalyzer": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Resolution",
        "NoisePowerSpectralDensity"],
    }),
     "ns3::ConstantRateWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["DataMode",
            "ControlMode",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::Ipv6OptionPad1": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["OptionNumber"],
    }),
     "ns3::UdpTraceClient": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["RemoteAddress",
            "RemotePort",
            "MaxPacketSize",
            "StartTime",
            "StopTime"],
    }),
     "ns3::RraaWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["Basic",
            "Timeout",
            "ewndFor54mbps",
            "ewndFor48mbps",
            "ewndFor36mbps",
            "ewndFor24mbps",
            "ewndFor18mbps",
            "ewndFor12mbps",
            "ewndFor9mbps",
            "ewndFor6mbps",
            "poriFor48mbps",
            "poriFor36mbps",
            "poriFor24mbps",
            "poriFor18mbps",
            "poriFor12mbps",
            "poriFor9mbps",
            "poriFor6mbps",
            "pmtlFor54mbps",
            "pmtlFor48mbps",
            "pmtlFor36mbps",
            "pmtlFor24mbps",
            "pmtlFor18mbps",
            "pmtlFor12mbps",
            "pmtlFor9mbps",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::RandomPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Variable"],
    }),
     "ns3::UanChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::MinstrelWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["UpdateStatistics",
            "LookAroundRate",
            "EWMA",
            "SegmentSize",
            "SampleColumn",
            "PacketLength",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::UanPhyDual": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["CcaThresholdPhy1",
            "CcaThresholdPhy2",
            "TxPowerPhy1",
            "TxPowerPhy2",
            "RxGainPhy1",
            "RxGainPhy2",
            "SupportedModesPhy1",
            "SupportedModesPhy2"],
    }),
     "ns3::ListErrorModel": dict({
        "category": FC.CATEGORY_ERROR_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["IsEnabled"],
    }),
     "ns3::VirtualNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Mtu"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
     "ns3::UanPhyGen": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["CcaThreshold",
            "RxThreshold",
            "TxPower",
            "RxGain",
            "SupportedModes"],
    }),
     "ns3::Ipv6L3Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["DefaultTtl",
            "IpForward"],
    }),
     "ns3::PointToPointRemoteChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Delay"],
    }),
     "ns3::UanPhyPerUmodem": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::OnoeWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["UpdatePeriod",
            "RaiseThreshold",
            "AddCreditThreshold",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::QadhocWifiMac": dict({
        "category": FC.CATEGORY_MAC_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["CtsTimeout",
            "AckTimeout",
            "BasicBlockAckTimeout",
            "CompressedBlockAckTimeout",
            "Sifs",
            "EifsNoDifs",
            "Slot",
            "Pifs",
            "MaxPropagationDelay",
            "Ssid"],
    }),
     "ns3::JakesPropagationLossModel": dict({
        "category": FC.CATEGORY_LOSS_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["NumberOfRaysPerPath",
            "NumberOfOscillatorsPerRay",
            "DopplerFreq",
            "Distribution"],
    }),
     "ns3::PacketSink": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["Local",
            "Protocol",
            "StartTime",
            "StopTime"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::RandomDirection2dMobilityModel": dict({
        "category": FC.CATEGORY_MOBILITY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["Bounds",
            "RndSpeed",
            "Pause",
            "Position",
            "Velocity"],
        "tags": [tags.MOBILE],
    }),
     "ns3::UanMacAloha": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::MsduStandardAggregator": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxAmsduSize"],
    }),
     "ns3::DcaTxop": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MinCw",
            "MaxCw",
            "Aifsn"],
    }),
     "ns3::UanPhyCalcSinrFhFsk": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["NumberOfHops"],
    }),
     "ns3::UanPropModelIdeal": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": [],
    }),
     "ns3::UanMacRcGw": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["MaxReservations",
            "NumberOfRates",
            "RetryRate",
            "MaxPropDelay",
            "SIFS",
            "NumberOfNodes",
            "MinRetryRate",
            "RetryStep",
            "NumberOfRetryRates",
            "TotalRate",
            "RateStep",
            "FrameSize"],
    }),
     "ns3::NistErrorRateModel": dict({
        "category": FC.CATEGORY_ERROR_MODELS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["phy"],
        "attributes": [],
    }),
     "ns3::Ipv4L3Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_ipv4protocol,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["DefaultTtl",
            "IpForward",
            "WeakEsModel"],
    }),
     "ns3::aodv::RoutingProtocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["HelloInterval",
            "RreqRetries",
            "RreqRateLimit",
            "NodeTraversalTime",
            "NextHopWait",
            "ActiveRouteTimeout",
            "MyRouteTimeout",
            "BlackListTimeout",
            "DeletePeriod",
            "TimeoutBuffer",
            "NetDiameter",
            "NetTraversalTime",
            "PathDiscoveryTime",
            "MaxQueueLen",
            "MaxQueueTime",
            "AllowedHelloLoss",
            "GratuitousReply",
            "DestinationOnly",
            "EnableHello",
            "EnableBroadcast"],
    }),
     "ns3::TcpL4Protocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "attributes": ["RttEstimatorFactory",
            "ProtocolNumber"],
    }),
     "ns3::olsr::RoutingProtocol": dict({
        "category": FC.CATEGORY_PROTOCOLS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["HelloInterval",
            "TcInterval",
            "MidInterval",
            "HnaInterval",
            "Willingness"],
    }),
     "ns3::UdpEchoServer": dict({
        "category": FC.CATEGORY_APPLICATIONS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["node"],
        "stop_function": stop_application,
        "start_function": start_application,
        "status_function": status_application,
        "attributes": ["Port",
           "StartTime",
           "StopTime"],
        "tags": [tags.APPLICATION],
    }),
     "ns3::AmrrWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["UpdatePeriod",
            "FailureRatio",
            "SuccessRatio",
            "MaxSuccessThreshold",
            "MinSuccessThreshold",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::ArfWifiManager": dict({
        "category": FC.CATEGORY_MANAGERS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": ["dev"],
        "attributes": ["TimerThreshold",
            "SuccessThreshold",
            "IsLowLatency",
            "MaxSsrc",
            "MaxSlrc",
            "RtsCtsThreshold",
            "FragmentationThreshold",
            "NonUnicastMode"],
    }),
     "ns3::SubscriberStationNetDevice": dict({
        "category": FC.CATEGORY_DEVICES,
        "create_function": create_subscriber_station,
        "configure_function": configure_station,
        "help": "Subscriber station for mobile wireless network",
        "connector_types": ["node", "chan", "phy", "sflows"],
        "attributes": ["LostDlMapInterval",
            "LostUlMapInterval",
            "MaxDcdInterval",
            "MaxUcdInterval",
            "IntervalT1",
            "IntervalT2",
            "IntervalT3",
            "IntervalT7",
            "IntervalT12",
            "IntervalT20",
            "IntervalT21",
            "MaxContentionRangingRetries",
            "Mtu",
            "RTG",
            "TTG"],
        "traces": ["wimaxpcap", "wimaxascii"],
        "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
    }),
    "ns3::flame::FlameRtable": dict({
        "category": "",
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "",
        "connector_types": [],
        "attributes": ["Lifetime"],
    }),
    "ns3::BSSchedulerRtps": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "Simple downlink scheduler for rtPS flows",
        "connector_types": ["dev"],
        "attributes": [],
    }),
    "ns3::BSSchedulerSimple": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_element,
        "configure_function": configure_element,
        "help": "simple downlink scheduler for service flows",
        "connector_types": ["dev"],
        "attributes": [],
    }),
    "ns3::SimpleOfdmWimaxChannel": dict({
        "category": FC.CATEGORY_CHANNELS,
        "create_function": create_wimax_channel,
        "configure_function": configure_element,
        "help": "Wimax channel",
        "connector_types": ["devs"],
        "attributes": [],
    }),
    "ns3::SimpleOfdmWimaxPhy": dict({
        "category": FC.CATEGORY_PHY_MODELS,
        "create_function": create_wimax_phy,
        "configure_function": configure_element,
        "help": "Wimax Phy",
        "connector_types": ["dev"],
        "attributes": [],
    }),
    "ns3::UplinkSchedulerSimple": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_element_no_constructor,
        "configure_function": configure_element,
        "help": "Simple uplink scheduler for service flows",
        "connector_types": ["dev"],
        "attributes": [],
    }),
    "ns3::UplinkSchedulerRtps": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_element_no_constructor,
        "configure_function": configure_element,
        "help": "Simple uplink scheduler for rtPS flows",
        "connector_types": ["dev"],
        "attributes": [],
    }),
    "ns3::IpcsClassifierRecord": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_ipcs_classifier_record,
        "configure_function": configure_element,
        "help": "Classifier record for service flow",
        "connector_types": ["sflow"],
        "attributes": ["ClassifierSrcAddress", 
            "ClassifierSrcMask", 
            "ClassifierDstAddress",
            "ClassifierDstMask",
            "ClassifierSrcPortLow",
            "ClassifierSrcPortHigh",
            "ClassifierDstPortLow",
            "ClassifierDstPortHigh",
            "ClassifierProtocol",
            "ClassifierPriority"],
    }),   
    "ns3::ServiceFlow": dict({
        "category": FC.CATEGORY_SERVICE_FLOWS,
        "create_function": create_service_flow,
        "configure_function": configure_element,
        "help": "Service flow for QoS",
        "connector_types": ["classif", "dev"],
        "attributes": ["ServiceFlowDirection", 
            "ServiceFlowSchedulingType"],
    }),   
})
        
