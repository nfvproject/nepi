
from nepi.design import attributes, connectors, tags
from nepi.design.boxes import TestbedBox, Box, IPAddressBox, IPAddressCapableBox, \
        RouteEntryBox, RouteEntryCapableBox, ContainerBox, TunnelBox
 
TESTBED_ID = "netns01"

EMULATION = "netns::Emulation"
NODE = "netns::Node"
P2PIFACE = "netns::P2PNodeInterface"
TAPIFACE = "netns::TapNodeInterface"
TUNIFACE = "netns::TunNodeInterface"
NODEIFACE = "netns::NodeInterface"
SWITCH = "netns::Switch"
APPLICATION = "netns::Application"
TUNCHANNEL = "netns::TunChannel"
CONTAINER = "netns::Container"
PCAPTRACE = "netns::PcapTrace"
OUTTRACE = "netns::StdoutTrace"
ERRTRACE = "netns::StderrTrace"
ROUTE = "netns::RouteEntry"
IP4ADDRESS = "netns::IP4Address"

boxes = list()


############ CONTROLLER #############

box = TestbedBox(TESTBED_ID, EMULATION, help = "NETNS emulation instance.")
boxes.append(box)
box.add_attr(
    attributes.BoolAttribute(
        "enableDebug", 
        "Enable netns debug output", 
        default_value = False,
        )
    )


############ CONTAINER #############

box = ContainerBox(TESTBED_ID, CONTAINER, help = "Container for grouping NETNS box configurations.")
boxes.append(box)
box.add_container_info(TESTBED_ID, tags.CONTROLLER)


############ ADDRESS #############

box = IPAddressBox(TESTBED_ID, IP4ADDRESS, help = "IP Address box.")
boxes.append(box)

conn = connectors.Connector("iface", "Connector from address to interface", max = 1, min = 1)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", P2PIFACE, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", NODEIFACE, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", TAPIFACE, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(IP4ADDRESS, "iface", TUNIFACE, "addrs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

box.add_tag(tags.ADDRESS)


############ ROUTE ENTRY #############

box = RouteEntryBox(TESTBED_ID, ROUTE, help = "Route entry box.")
boxes.append(box)

conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = connectors.ConnectionRule(ROUTE, "node", NODE, "routes", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)


############ NODE #############

box = RouteEntryCapableBox(TESTBED_ID, NODE, ROUTE, "node",
        help = "Emulated Node with virtualized network stack")
boxes.append(box)

box.add_attr(
        attributes.BoolAttribute(
            "forwardX11", 
            "Forward x11 from main namespace to the node",
            default_value = False,
            flags = attributes.AttributeFlags.ExecReadOnly | 
                    attributes.AttributeFlags.ExecImmutable
            )
        )

