# -*- coding: utf-8 -*-

from nepi.design import attributes, tags
from nepi.design.boxes import TestbedBoxFactory, BoxFactory, IPAddressBoxFactory
from nepi.design.connectors import Connector, ConnectionRule

TESTBED_ID = "mock"

TESTBED = "mock::MockInstance"
NODE = "mock::Node"
IFACE = "mock::Interface"
APP = "mock::Application"
TRACE = "mock::Trace"
ADDRESS = "mock::IPv4Address"


factories = list()


# CONTROLLER
factory = TestbedBoxFactory(TESTBED_ID, TESTBED)
factories.append(factory)


# NODE
factory = BoxFactory(TESTBED_ID, NODE)
factories.append(factory)
## CONNECTORS
conn = Connector(NODE, "devs", "Connector from node to intefaces", max = -1, min = 0)
rule = ConnectionRule(NODE, "devs", IFACE, "node", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)

conn = Connector(NODE, "apps", "Connector from node to applications", max = -1, min = 0)
rule = ConnectionRule(NODE, "apps", APP, "node", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)

conn = Connector(NODE, "traces", "Connector from node to traces", max = -1, min = 0)
rule = ConnectionRule(NODE, "traces", TRACE, "node", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)
## CONTAINER BOX ID
factory.add_container_box_id(TESTBED)
## ATTRIBUTES INFO
factory.add_attr(
        attributes.BoolAttribute(
            "boolAttr", 
            "Test bool attr", 
            default_value = False,
            )
        )
## TAGS
factory.add_tag(tags.NODE)


#IFACE
factory = BoxFactory(TESTBED_ID, IFACE)
factories.append(factory)
## Connector
conn = Connector(IFACE, "node", "Connector from interface to node", max = 1, min = 1)
rule = ConnectionRule(IFACE, "node", NODE, "devs", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)

conn = Connector(IFACE, "addrs", "Connector from interface to addresses", max = -1, min = 1)
rule = ConnectionRule(IFACE, "addrs", ADDRESS, "iface", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)

conn = Connector(IFACE, "peer", "Connector from interface to interface", max = 1, min = 1)
rule = ConnectionRule(IFACE, "peer", IFACE, "peer", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)
## CONTAINER BOX ID
factory.add_container_box_id(TESTBED)
## TAGS
factory.add_tag(tags.INTERFACE)


# APPLICATION
factory = BoxFactory(TESTBED_ID, APP)
factories.append(factory)
## Connector
conn = Connector(APP, "node", "Connector from application to node", max = 1, min = 1)
rule = ConnectionRule(APP, "node", NODE, "apps", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)
## ATTRIBUTES INFO
factory.add_attr(
        attributes.TimeAttribute(
            "start", 
            "Test start attr", 
            default_value = "0s",
            )
        )
## CONTAINER BOX ID
factory.add_container_box_id(TESTBED)
## TAGS
factory.add_tag(tags.APPLICATION)


# TRACE
factory = BoxFactory(TESTBED_ID, TRACE)
factories.append(factory)
## Connector
conn = Connector(TRACE, "node", "Connector from trace to node", max = 1, min = 1)
rule = ConnectionRule(TRACE, "node", NODE, "traces", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)
## ATTRIBUTES INFO
factory.add_attr(
        attributes.StringAttribute(
            "stringAttr", 
            "Test string attr", 
            default_value = "empty",
            )
        )
## CONTAINER BOX ID
factory.add_container_box_id(TESTBED)
## TAGS
factory.add_tag(tags.TRACE)


# ADDRESS
factory = IPAddressBoxFactory(TESTBED_ID, ADDRESS)
factories.append(factory)
## Connector
conn = Connector(ADDRESS, "iface", "Connector from address to interface", max = 1, min = 1)
rule = ConnectionRule(ADDRESS, "iface", IFACE, "addrs", False)
conn.add_connection_rule(rule)
factory.add_connector(conn)
## CONTAINER BOX ID
factory.add_container_box_id(TESTBED)
## TAGS
factory.add_tag(tags.ADDRESS)

