# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import tags, validation
from nepi.util.constants import ApplicationStatus as AS, \
        FactoryCategories as FC, DeploymentConfiguration as DC

# Factories
NODE = "Node"
WIFIIFACE = "WifiInterface"
ETHIFACE = "EthInterface"
CHANNEL = "Channel"
APPLICATION = "Application"

### Connection functions ####

### Creation functions ###

def create_node(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    hostname = parameters['hostname']
    testbed_instance._elements[guid] = hostname
    testbed_instance._publish_and_enroll_host(hostname)

def create_wifiiface(testbed_instance, guid):
    pass

def create_ethiface(testbed_instance, guid):
    pass

def create_channel(testbed_instance, guid):
    pass

def create_application(testbed_instance, guid):
    pass

### Start/Stop functions ###

def start_application(testbed_instance, guid):
    # search for the node asociated with the device
    node_guids = testbed_instance.get_connected(guid, "node", "apps")
    if len(node_guids) == 0:
        raise RuntimeError("Can't instantiate interface %d outside node" % guid)

    # node attributes
    node_parameters = testbed_instance._get_parameters(node_guids[0])
    hostname = node_parameters['hostname']

    # application attributes
    parameters = testbed_instance._get_parameters(guid)
    app_id = parameters.get("appId")
    arguments = parameters.get("arguments")
    path = parameters.get("path")
    testbed_instance._publish_execute(hostname, app_id, arguments, path)

def stop_application(testbed_instance, guid):
    pass

### Status functions ###

def status_application(testbed_instance, guid):
    if guid not in testbed_instance.elements.keys():
        return AS.STATUS_NOT_STARTED
    return AS.STATUS_RUNNING
    # TODO!!!!
    #return AS.STATUS_FINISHED

### Configure functions ###

def configure_wifiiface(testbed_instance, guid):
    # search for the node asociated with the device
    node_guids = testbed_instance.get_connected(guid, "node", "devs")
    if len(node_guids) == 0:
        raise RuntimeError("Can't instantiate interface %d outside node" % guid)

    # node attributes
    node_parameters = testbed_instance._get_parameters(node_guids[0])
    hostname = node_parameters['hostname']

    # wifi iface attributes
    parameters = testbed_instance._get_parameters(guid)

    for attr in ["mode", "type", "channel", "essid"]: 
        attribute = "net/w0/%s" % attr
        value = parameters.get(attr)
        if value:
            testbed_instance._publish_configure(hostname, attribute, value)

    if guid in testbed_instance._add_address: 
        attribute = "net/w0/ip"
        addresses = testbed_instance._add_address[guid]
        (value, netprefix, broadcast) = addresses[0]
        testbed_instance._publish_configure(hostname, attribute, value)

### Factory information ###

connector_types = dict({
    "apps": dict({
                "help": "Connector from node to applications", 
                "name": "apps",
                "max": -1, 
                "min": 0
            }),
    "devs": dict({
                "help": "Connector to network interfaces", 
                "name": "devs",
                "max": -1, 
                "min": 0
            }),
    "chan": dict({
                "help": "Connector from a device to a channel", 
                "name": "chan",
                "max": 1, 
                "min": 1
            }),
    "node": dict({
                "help": "Connector to a Node", 
                "name": "node",
                "max": 1, 
                "min": 1
            }),
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, WIFIIFACE, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, ETHIFACE, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, WIFIIFACE, "chan"),
        "to":   (TESTBED_ID, CHANNEL, "devs"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APPLICATION, "node"),
        "can_cross": False
    }),
 ]

attributes = dict({
    "appId": dict({
                "name": "appId",
                "help": "Application id",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "arguments": dict({
                "name": "arguments",
                "help": "Application arguments",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "path": dict({
                "name": "path",
                "help": "Path to binary (e.g '/opt/vlc-1.1.13/vlc')",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "hostname": dict({
                "name": "hostname",
                "help": "Hostname for the target OMF node",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "mode": dict({
                "name": "mode",
                "help": "Corresponds to the OMF attributes net/w0/mode",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "type": dict({
                "name": "type",
                "help": "Corresponds to the OMF attributes net/w0/type",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "channel": dict({
                "name": "channel",
                "help": "Corresponds to the OMF attributes net/w0/channel",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "essid": dict({
                "name": "essid",
                "help": "Corresponds to the OMF attributes net/w0/essid",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),


    })

traces = dict()

create_order = [ NODE, WIFIIFACE, ETHIFACE, CHANNEL, APPLICATION ]
configure_order = [ WIFIIFACE, ETHIFACE, NODE, CHANNEL, APPLICATION ]

factories_info = dict({
    NODE: dict({
            "help": "OMF Node",
            "category": FC.CATEGORY_NODES,
            "create_function": create_node,
            "box_attributes": ["hostname"],
            "connector_types": ["devs", "apps"],
            "tags": [tags.NODE, tags.ALLOW_ROUTES],
       }),
    WIFIIFACE: dict({
            "help": "Wireless network interface",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create_wifiiface,
            "configure_function": configure_wifiiface,
            "box_attributes": ["mode", "type", "channel", "essid"],
            "connector_types": ["node", "chan"],
            "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
       }),
    ETHIFACE: dict({
            "help": "Ethernet network interface",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create_ethiface,
            #"box_attributes": [""],
            "connector_types": ["node"],
            "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
       }),
    CHANNEL: dict({
            "help": "Wireless channel",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create_channel,
            "box_attributes": ["mode", "type", "channel", "essid"],
            "connector_types": ["devs"],
       }),
    APPLICATION: dict({
            "help": "Generic executable command line application",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_application,
            "start_function": start_application,
            "stop_function": stop_application,
            "status_function": status_application,
            "box_attributes": ["appId", "arguments", "path"],
            "connector_types": ["node"],
            "tags": [tags.APPLICATION],
        }),
})

testbed_attributes = dict({
    "enable_debug": dict({
            "name": "enableDebug",
            "help": "Enable netns debug output",
            "type": Attribute.BOOL,
            "value": False,
            "validation_function": validation.is_bool
        }),
    "xmppSlice": dict({
                "name": "xmppSlice",
                "help": "OMF slice",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "xmppHost": dict({
                "name": "xmppHost",
                "help": "OMF XMPP server host",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "xmppPort": dict({
                "name": "xmppPort",
                "help": "OMF XMPP service port",
                "type": Attribute.INTEGER,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_integer
            }),
    "xmppPassword": dict({
                "name": "xmppPassword",
                "help": "OMF XMPP slice password",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    })

supported_recovery_policies = [
        DC.POLICY_FAIL,
    ]

class MetadataInfo(metadata.MetadataInfo):
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
        return create_order

    @property
    def configure_order(self):
        return configure_order

    @property
    def factories_info(self):
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

    @property
    def testbed_id(self):
        return TESTBED_ID

    @property
    def testbed_version(self):
        return TESTBED_VERSION
    
    @property
    def supported_recover_policies(self):
        return supported_recovery_policies

