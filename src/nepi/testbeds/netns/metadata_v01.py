#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

from nepi.util.tunchannel_impl import \
    preconfigure_tunchannel, postconfigure_tunchannel, \
    wait_tunchannel, create_tunchannel, \
    crossconnect_tunchannel_peer_init, \
    crossconnect_tunchannel_peer_compl

import functools

NODE = "Node"
P2PIFACE = "P2PNodeInterface"
TAPIFACE = "TapNodeInterface"
NODEIFACE = "NodeInterface"
SWITCH = "Switch"
APPLICATION = "Application"
TUNCHANNEL = "TunChannel"

NS3_TESTBED_ID = "ns3"
FDNETDEV = "ns3::FileDescriptorNetDevice"

def _follow_trace(testbed_instance, guid, trace_id, filename):
    filepath = testbed_instance.trace_filepath(guid, trace_id, filename)
    trace = open(filepath, "wb")
    testbed_instance.follow_trace(guid, trace_id, trace, filename)
    return trace

### Connection functions ####

def connect_switch(testbed_instance, switch_guid, interface_guid):
    switch = testbed_instance._elements[switch_guid]
    interface = testbed_instance._elements[interface_guid]
    switch.connect(interface)
   
def connect_fd(testbed_instance, tap_guid, cross_data):
    import passfd
    import socket
    tap = testbed_instance._elements[tap_guid]
    address = cross_data["tun_addr"]
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.connect(address)
    passfd.sendfd(sock, tap.fd, '0')
    # TODO: after succesful transfer, the tap device should close the fd

def connect_tunchannel_tap(testbed_instance, chan_guid, tap_guid):
    tap = testbed_instance._elements[tap_guid]
    chan = testbed_instance._elements[chan_guid]

    # Create a file object for the tap's interface device 
    # and send it to the channel. It should comply with all the
    # requirements for the channel's tun_socket.
    import os
    chan.tun_socket = os.fdopen(tap.fd)
    
    # Set the channel to ethernet mode (it's a tap)
    chan.ethernet_mode = True
    
    # Check to see if the device uses PI headers
    # It's normally so
    with_pi = True
    try:
        import fcntl
        import struct
        TUNGETIFF = 0x800454d2
        IFF_NO_PI = 0x00001000
        struct_ifreq = "x"*16+"H"+"x"*22
        flags = struct.unpack(struct_ifreq,
            fcntl.ioctl(tap.fd, TUNGETIFF, struct.pack(struct_ifreq,0)) )
        with_pi = (0 == (flags & IFF_NO_PI))
    except:
        # maybe the kernel doesn't support the IOCTL,
        # in which case, we assume it uses PI headers (as is usual)
        pass
    chan.with_pi = with_pi

### Trace functions ###

def nodepcap_trace(testbed_instance, guid, trace_id):
    node = testbed_instance._elements[guid]
    parameters = testbed_instance._get_parameters(guid)
    filename = "%d-cap.stdout" % guid
    stdout = _follow_trace(testbed_instance, guid, "pcap_stdout", filename)
    filename = "%d-pcap.stderr" % guid
    stderr = _follow_trace(testbed_instance, guid, "pcap_stderr", filename)
    filename = "%d-node.pcap" % guid
    filepath = testbed_instance.trace_filenpath(guid, trace_id, filename)
    command = "tcpdump -i 'any' -w %s" % filepath
    user = "root"
    trace = node.Popen(command, shell = True, stdout = stdout, 
            stderr = stderr, user = user)
    testbed_instance.follow_trace(guid, trace_id, trace, filename)

trace_functions = dict({
    "pcap": nodepcap_trace,
    })

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
    command = parameters["command"]
    user = None
    if "user" in parameters:
        user = parameters["user"]
    stdout = stderr = None
    if "stdout" in traces:
        filename = "%d-stdout.trace" % guid
        stdout = _follow_trace(testbed_instance, guid, "stdout", filename)
    if "stderr" in traces:
        filename = "%d-stderr.trace" % guid
        stderr = _follow_trace(testbed_instance, guid, "stderr", filename)
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

### Configure functions ###

def configure_traces(testbed_instance, guid):
    traces = testbed_instance._get_traces(guid)
    for trace_id in traces:
        if trace_id not in trace_functions:
            continue
        trace_func = trace_functions[trace_id]
        trace_func(testbed_instance, guid, trace_id)