## CONNECTORS
conn = connectors.Connector("ifaces", "Connector from netns::Node to netns intefaces", max = -1, min = 0)
rule = connectors.ConnectionRule(NODE, "ifaces", P2PIFACE, "node", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(NODE, "ifaces", NODEIFACE, "node", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(NODE, "ifaces", TAPIFACE, "node", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(NODE, "ifaces", TUNIFACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("apps", "Connector from netns::Node to netns::Application", max = -1, min = 0)
rule = connectors.ConnectionRule(NODE, "apps", APPLICATION, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("traces", "Connector from netns::Node to netns::PcapTrace", max = -1, min = 0)
rule = connectors.ConnectionRule(NODE, "traces", PCAPTRACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

## TAGS
box.add_tag(tags.NODE)


############ INTERFACES #############

class IfaceBox(IPAddressCapableBox):
    def __init__(self, testbed_id, box_id, address_box_id, address_connector,
            provider = None, guid = None, help = None):
        super(IfaceBox, self).__init__(testbed_id, box_id, address_box_id, 
                address_connector, provider, guid, help)
        
        self.add_tag(tags.INTERFACE)
        
        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", "Connector to netns::Node", max = 1, min = 1)
        rule = connectors.ConnectionRule(self.box_id, "node", NODE, "ifaces", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
            attributes.MacAddressAttribute(
                    "lladdr", 
                    "Mac address", 
                    flags = attributes.AttributeFlags.ExecReadOnly | 
                            attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                    "up", 
                    "Link up",
                    default_value = False
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                    "name", 
                    "Device Name", 
                    flags = attributes.AttributeFlags.ExecReadOnly | 
                            attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.IntegerAttribute(
                    "mtu", 
                    "Maximum transmition unit for device"
                )
            )

        self.add_attr(
            attributes.IPv4Attribute(
                    "broadcast", 
                    "BroadcastAddress"
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                    "multicast", 
                    "Multicast enabled",
                    default_value = False
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                    "arp", 
                    "ARP enabled",
                    default_value = False
                )
            )


############ P2PIFACE #############

box = IfaceBox(TESTBED_ID, P2PIFACE, IP4ADDRESS, "iface",
        help = "Point to point network interface")
boxes.append(box)

## CONNECTORS
conn = connectors.Connector("p2p", "Connector to netns::P2PInterface", max = 1, min = 1)
rule = connectors.ConnectionRule(P2PIFACE, "p2p", P2PIFACE, "p2p", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ NODEIFACE #############

box = IfaceBox(TESTBED_ID, NODEIFACE, IP4ADDRESS, "iface",
        help = "Node network interface")
boxes.append(box)

## CONNECTORS
conn = connectors.Connector("switch", "Connector to netns::Switch", max = 1, min = 1)
rule = connectors.ConnectionRule(NODEIFACE, "switch", SWITCH, "ifaces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ TAPIFACE #############

box = IfaceBox(TESTBED_ID, TAPIFACE, IP4ADDRESS, "iface",
        help = "TAP device network interface")
boxes.append(box)

## CONNECTORS
conn = connectors.Connector("fd->", "File descriptor provider for devices with file descriptors", max = 1, min = 0)
rule = connectors.ConnectionRule(TAPIFACE, "fd->", None, "->fd", True)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ TUNIFACE #############

box = IfaceBox(TESTBED_ID, TUNIFACE, IP4ADDRESS, "iface",
        help = "TUN device network interface")
boxes.append(box)

## CONNECTORS
conn = connectors.Connector("fd->", "File descriptor provider for devices with file descriptors", max = 1, min = 0)
rule = connectors.ConnectionRule(TUNIFACE, "fd->", None, "->fd", True)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ SWITCH #############

box = Box(TESTBED_ID, SWITCH, help = "Switch interface")
boxes.append(box)
box.add_attr(
    attributes.MacAddressAttribute(
        "lladdr", 
        "Mac address", 
        flags = attributes.AttributeFlags.ExecReadOnly | 
                attributes.AttributeFlags.ExecImmutable
    )
)
box.add_attr(
    attributes.BoolAttribute(
        "up", 
        "Link up",
        default_value = False
    )
)
box.add_attr(
    attributes.StringAttribute(
        "name", 
        "Device Name", 
        flags = attributes.AttributeFlags.ExecReadOnly | 
                attributes.AttributeFlags.ExecImmutable
    )
)
box.add_attr(
    attributes.IntegerAttribute(
        "mtu", 
        "Maximum transmition unit for device"
    )
)

## CONNECTORS
conn = connectors.Connector("ifaces", "Connector from netns::Node to netns intefaces", max = -1, min = 0)
rule = connectors.ConnectionRule(SWITCH, "ifaces", NODEIFACE, "switch", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

## TAGS
box.add_tag(tags.SWITCH)


############ APPLICATION #############

box = Box(TESTBED_ID, APPLICATION, help = "Generic executable command line application")
boxes.append(box)

box.add_attr(
    attributes.StringAttribute(
        "command", 
        "Command line string",
        flags = attributes.AttributeFlags.ExecReadOnly | 
                attributes.AttributeFlags.ExecImmutable
    )
)

box.add_attr(
    attributes.StringAttribute(
        "user", 
        "System user",
        flags = attributes.AttributeFlags.ExecReadOnly | 
                attributes.AttributeFlags.ExecImmutable
    )
)

## CONNECTORS
conn = connectors.Connector("node", "Connector from netns::Application to netns::Node", max = -1, min = 0)
rule = connectors.ConnectionRule(APPLICATION, "node", NODE, "apps", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("traces", "Connector from netns::Application to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(APPLICATION, "traces", OUTTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
rule = connectors.ConnectionRule(APPLICATION, "traces", ERRTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

## TAGS
box.add_tag(tags.APPLICATION)


############ TUNCHANNEL #############

box = TunnelBox(TESTBED_ID, TUNCHANNEL, 
        help = "Channel to forward netns::TapInterface data to other TAP interfaces supporting the NEPI tunneling protocol.")
boxes.append(box)

## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)


############ PCAPTRACE #############

box = Box(TESTBED_ID, PCAPTRACE, help = "Trace to generate tcpdump on a node")
boxes.append(box)

conn = connectors.Connector("node", "Connector from netns::PcapTrace to netns::PcapTrace", max = 1, min = 0)
rule = connectors.ConnectionRule(PCAPTRACE, "node", NODE, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

box.add_tag(tags.TRACE)


############ ERRTRACE #############

box = Box(TESTBED_ID, ERRTRACE, help = "Trace to capture errors from applications")
boxes.append(box)

conn = connectors.Connector("app", "Connector from netns::ErrTrace to netns::Application", max = 1, min = 0)
rule = connectors.ConnectionRule(ERRTRACE, "app", APPLICATION, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

box.add_tag(tags.TRACE)


############ OUTTRACE #############

box = Box(TESTBED_ID, OUTTRACE, help = "Trace to capture output from applications")
boxes.append(box)

conn = connectors.Connector("app", "Connector from netns::OutTrace to netns::Application", max = 1, min = 0)
rule = connectors.ConnectionRule(OUTTRACE, "app", APPLICATION, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

box.add_tag(tags.TRACE)


