#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nepi.core import description 
from nepi.core.attributes import Attribute
from nepi.util import validation

TESTBED_ID = "netns"

factories_metadata = dict({
    "v0.1" : metadata_v01
    })

def metadata_v01():
    return = dict({
             "node": dict({ #TODO: RoutingTable
                    "display_name": "Node",
                    "help": "Node element",
                    "category": "topology",
                    "connector_types": [
                        ("netns_node_apps", 
                            "Connector from node to applications", 
                            "apps", -1, 0,
                            ["netns_application_node"]),
                        ("netns_node_devs", 
                            "Connector from node to network interfaces", 
                            "devs", -1, 0,
                            [   
                                "netns_nodeiface_node", 
                                "netns_tapiface_node", 
                                "netns_p2piface_node"
                            ])
                        ],
                    "element_attributes": [
                        ("forward_X11", 
                            "Forward x11 from main namespace to the node", 
                            Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool)
                        ]
                }),
            "p2piface": dict({ #TODO: Addresses!
                    "display_name": "P2PInterface",
                    "help": "Point to point network interface",
                    "category": "devices",
                    "connector_types": [
                            ("netns_p2piface_node", 
                                "Connector from P2PInterface to Node", 
                                "node", 1, 1, 
                                ["netns_node_devs"]),
                            ("netns_p2pinterface_p2p", 
                                "Connector to another P2PInterface", 
                                "p2p", 1, 0, 
                                ["netns_p2piface_p2p"])
                        ],
                    "element_attributes": [
                        ("lladdr", "Mac address", Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_mac_address),
                        ("up", "Link up", Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool),
                        ("name", "Device name", Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_string),
                        ("mtu", "Maximmum transmition unit for device", 
                            Attribute.INTEGER,
                            None, None, None, False, 
                            validation.is_integer),
                        ("broadcast", "Broadcast address", 
                            Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_string),
                        ("multicast", "Is multicast enabled", 
                            Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool),
                        ("arp", "Is ARP enabled", Attribute.BOOL, 
                            True, None, None, False, 
                            validation.is_bool),
                    ]
                }),
                "tapiface": dict({ #TODO: Addresses!
                    "display_name": "TapNodeInterface",
                    "help": "Tap device network interface",
                    "category": "devices",
                    "connector_types": [
                        ("netns_tapiface_node", 
                            "Connector to a Node", 
                            "node", 1, 1, 
                            ["netns_node_devs"]),
                       ("netns_tapiface_fd", 
                           "Connector to a network interface that can receive a file descriptor", 
                           "fd", 1, 0, 
                            # TODO: Doesn't exist yet!
                           ["ns3_fdnetdev_fd"])
                       ],
                    "element_attributes": [
                        ("lladdr", "Mac address", Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_mac_address),
                        ("up", "Link up", Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool),
                        ("name", "Device name", Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_string),
                        ("mtu", "Maximmum transmition unit for device", 
                            Attribute.INTEGER, 
                            None, None, None, False, 
                            validation.is_integer),
                        ("broadcast", "Broadcast address", 
                            Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_string),
                        ("multicast", "Is multicast enabled", 
                            Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool),
                        ("arp", "Is ARP enabled", Attribute.BOOL, 
                            True, None, None, False, 
                            validation.is_bool),
                    ]
                }),
            "nodeiface": dict({ #TODO: Addresses!
                    "display_name": "NodeInterface",
                    "help": "Node network interface",
                    "category": "devices",
                    "connector_types": [
                        ("netns_nodeiface_node", "Connector to a node",
                            "node", 1, 1, 
                            ["netns_node_devs"]),
                        ("netns_nodeiface_switch", "Connector to a switch", 
                            "switch", 1, 0,
                            ["netns_switch_devs"])
                        ],
                    "element_attributes": [
                        ("lladdr", "Mac address", Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_mac_address),
                        ("up", "Link up", Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool),
                        ("name", "Device name", Attribute.STRING, 
                            None, None, None, False, 
                            validation.is_string),
                        ("mtu", "Maximmum transmition unit for device", 
                            Attribute.INTEGER, 
                            None, None, None, False, 
                            validation.is_integer),
                        ("broadcast", "Broadcast address", 
                            Attribute.STRING,
                            None, None, None, False, 
                            validation.is_string),
                        ("multicast", "Is multicast enabled", 
                            Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool),
                        ("arp", "Is ARP enabled", Attribute.BOOL, 
                            True, None, None, False, 
                            validation.is_bool),
                    ]
                }),
            "switch": dict({
                    "display_name": "Switch",
                    "help": "Switch interface",
                    "category": "devices",
                    "connector_types": [
                        ("netns_switch_devs", "Connector to network interfaces", 
                            "devs", -1, 0, 
                            ["netns_nodeiface_switch"])
                        ],
                    "element_attributes": [
                        ("Up", "Link up", Attribute.BOOL, 
                            False, None, None, False,
                            validation.is_bool),
                        ("Name", "Device name", Attribute.STRING, 
                            None, None, None, False,
                            validation,is_string),
                        ("Mtu", "Maximmum transmition unit for device", 
                            Attribute.INTEGER, 
                            None, None, None, False,
                            validation.is_integer),
                        ("Multicast", "Is multicast enabled", 
                            Attribute.BOOL,
                            None, None, None, False, 
                            validation.is_bool),
                        #TODO:("Stp", help, type, value, range, allowed, readonly, validation_function),
                        #TODO:("ForwarddDelay", help, type, value, range, allowed, readonly, validation_function),
                        #TODO:("HelloTime", help, type, value, range, allowed, readonly, validation_function),
                        #TODO:("AgeingTime", help, type, value, range, allowed, readonly, validation_function),
                        #TODO:("MaxAge", help, type, value, range, allowed, readonly, validation_function)
                        ]
                }),
                "application": dict({
                    "display_name": "Application",
                    "help": "Generic executable command line application",
                    "category": "applications",
                    "connector_types": [
                            ("netns_application_node", "Connector to a node",
                                "node", 1, 1, 
                                ["netns_node_apps"])
                        ],
                    "traces": [
                            ("StdoutTrace", "Standard output"),
                            ("StderrTrace", "Standard error")
                        ],
                    "element_attributes": [
                        ("Command", "Command line",
                            Attribute.STRING,
                            None, None, None, False,
                            validation.is_string)
                        ("User", "System user", 
                            Attribute.STRING, 
                            None, None, None, False,
                            validation.is_string)
                        ("Stdin", "Standard input", 
                            Attribute.STRING,
                            None, None, None, False,
                            validation.is_string)
                        ]
                }),

        })

def create_factories(version):
    factories = list()
    metadata = factories_metadata[version]()
    
    for factory_id, info in metadata.iteritems():
        help = info["help"]
        category = info["category"]
        display_name = info["display_name"]
        factory = Factory(factory_id, display_name, help, category)

        for (connector_type_id, help, name, max, min, 
                allowed_connector_type_ids) in info["connector_types"]:
            factory.add_connector_type(connector_type_id, help, name, max,
                    min, allowed_connector_type_ids)
        for :
            factory.add_trace(name, help)
        for :
            factory.add_attribute(name, help, type, value, range, allowed,
                    readonly, validation_function)
         for :
            factory.add_element_attribute(name, help, type, value, range,
                    allowed, readonly, validation_function)
        factories.append(factory)
    return factories

def create_provider(version):
    provider = description.FactoriesProvider()
    for factory in create_factories(version):
        provider.add_factory(factory)
    return provider

def create_description_instance(guid_generator, version, provider):
    return description.TestbedDescription(guid_generator, TESTBED_ID, version, provider)


