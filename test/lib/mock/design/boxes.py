
from nepi.design import attributes, tags
from nepi.design.boxes import TestbedBox, Box, IPAddressBox, IPAddressCapableBox, \
        RouteEntryBox, RouteEntryCapableBox, ContainerBox
from nepi.design.connectors import Connector, ConnectionRule

TESTBED_ID = "mock"

TESTBED = "mock::MockInstance"
NODE = "mock::Node"
IFACE = "mock::Interface"
APP = "mock::Application"
TRACE = "mock::Trace"
ADDRESS = "mock::IPv4Address"
ROUTE = "mock::RouteEntry"
CONTAINER = "mock::Container"

boxes = list()

# CONTROLLER
box = TestbedBox(TESTBED_ID, TESTBED)
boxes.append(box)

# CONTAINER
box = ContainerBox(TESTBED_ID, CONTAINER)
box.add_container_info(TESTBED_ID, tags.TC)
boxes.append(box)

# NODE
box = RouteEntryCapableBox(TESTBED_ID, NODE, ROUTE, "node")
boxes.append(box)
## CONNECTORS
conn = Connector("devs", "Connector to %s" % IFACE, max = -1, min = 0)
rule = ConnectionRule(NODE, "devs", IFACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("apps", "Connector to %s" % APP, max = -1, min = 0)
rule = ConnectionRule(NODE, "apps", APP, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("traces", "Connector to %s" % TRACE, max = -1, min = 0)
rule = ConnectionRule(NODE, "traces", TRACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.TC)
box.add_container_info(TESTBED_ID, tags.CONTAINER)
## ATTRIBUTES INFO
box.add_attr(
        attributes.BoolAttribute(
            "boolAttr", 
            "Test bool attr", 
            default_value = False,
            )
        )
## TAGS
box.add_tag(tags.NODE)


#IFACE
box = IPAddressCapableBox(TESTBED_ID, IFACE, ADDRESS, "iface")
boxes.append(box)
## Connector
conn = Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = ConnectionRule(IFACE, "node", NODE, "devs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("peer", "Connector from %s to %s" % (IFACE, IFACE), max = 1, min = 1)
rule = ConnectionRule(IFACE, "peer", IFACE, "peer", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.TC)
box.add_container_info(TESTBED_ID, tags.CONTAINER)
## TAGS
box.add_tag(tags.INTERFACE)


# APPLICATION
box = Box(TESTBED_ID, APP)
boxes.append(box)
## Connector
conn = Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = ConnectionRule(APP, "node", NODE, "apps", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## ATTRIBUTES INFO
box.add_attr(
        attributes.TimeAttribute(
            "start", 
            "Test start attr", 
            default_value = "0s",
            )
        )
## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.TC)
box.add_container_info(TESTBED_ID, tags.CONTAINER)
## TAGS
box.add_tag(tags.APPLICATION)


# TRACE
box = Box(TESTBED_ID, TRACE)
boxes.append(box)
## Connector
conn = Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = ConnectionRule(TRACE, "node", NODE, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## ATTRIBUTES INFO
box.add_attr(
        attributes.StringAttribute(
            "stringAttr", 
            "Test string attr", 
            default_value = "empty",
            )
        )
## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.TC)
box.add_container_info(TESTBED_ID, tags.CONTAINER)
## TAGS
box.add_tag(tags.TRACE)


# ADDRESS
box = IPAddressBox(TESTBED_ID, ADDRESS)
boxes.append(box)
## Connector
conn = Connector("iface", "Connector to %s" % IFACE, max = 1, min = 1)
rule = ConnectionRule(ADDRESS, "iface", IFACE, "addrs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.TC)
box.add_container_info(TESTBED_ID, tags.CONTAINER)
## TAGS
box.add_tag(tags.ADDRESS)


# ROUTE
box = RouteEntryBox(TESTBED_ID, ROUTE)
boxes.append(box)
## Connector
conn = Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = ConnectionRule(ROUTE, "node", NODE, "routes", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container_info(TESTBED_ID, tags.TC)
box.add_container_info(TESTBED_ID, tags.CONTAINER)
## TAGS
box.add_tag(tags.ROUTE)

