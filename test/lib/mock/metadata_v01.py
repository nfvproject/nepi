#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
from nepi.util.constants import STATUS_FINISHED

NODE = "Node"
IFACE = "Interface"
APP = "Application"

### Connection functions ####

### Creation functions ###

def create_node(testbed_instance, guid):
    element = NODE 
    testbed_instance.elements[guid] = element

def create_iface(testbed_instance, guid):
     element = IFACE
     testbed_instance.elements[guid] = element

def create_application(testbed_instance, guid):
     element = APP
     testbed_instance.elements[guid] = element

### Start/Stop functions ###

### Status functions ###

def status_application(testbed_instance, guid):
    return STATUS_FINISHED

### Factory information ###

connector_types = dict({
    "apps": dict({
                "help": "Connector from node to applications", 
                "name": "apps",
                "max": -1, 
                "min": 0
            }),
    "devs": dict({
                "help": "Connector from node to network interfaces", 
                "name": "devs",
                "max": -1, 
                "min": 0
            }),
    "node": dict({
                "help": "Connector to a Node", 
                "name": "node",
                "max": 1, 
                "min": 1
            }),
    "iface": dict({
                "help": "Connector to a Interface", 
                "name": "iface",
                "max": 1, 
                "min": 0
            }),
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, IFACE, "node"),
        "code": None,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, IFACE, "iface"),
        "to":   (TESTBED_ID, IFACE, "iface"),
        "code": None,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APP, "node"),
        "code": None,
        "can_cross": False
    })
]

attributes = dict({
    "fake": dict({
                "name": "fake",
                "help": "fake attribute",
                "type": Attribute.BOOL,
                "value": False,
                "range": None,
                "allowed": None,
                "validation_function": validation.is_bool
            }),
    })

traces = dict({
    "fake": dict({
                "name": "fake",
                "help": "fake trace"
              }),
    })

factories_order = [ NODE, IFACE, APP ]

factories_info = dict({
    NODE: dict({
            "help": "Fake node",
            "category": "topology",
            "create_function": create_node,
            "start_function": None,
            "stop_function": None,
            "status_function": None,
            "box_attributes": ["fake"],
            "connector_types": ["devs", "apps"]
       }),
    IFACE: dict({
            "help": "Fake iface",
            "category": "devices",
            "create_function": create_iface,
            "start_function": None,
            "stop_function": None,
            "status_function": None,
            "factory_attributes": ["fake"],
            "box_attributes": ["fake"],
            "connector_types": ["node", "iface"]
       }),
    APP: dict({
            "help": "Fake application",
            "category": "applications",
            "create_function": create_application,
            "start_function": None,
            "stop_function": None,
            "status_function": status_application,
            "box_attributes": ["fake"],
            "connector_types": ["node"],
            "traces": ["fake"]
        }),
})

testbed_attributes = dict({
        "fake": dict({
                "name": "fake",
                "help": "fake attribute",
                "type": Attribute.BOOL,
                "value": False,
                "range": None,
                "allowed": None,
                "validation_function": validation.is_bool
            }),
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
        return attributes

    @property
    def traces(self):
        return traces

    @property
    def factories_order(self):
        return factories_order

    @property
    def factories_info(self):
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

