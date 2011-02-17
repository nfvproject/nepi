#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.description import AF_INET
from nepi.core.attributes import Attribute
from nepi.util import validation

def get_metadata():
    return dict({
             "Node": dict({
                    "factory_type": "routing",
                    "display_name": "Node",
                    "help": "Node",
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
                    "box_attributes": [
                        ("forward_X11", 
                            "Forward x11 from main namespace to the node", 
                            Attribute.BOOL, 
                            False, None, None, False, 
                            validation.is_bool)
                        ]
                }),
            "P2PInterface": dict({
                    "factory_type": "addressable",
                    "family": AF_INET,
                    "max_addresses": 1,
                    "display_name": "P2PInterface",
                    "help": "Point to point network interface",
                    "category": "devices",
                    "connector_types": [
                            ("netns_p2piface_node", 
                                "Connector from P2PInterface to Node", 
                                "node", 1, 1, 
                                ["netns_node_devs"]),
                            ("netns_p2piface_p2p", 
                                "Connector to another P2PInterface", 
                                "p2p", 1, 0, 
                                ["netns_p2piface_p2p"])
                        ],
                    "box_attributes": [
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
                "TapNodeInterface": dict({
                    "factory_type": "addressable",
                    "family": AF_INET,
                    "max_addresses": 1,
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
                    "box_attributes": [
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
            "NodeInterface": dict({
                    "factory_type": "addressable",
                    "family": AF_INET,
                    "max_addresses": 1,
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
                    "box_attributes": [
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
            "Switch": dict({
                    "display_name": "Switch",
                    "help": "Switch interface",
                    "category": "devices",
                    "connector_types": [
                        ("netns_switch_devs", "Connector to network interfaces", 
                            "devs", -1, 0, 
                            ["netns_nodeiface_switch"])
                        ],
                    "box_attributes": [
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
                        ("multicast", "Is multicast enabled", 
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
               "Application": dict({
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
                    "box_attributes": [
                        ("command", "Command line",
                            Attribute.STRING,
                            None, None, None, False,
                            validation.is_string),
                        ("user", "System user", 
                            Attribute.STRING, 
                            None, None, None, False,
                            validation.is_string),
                        ("stdin", "Standard input", 
                            Attribute.STRING,
                            None, None, None, False,
                            validation.is_string)
                        ]
                }),
        })
