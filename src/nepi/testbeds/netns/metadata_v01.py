#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

NODE = "Node"
P2PIFACE = "P2PNodeInterface"
TAPIFACE = "TapNodeInterface"
NODEIFACE = "NodeInterface"
SWITCH = "Switch"
APPLICATION = "Application"

NS3_TESTBED_ID = "ns3"
FDNETDEV = "ns3::FileDescriptorNetDevice"

### Connection functions ####

def connect_switch(testbed_instance, switch, interface):
    switch.connect(interface)
   
#XXX: This connection function cannot be use to transfer a file descriptor
# to a remote tap device
def connect_fd_local(testbed_instance, tap, fdnd):
    import passfd
    import socket
    fd = tap.file_descriptor
    address = fdnd.socket_address
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.connect(address)
    passfd.sendfd(sock, fd, '0')
    # TODO: after succesful transfer, the tap device should close the fd

### Creation functions ###

def create_node(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    forward_X11 = False
    if "forward_X11" in parameters:
        forward_X11 = parameters["forward_X11"]
        del parameters["forward_X11"]
    element = testbed_instance.netns.Node(forward_X11 = forward_X11)
    testbed_instance.elements[guid] = element

def create_p2piface(testbed_instance, guid):
    if guid in testbed_instance.elements:
        # The interface pair was already instantiated
        return
    # search for the node asociated with the p2piface
    node1_guid = testbed_instance.get_connected(guid, "node", "devs")
    if len(node1_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % guid)
    node1 = testbed_instance.elements[node1_guid[0]]
    # search for the pair p2piface
    p2p_guid = testbed_instance.get_connected(guid, "p2p","p2p")
    if len(p2p_guid) == 0:
        raise RuntimeError("Can't instantiate p2p interface %d. \
                Missing interface pair" % guid)
    guid2 = p2p_guid[0]
    node2_guid = testbed_instance.get_connected(guid2, "node", "devs")
    if len(node2_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % guid2)
    node2 = testbed_instance.elements[node2_guid[0]]
    element1, element2 = testbed_instance.netns.P2PInterface.create_pair(
        node1, node2)
    testbed_instance.elements[guid] = element1
    testbed_instance.elements[guid2] = element2

def create_tapiface(testbed_instance, guid):
    node_guid = testbed_instance.get_connected(guid, "node", "devs")
    if len(node_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % guid)
    node = testbed_instance.elements[node_guid[0]]
    element = node.add_tap()
    testbed_instance.elements[guid] = element

def create_nodeiface(testbed_instance, guid):
    node_guid = testbed_instance.get_connected(guid, "node", "devs")
    if len(node_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % guid)
    node = testbed_instance.elements[node_guid[0]]
    element = node.add_if()
    testbed_instance.elements[guid] = element

def create_switch(testbed_instance, guid):
    element = testbed_instance.netns.Switch()
    testbed_instance.elements[guid] = element

def create_application(testbed_instance, guid):
    testbed_instance.elements[guid] = None # Delayed construction 

### Start/Stop functions ###

def start_application(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    traces = testbed_instance._get_traces(guid)
    user = parameters["user"]
    command = parameters["command"]
    stdout = stderr = None
    if "stdout" in traces:
        filename = testbed_instance.trace_filename(guid, "stdout")
        stdout = open(filename, "wb")
        testbed_instance.follow_trace("stdout", stdout)
    if "stderr" in traces:
        filename = testbed_instance.trace_filename(guid, "stderr")
        stderr = open(filename, "wb")
        testbed_instance.follow_trace("stderr", stderr)

    node_guid = testbed_instance.get_connected(guid, "node", "apps")
    if len(node_guid) == 0:
        raise RuntimeError("Can't instantiate interface %d outside netns \
                node" % guid)
    node = testbed_instance.elements[node_guid[0]]
    element  = node.Popen(command, shell = True, stdout = stdout, 
            stderr = stderr, user = user)
    testbed_instance.elements[guid] = element

### Status functions ###

def status_application(testbed_instance, guid):
    if guid not in testbed_instance.elements.keys():
        return STATUS_NOT_STARTED
    app = testbed_instance.elements[guid]
    if app.poll() == None:
        return STATUS_RUNNING
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
    "p2p": dict({
                "help": "Connector to a P2PInterface", 
                "name": "p2p",
                "max": 1, 
                "min": 0
            }),
    "fd": dict({
                "help": "Connector to a network interface that can receive a file descriptor", 
                "name": "fd",
                "max": 1, 
                "min": 0
            }),
    "switch": dict({
                "help": "Connector to a switch", 
                "name": "switch",
                "max": 1, 
                "min": 0
            })
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, P2PIFACE, "node"),
        "code": None,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, TAPIFACE, "node"),
        "code": None,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, NODEIFACE, "node"),
        "code": None,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, P2PIFACE, "p2p"),
        "to":   (TESTBED_ID, P2PIFACE, "p2p"),
        "code": None,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "fd"),
        "to":   (NS3_TESTBED_ID, FDNETDEV, "fd"),
        "code": connect_fd_local,
        "can_cross": True
    }),
     dict({
        "from": (TESTBED_ID, SWITCH, "devs"),
        "to":   (TESTBED_ID, NODEIFACE, "switch"),
        "code": connect_switch,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APPLICATION, "node"),
        "code": None,
        "can_cross": False
    })
]

