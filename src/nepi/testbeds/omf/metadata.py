# -*- coding: utf-8 -*-

import functools
import weakref

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import tags, validation
from nepi.util.constants import ApplicationStatus as AS, \
        FactoryCategories as FC, DeploymentConfiguration as DC

##############################################################################

class OmfResource(object):
    def __init__(self, guid, tc):
        super(OmfResource, self).__init__()
        self._tc = weakref.ref(tc)
        self._guid = guid

    @property
    def tc(self):
        return self._tc and self._tc()

    def configure(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def status(self):
        pass

    def shutdown(self):
        pass

## NODE #######################################################################

class OmfNode(OmfResource):
    def __init__(self, guid, tc):
        super(OmfNode, self).__init__(guid, tc)
        self.hostname = self.tc._get_parameters(guid)['hostname']
        self.tc.api.enroll_host(self.hostname)

## APPLICATION ################################################################

class OmfApplication(OmfResource):
    def __init__(self, guid, tc):
        super(OmfApplication, self).__init__(guid, tc)
        node_guids = tc.get_connected(guid, "node", "apps")
        if len(node_guids) == 0:
            raise RuntimeError("Can't instantiate interface %d outside node" % guid)

        self._node_guid = node_guids[0] 
        self.app_id = None
        self.arguments = None
        self.path = None

    def start(self):
        node = self.tc.elements.get(self._node_guid)
        self.tc.api.execute(node.hostname, 
                self.appId, 
                self.arguments, 
                self.path)

    def status(self):
        if guid not in testbed_instance.elements.keys():
            return AS.STATUS_NOT_STARTED
        return AS.STATUS_RUNNING
        # TODO!!!!
        #return AS.STATUS_FINISHED


## WIFIIFACE ########################################################

class OmfWifiInterface(OmfResource):
    def __init__(self, guid, tc):
        super(OmfWifiInterface, self).__init__(guid, tc)
        node_guids = tc.get_connected(guid, "node", "devs")
        if len(node_guids) == 0:
            raise RuntimeError("Can't instantiate interface %d outside node" % guid)

        self._node_guid = node_guids[0] 
        self.mode = None
        self.type = None
        self.essid = None
        self.channel = None
        self.ip = None

    def __setattr__(self, name, value):
        if name in ["ip", "mode", "type", "essid", "channel"]:
            node = self.tc.elements.get(self._node_guid)    
            attribute = "net/w0/%s" % name
            self._tc().api.configure(node.hostname, attribute, value)
        else:
            super(OmfWifiInterface, self).__setattr__(name, value)

# Factories
NODE = "Node"
WIFIIFACE = "WifiInterface"
CHANNEL = "Channel"
OMFAPPLICATION = "OmfApplication"

def create(factory, testbed_instance, guid):
    clazz = OmfResource
    if factory == NODE:
        clazz = OmfNode
    elif factory == OMFAPPLICATION:
        clazz = OmfApplication
    elif factory == WIFIIFACE:
        clazz = OmfWifiInterface

    element = clazz(guid, testbed_instance)
    #import pdb; pdb.set_trace()
    testbed_instance._elements[guid] = element

def start(testbed_instance, guid):
    element = testbed_instance.elements.get(guid)
    element.start()

def stop(testbed_instance, guid):
    element = testbed_instance.elements.get(guid)
    element.stop()

def status(testbed_instance, guid):
    element = testbed_instance.elements.get(guid)
    return element.status()

def configure(testbed_instance, guid):
    element = testbed_instance.elements.get(guid)
    return element.status()

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
        "from": (TESTBED_ID, WIFIIFACE, "chan"),
        "to":   (TESTBED_ID, CHANNEL, "devs"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, OMFAPPLICATION, "node"),
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
                "flags": Attribute.NoDefaultValue, 
                "validation_function": validation.is_string
            }),
    "type": dict({
                "name": "type",
                "help": "Corresponds to the OMF attributes net/w0/type",
                "type": Attribute.STRING,
                "flags": Attribute.NoDefaultValue, 
                "validation_function": validation.is_string
            }),
    "channel": dict({
                "name": "channel",
                "help": "Corresponds to the OMF attributes net/w0/channel",
                "type": Attribute.STRING,
                "flags": Attribute.NoDefaultValue, 
                "validation_function": validation.is_string
            }),
    "essid": dict({
                "name": "essid",
                "help": "Corresponds to the OMF attributes net/w0/essid",
                "type": Attribute.STRING,
                "flags": Attribute.NoDefaultValue, 
                "validation_function": validation.is_string
            }),
    "ip": dict({
                "name": "ip",
                "help": "Corresponds to the OMF attributes net/w0/ip",
                "type": Attribute.STRING,
                "flags": Attribute.NoDefaultValue, 
                "validation_function": validation.is_ip4_address
            }),



    })

traces = dict()

create_order = [ NODE, WIFIIFACE, CHANNEL, OMFAPPLICATION ]
configure_order = [ WIFIIFACE,  NODE, CHANNEL, OMFAPPLICATION ]

factories_info = dict({
    NODE: dict({
            "help": "OMF Node",
            "category": FC.CATEGORY_NODES,
            "create_function": functools.partial(create, NODE),
            "box_attributes": ["hostname"],
            "connector_types": ["devs", "apps"],
            "tags": [tags.NODE, tags.ALLOW_ROUTES],
       }),
    WIFIIFACE: dict({
            "help": "Wireless network interface",
            "category": FC.CATEGORY_DEVICES,
            "create_function": functools.partial(create, WIFIIFACE),
            "configure_function": configure,
            "box_attributes": ["mode", "type", "channel", "essid", "ip"],
            "connector_types": ["node", "chan"],
            "tags": [tags.INTERFACE, tags.HAS_ADDRESSES],
       }),
    CHANNEL: dict({
            "help": "Wireless channel",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create,
            "create_function": functools.partial(create, CHANNEL),
            "box_attributes": ["mode", "type", "channel", "essid"],
            "connector_types": ["devs"],
       }),
    OMFAPPLICATION: dict({
            "help": "Generic executable command line application",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": functools.partial(create, OMFAPPLICATION),
            "start_function": start,
            "stop_function": stop,
            "status_function": status,
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