def configure_device(testbed_instance, guid):
    configure_traces(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    if not guid in testbed_instance._add_address:
        return
    addresses = testbed_instance._add_address[guid]
    for address in addresses:
        (address, netprefix, broadcast) = address
        # TODO: Decide if we should add a ipv4 or ipv6 address
        element.add_v4_address(address, netprefix)

def configure_node(testbed_instance, guid):
    configure_traces(testbed_instance, guid)
    element = testbed_instance._elements[guid]
    if not guid in testbed_instance._add_route:
        return
    routes = testbed_instance._add_route[guid]
    for route in routes:
        (destination, netprefix, nexthop) = route
        element.add_route(prefix = destination, prefix_len = netprefix,
            nexthop = nexthop)

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
    "->fd": dict({
                "help": "File descriptor receptor for devices with file descriptors",
                "name": "->fd",
                "max": 1,
                "min": 0
            }),
    "fd->": dict({
                "help": "File descriptor provider for devices with file descriptors",
                "name": "fd->",
                "max": 1,
                "min": 0
            }),
    "switch": dict({
                "help": "Connector to a switch", 
                "name": "switch",
                "max": 1, 
                "min": 0
            }),
    "tcp": dict({
                "help": "ip-ip tunneling over TCP link", 
                "name": "tcp",
                "max": 1, 
                "min": 0
            }),
    "udp": dict({
                "help": "ip-ip tunneling over UDP datagrams", 
                "name": "udp",
                "max": 1, 
                "min": 0
            }),
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, P2PIFACE, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, TAPIFACE, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, NODEIFACE, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, P2PIFACE, "p2p"),
        "to":   (TESTBED_ID, P2PIFACE, "p2p"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "fd->"),
        "to":   (None, None, "->fd"),
        "compl_code": connect_fd,
        "can_cross": True
    }),
     dict({
        "from": (TESTBED_ID, SWITCH, "devs"),
        "to":   (TESTBED_ID, NODEIFACE, "switch"),
        "init_code": connect_switch,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APPLICATION, "node"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNCHANNEL, "->fd" ),
        "to":   (TESTBED_ID, TAPIFACE, "fd->" ),
        "init_code": connect_tunchannel_tap,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNCHANNEL, "tcp"),
        "to":   (None, None, "tcp"),
        "init_code": functools.partial(crossconnect_tunchannel_peer_init,"tcp"),
        "compl_code": functools.partial(crossconnect_tunchannel_peer_compl,"tcp"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, TUNCHANNEL, "udp"),
        "to":   (None, None, "udp"),
        "init_code": functools.partial(crossconnect_tunchannel_peer_init,"udp"),
        "compl_code": functools.partial(crossconnect_tunchannel_peer_compl,"udp"),
        "can_cross": True
    }),
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
        }),
    "node_pcap": dict({
                "name": "pcap",
                "help": "tcpdump at all node interfaces",
        }) 
    })

create_order = [ NODE, P2PIFACE, NODEIFACE, TAPIFACE, 
        TUNCHANNEL, SWITCH,
        APPLICATION ]

configure_order = [ P2PIFACE, NODEIFACE, TAPIFACE, 
        TUNCHANNEL, SWITCH, 
        NODE, APPLICATION ]

factories_info = dict({
    NODE: dict({
            "allow_routes": True,
            "help": "Emulated Node with virtualized network stack",
            "category": "topology",
            "create_function": create_node,
            "configure_function": configure_node,
            "box_attributes": ["forward_X11"],
            "connector_types": ["devs", "apps"],
            "traces": ["node_pcap"]
       }),
    P2PIFACE: dict({
            "allow_addresses": True,
            "help": "Point to point network interface",
            "category": "devices",
            "create_function": create_p2piface,
            "configure_function": configure_device,
            "box_attributes": ["lladdr", "up", "device_name", "mtu", 
                "multicast", "broadcast", "arp"],
            "connector_types": ["node", "p2p"]
       }),
    TAPIFACE: dict({
            "allow_addresses": True,
            "help": "Tap device network interface",
            "category": "devices",
            "create_function": create_tapiface,
            "configure_function": configure_device,
            "box_attributes": ["lladdr", "up", "device_name", "mtu", 
                "multicast", "broadcast", "arp"],
            "connector_types": ["node", "fd->"]
        }),
    NODEIFACE: dict({
            "allow_addresses": True,
            "help": "Node network interface",
            "category": "devices",
            "create_function": create_nodeiface,
            "configure_function": configure_device,
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
     TUNCHANNEL : dict({
        "category": "Channel",
        "create_function": create_tunchannel,
        "preconfigure_function": preconfigure_tunchannel,
        "configure_function": postconfigure_tunchannel,
        "start_function": wait_tunchannel,
        "help": "Channel to forward "+TAPIFACE+" data to "
                "other TAP interfaces supporting the NEPI tunneling protocol.",
        "connector_types": ["->fd", "udp", "tcp"],
        "allow_addresses": False,
        "box_attributes": ["tun_proto", "tun_addr", "tun_port", "tun_key"]
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

