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

