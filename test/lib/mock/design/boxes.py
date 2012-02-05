# -*- coding: utf-8 -*-

from nepi.design import attributes, tags
from nepi.design.boxes import TestbedBox, Box, IPAddressBox
from nepi.design.connectors import Connector, ConnectionRule

TESTBED_ID = "mock"

TESTBED = "mock::MockInstance"
NODE = "mock::Node"
IFACE = "mock::Interface"
APP = "mock::Application"
TRACE = "mock::Trace"
ADDRESS = "mock::IPv4Address"

boxes = list()

# CONTROLLER
box = TestbedBox(TESTBED_ID, TESTBED, None, None)
boxes.append(box)


# NODE
box = Box(TESTBED_ID, NODE, None, None)
boxes.append(box)
## CONNECTORS
conn = Connector("devs", "Connector from node to intefaces", max = -1, min = 0)
rule = ConnectionRule(NODE, "devs", IFACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("apps", "Connector from node to applications", max = -1, min = 0)
rule = ConnectionRule(NODE, "apps", APP, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("traces", "Connector from node to traces", max = -1, min = 0)
rule = ConnectionRule(NODE, "traces", TRACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container(TESTBED)
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
box = Box(TESTBED_ID, IFACE, None, None)
boxes.append(box)
## Connector
conn = Connector("node", "Connector from interface to node", max = 1, min = 1)
rule = ConnectionRule(IFACE, "node", NODE, "devs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("addrs", "Connector from interface to addresses", max = -1, min = 1)
rule = ConnectionRule(IFACE, "addrs", ADDRESS, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = Connector("peer", "Connector from interface to interface", max = 1, min = 1)
rule = ConnectionRule(IFACE, "peer", IFACE, "peer", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container(TESTBED)
## TAGS
box.add_tag(tags.INTERFACE)


# APPLICATION
box = Box(TESTBED_ID, APP, None, None)
boxes.append(box)
## Connector
conn = Connector("node", "Connector from application to node", max = 1, min = 1)
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
box.add_container(TESTBED)
## TAGS
box.add_tag(tags.APPLICATION)


# TRACE
box = Box(TESTBED_ID, TRACE, None, None)
boxes.append(box)
## Connector
conn = Connector("node", "Connector from trace to node", max = 1, min = 1)
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
box.add_container(TESTBED)
## TAGS
box.add_tag(tags.TRACE)


# ADDRESS
box = IPAddressBox(TESTBED_ID, ADDRESS, None, None)
boxes.append(box)
## Connector
conn = Connector("iface", "Connector from address to interface", max = 1, min = 1)
rule = ConnectionRule(ADDRESS, "iface", IFACE, "addrs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)
## CONTAINER BOX ID
box.add_container(TESTBED)
## TAGS
box.add_tag(tags.ADDRESS)

