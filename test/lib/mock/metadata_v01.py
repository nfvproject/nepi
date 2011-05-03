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

def connect_cross(testbed_instance, guid, cross_data):
    connected = True
    testbed_instance.set(guid, "cross", True)

### Creation functions ###

def create_node(testbed_instance, guid):
    testbed_instance.elements[guid] = NODE

def create_iface(testbed_instance, guid):
     testbed_instance.elements[guid] = IFACE

def create_application(testbed_instance, guid):
     testbed_instance.elements[guid] = APP

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
    "cross": dict({
                "help": "Connector to an Interface in other testbed", 
                "name": "cross",
                "max": 1, 
                "min": 0
            }),
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, IFACE, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, IFACE, "iface"),
        "to":   (TESTBED_ID, IFACE, "iface"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APP, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, IFACE, "cross"),
        "to":   ("mock2", IFACE, "cross"),
        "init_code": connect_cross,
        "can_cross": True,
    })]

attributes = dict({
    "fake": dict({
                "name": "fake",
                "help": "fake attribute",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "test": dict({
                "name": "test",
                "help": "test attribute",
                "type": Attribute.STRING,
                "validation_function": validation.is_string
            }),
    "cross": dict({
                "name": "cross",
                "help": "Attribute that indicates if cross connection was performed",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
        })
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
            "box_attributes": ["fake","test"],
            "connector_types": ["devs", "apps"]
       }),
    IFACE: dict({
            "help": "Fake iface",
            "category": "devices",
            "create_function": create_iface,
            "start_function": None,
            "stop_function": None,
            "status_function": None,
            "allow_addresses": True,
            "factory_attributes": ["fake"],
            "box_attributes": ["fake", "test", "cross"],
            "connector_types": ["node", "iface", "cross"]
       }),
    APP: dict({
            "help": "Fake application",
            "category": "applications",
            "create_function": create_application,
            "start_function": None,
            "stop_function": None,
            "status_function": status_application,
            "box_attributes": ["fake", "test"],
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
        "test": dict({
                "name": "test",
                "help": "test attribute",
                "type": Attribute.STRING,
                "validation_function": validation.is_string
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
    def create_order(self):
        return factories_order

    @property
    def configure_order(self):
        return factories_order

    @property
    def factories_info(self):
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