attributes = dict({
    "forward_X11": dict({      
                "name": "forward_X11",
                "help": "Forward x11 from main namespace to the node",
                "type": Attribute.BOOL, 
                "value": False,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_bool
            }),
    "lladdr": dict({      
                "name": "lladdr", 
                "help": "Mac address", 
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_mac_address
            }),
    "up": dict({
                "name": "up",
                "help": "Link up",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "device_name": dict({
                "name": "name",
                "help": "Device name",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "mtu":  dict({
                "name": "mtu", 
                "help": "Maximum transmition unit for device",
                "type": Attribute.INTEGER,
                "validation_function": validation.is_integer
            }),
    "broadcast": dict({ 
                "name": "broadcast",
                "help": "Broadcast address",
                "type": Attribute.STRING,
                "validation_function": validation.is_string # TODO: should be is address!
            }),
    "multicast": dict({      
                "name": "multicast",
                "help": "Multicast enabled",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "arp": dict({
                "name": "arp",
                "help": "ARP enabled",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "command": dict({
                "name": "command",
                "help": "Command line string",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "user": dict({
                "name": "user",
                "help": "System user",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "stdin": dict({
                "name": "stdin",
                "help": "Standard input",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    })

traces = dict({
    "stdout": dict({
                "name": "stdout",
                "help": "Standard output stream"
              }),
    "stderr": dict({
                "name": "stderr",
                "help": "Application standard error",
        }) 
    })

factories_order = [ NODE, P2PIFACE, NODEIFACE, TAPIFACE, SWITCH,
        APPLICATION ]

factories_info = dict({
    NODE: dict({
            "allow_routes": True,
            "help": "Emulated Node with virtualized network stack",
            "category": "topology",
            "create_function": create_node,
            "box_attributes": ["forward_X11"],
            "connector_types": ["devs", "apps"]
       }),
    P2PIFACE: dict({
            "allow_addresses": True,
            "help": "Point to point network interface",
            "category": "devices",
            "create_function": create_p2piface,
            "box_attributes": ["lladdr", "up", "device_name", "mtu", 
                "multicast", "broadcast", "arp"],
            "connector_types": ["node", "p2p"]
       }),
    TAPIFACE: dict({
            "allow_addresses": True,
            "help": "Tap device network interface",
            "category": "devices",
            "create_function": create_tapiface,
            "box_attributes": ["lladdr", "up", "device_name", "mtu", 
                "multicast", "broadcast", "arp"],
            "connector_types": ["node", "fd"]
        }),
    NODEIFACE: dict({
            "allow_addresses": True,
            "help": "Node network interface",
            "category": "devices",
            "create_function": create_nodeiface,
            "box_attributes": ["lladdr", "up", "device_name", "mtu", 
                "multicast", "broadcast", "arp"],
            "connector_types": ["node", "switch"]
        }),
    SWITCH: dict({
            "display_name": "Switch",
            "help": "Switch interface",
            "category": "devices",
            "create_function": create_switch,
            "box_attributes": ["up", "device_name", "mtu", "multicast"],
             #TODO: Add attribute ("Stp", help, type, value, range, allowed, readonly, validation_function),
             #TODO: Add attribute ("ForwarddDelay", help, type, value, range, allowed, readonly, validation_function),
             #TODO: Add attribute ("HelloTime", help, type, value, range, allowed, readonly, validation_function),
             #TODO: Add attribute ("AgeingTime", help, type, value, range, allowed, readonly, validation_function),
             #TODO: Add attribute ("MaxAge", help, type, value, range, allowed, readonly, validation_function)
           "connector_types": ["devs"]
        }),
    APPLICATION: dict({
            "help": "Generic executable command line application",
            "category": "applications",
            "create_function": create_application,
            "start_function": start_application,
            "status_function": status_application,
            "box_attributes": ["command", "user"],
            "connector_types": ["node"],
            "traces": ["stdout", "stderr"]
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
         "home_directory": dict({
                "name": "homeDirectory",
                "help": "Path to the directory where traces and other files \
                        will be stored",
                "type": Attribute.STRING,
                "value": False,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            })
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

