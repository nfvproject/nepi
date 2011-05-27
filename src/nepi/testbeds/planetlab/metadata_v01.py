#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP

import functools
import os
import os.path

NODE = "Node"
NODEIFACE = "NodeInterface"
TUNIFACE = "TunInterface"
TAPIFACE = "TapInterface"
APPLICATION = "Application"
DEPENDENCY = "Dependency"
NEPIDEPENDENCY = "NepiDependency"
NS3DEPENDENCY = "NS3Dependency"
INTERNET = "Internet"
NETPIPE = "NetPipe"

PL_TESTBED_ID = "planetlab"


### Custom validation functions ###
def is_addrlist(attribute, value):
    if not validation.is_string(attribute, value):
        return False
    
    if not value:
        # No empty strings
        return False
    
    components = value.split(',')
    
    for component in components:
        if '/' in component:
            addr, mask = component.split('/',1)
        else:
            addr, mask = component, '32'
        
        if mask is not None and not (mask and mask.isdigit()):
            # No empty or nonnumeric masks
            return False
        
        if not validation.is_ip4_address(attribute, addr):
            # Address part must be ipv4
            return False
        
    return True

def is_portlist(attribute, value):
    if not validation.is_string(attribute, value):
        return False
    
    if not value:
        # No empty strings
        return False
    
    components = value.split(',')
    
    for component in components:
        if '-' in component:
            pfrom, pto = component.split('-',1)
        else:
            pfrom = pto = component
        
        if not pfrom or not pto or not pfrom.isdigit() or not pto.isdigit():
            # No empty or nonnumeric ports
            return False
        
    return True


### Connection functions ####

def connect_node_iface_node(testbed_instance, node_guid, iface_guid):
    node = testbed_instance._elements[node_guid]
    iface = testbed_instance._elements[iface_guid]
    iface.node = node

def connect_node_iface_inet(testbed_instance, iface_guid, inet_guid):
    iface = testbed_instance._elements[iface_guid]
    iface.has_internet = True

def connect_tun_iface_node(testbed_instance, node_guid, iface_guid):
    node = testbed_instance._elements[node_guid]
    iface = testbed_instance._elements[iface_guid]
    if not node.emulation:
        raise RuntimeError, "Use of TUN interfaces requires emulation"
    iface.node = node
    node.required_vsys.update(('fd_tuntap', 'vif_up'))
    node.required_packages.update(('python', 'python-crypto', 'python-setuptools', 'gcc'))

def connect_tun_iface_peer(proto, testbed_instance, iface_guid, peer_iface_guid):
    iface = testbed_instance._elements[iface_guid]
    peer_iface = testbed_instance._elements[peer_iface_guid]
    iface.peer_iface = peer_iface
    iface.peer_proto = \
    iface.tun_proto = proto
    iface.tun_key = peer_iface.tun_key

def crossconnect_tun_iface_peer_init(proto, testbed_instance, iface_guid, peer_iface_data):
    iface = testbed_instance._elements[iface_guid]
    iface.peer_iface = None
    iface.peer_addr = peer_iface_data.get("tun_addr")
    iface.peer_proto = peer_iface_data.get("tun_proto") or proto
    iface.peer_port = peer_iface_data.get("tun_port")
    iface.tun_key = min(iface.tun_key, peer_iface_data.get("tun_key"))
    iface.tun_proto = proto
    
    preconfigure_tuniface(testbed_instance, iface_guid)

def crossconnect_tun_iface_peer_compl(proto, testbed_instance, iface_guid, peer_iface_data):
    # refresh (refreshable) attributes for second-phase
    iface = testbed_instance._elements[iface_guid]
    iface.peer_addr = peer_iface_data.get("tun_addr")
    iface.peer_proto = peer_iface_data.get("tun_proto") or proto
    iface.peer_port = peer_iface_data.get("tun_port")
    
    postconfigure_tuniface(testbed_instance, iface_guid)

def crossconnect_tun_iface_peer_both(proto, testbed_instance, iface_guid, peer_iface_data):
    crossconnect_tun_iface_peer_init(proto, testbed_instance, iface_guid, peer_iface_data)
    crossconnect_tun_iface_peer_compl(proto, testbed_instance, iface_guid, peer_iface_data)

def connect_dep(testbed_instance, node_guid, app_guid):
    node = testbed_instance._elements[node_guid]
    app = testbed_instance._elements[app_guid]
    app.node = node
    
    if app.depends:
        node.required_packages.update(set(
            app.depends.split() ))
    
    if app.add_to_path:
        if app.home_path and app.home_path not in node.pythonpath:
            node.pythonpath.append(app.home_path)
    
    if app.env:
        for envkey, envval in app.env.iteritems():
            envval = app._replace_paths(envval)
            node.env[envkey].append(envval)

def connect_node_netpipe(testbed_instance, node_guid, netpipe_guid):
    node = testbed_instance._elements[node_guid]
    netpipe = testbed_instance._elements[netpipe_guid]
    if not node.emulation:
        raise RuntimeError, "Use of NetPipes requires emulation"
    netpipe.node = node
    

### Creation functions ###

def create_node(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    
    # create element with basic attributes
    element = testbed_instance._make_node(parameters)
    
    # add constraint on number of (real) interfaces
    # by counting connected devices
    dev_guids = testbed_instance.get_connected(guid, "devs", "node")
    num_open_ifaces = sum( # count True values
        NODEIFACE == testbed_instance._get_factory_id(guid)
        for guid in dev_guids )
    element.min_num_external_ifaces = num_open_ifaces
    
    # require vroute vsys if we have routes to set up
    routes = testbed_instance._add_route.get(guid)
    if routes:
        element.required_vsys.add("vroute")
    
    testbed_instance.elements[guid] = element

def create_nodeiface(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_node_iface(parameters)
    testbed_instance.elements[guid] = element

def create_tuniface(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_tun_iface(parameters)
    
    # Set custom addresses, if there are any already
    # Setting this early helps set up P2P links
    if guid in testbed_instance._add_address and not (element.address or element.netmask or element.netprefix):
        addresses = testbed_instance._add_address[guid]
        for address in addresses:
            (address, netprefix, broadcast) = address
            element.add_address(address, netprefix, broadcast)
    
    testbed_instance.elements[guid] = element

def create_tapiface(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_tap_iface(parameters)
    
    # Set custom addresses, if there are any already
    # Setting this early helps set up P2P links
    if guid in testbed_instance._add_address and not (element.address or element.netmask or element.netprefix):
        addresses = testbed_instance._add_address[guid]
        for address in addresses:
            (address, netprefix, broadcast) = address
            element.add_address(address, netprefix, broadcast)
    
    testbed_instance.elements[guid] = element

def create_application(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_application(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-app-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_dependency(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_dependency(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-dep-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_nepi_dependency(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_nepi_dependency(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-nepi-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_ns3_dependency(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_ns3_dependency(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-ns3-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_internet(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_internet(parameters)
    testbed_instance.elements[guid] = element

def create_netpipe(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_netpipe(parameters)
    testbed_instance.elements[guid] = element

### Start/Stop functions ###

def start_application(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    traces = testbed_instance._get_traces(guid)
    app = testbed_instance.elements[guid]
    
    app.stdout = "stdout" in traces
    app.stderr = "stderr" in traces
    app.buildlog = "buildlog" in traces
    
    app.start()

def stop_application(testbed_instance, guid):
    app = testbed_instance.elements[guid]
    app.kill()

### Status functions ###

def status_application(testbed_instance, guid):
    if guid not in testbed_instance.elements.keys():
        return STATUS_NOT_STARTED
    
    app = testbed_instance.elements[guid]
    return app.status()

### Configure functions ###

def configure_nodeiface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    
    # Cannot explicitly configure addresses
    if guid in testbed_instance._add_address:
        raise ValueError, "Cannot explicitly set address of public PlanetLab interface"
    
    # Get siblings
    node_guid = testbed_instance.get_connected(guid, "node", "devs")[0]
    dev_guids = testbed_instance.get_connected(node_guid, "node", "devs")
    siblings = [ self._element[dev_guid] 
                 for dev_guid in dev_guids
                 if dev_guid != guid ]
    
    # Fetch address from PLC api
    element.pick_iface(siblings)
    
    # Do some validations
    element.validate()

def preconfigure_tuniface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    
    # Set custom addresses if any, and if not set already
    if guid in testbed_instance._add_address and not (element.address or element.netmask or element.netprefix):
        addresses = testbed_instance._add_address[guid]
        for address in addresses:
            (address, netprefix, broadcast) = address
            element.add_address(address, netprefix, broadcast)
    
    # Link to external interface, if any
    for iface in testbed_instance._elements.itervalues():
        if isinstance(iface, testbed_instance._interfaces.NodeIface) and iface.node is element.node and iface.has_internet:
            element.external_iface = iface
            break

    # Set standard TUN attributes
    if (not element.tun_addr or not element.tun_port) and element.external_iface:
        element.tun_addr = element.external_iface.address
        element.tun_port = 15000 + int(guid)

    # Set enabled traces
    traces = testbed_instance._get_traces(guid)
    element.capture = 'packets' in traces
    
    # Do some validations
    element.validate()
    
    # First-phase setup
    if element.peer_proto:
        if element.peer_iface and isinstance(element.peer_iface, testbed_instance._interfaces.TunIface):
            # intra tun
            listening = id(element) < id(element.peer_iface)
        else:
            # cross tun
            if not element.tun_addr or not element.tun_port:
                listening = True
            elif not element.peer_addr or not element.peer_port:
                listening = True
            else:
                # both have addresses...
                # ...the one with the lesser address listens
                listening = element.tun_addr < element.peer_addr
        element.prepare( 
            'tun-%s' % (guid,),
             listening)

def postconfigure_tuniface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    
    # Second-phase setup
    element.setup()
    
def wait_tuniface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    
    # Second-phase setup
    element.async_launch_wait()
    

def configure_node(testbed_instance, guid):
    node = testbed_instance._elements[guid]
    
    # Just inject configuration stuff
    node.home_path = "nepi-node-%s" % (guid,)
    node.ident_path = testbed_instance.sliceSSHKey
    node.slicename = testbed_instance.slicename
    
    # Do some validations
    node.validate()
    
    # recently provisioned nodes may not be up yet
    sleeptime = 1.0
    while not node.is_alive():
        time.sleep(sleeptime)
        sleeptime = min(30.0, sleeptime*1.5)
    
    # this will be done in parallel in all nodes
    # this call only spawns the process
    node.install_dependencies()

def configure_node_routes(testbed_instance, guid):
    node = testbed_instance._elements[guid]
    routes = testbed_instance._add_route.get(guid)
    
    if routes:
        devs = [ dev
            for dev_guid in testbed_instance.get_connected(guid, "devs", "node")
            for dev in ( testbed_instance._elements.get(dev_guid) ,)
            if dev and isinstance(dev, testbed_instance._interfaces.TunIface) ]
        
        node.configure_routes(routes, devs)

def configure_application(testbed_instance, guid):
    app = testbed_instance._elements[guid]
    
    # Do some validations
    app.validate()
    
    # Wait for dependencies
    app.node.wait_dependencies()
    
    # Install stuff
    app.setup()

def configure_dependency(testbed_instance, guid):
    dep = testbed_instance._elements[guid]
    
    # Do some validations
    dep.validate()
    
    # Wait for dependencies
    dep.node.wait_dependencies()
    
    # Install stuff
    dep.setup()

def configure_netpipe(testbed_instance, guid):
    netpipe = testbed_instance._elements[guid]
    
    # Do some validations
    netpipe.validate()
    
    # Wait for dependencies
    netpipe.node.wait_dependencies()
    
    # Install rules
    netpipe.configure()

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
    "deps": dict({
                "help": "Connector from node to application dependencies "
                        "(packages and applications that need to be installed)", 
                "name": "deps",
                "max": -1, 
                "min": 0
            }),
    "inet": dict({
                "help": "Connector from network interfaces to the internet", 
                "name": "inet",
                "max": 1, 
                "min": 1
            }),
    "node": dict({
                "help": "Connector to a Node", 
                "name": "node",
                "max": 1, 
                "min": 1
            }),
    "pipes": dict({
                "help": "Connector to a NetPipe", 
                "name": "pipes",
                "max": 2, 
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
    "fd->": dict({
                "help": "TUN device file descriptor provider", 
                "name": "fd->",
                "max": 1, 
                "min": 0
            }),
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, NODEIFACE, "node"),
        "init_code": connect_node_iface_node,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, TUNIFACE, "node"),
        "init_code": connect_tun_iface_node,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, TAPIFACE, "node"),
        "init_code": connect_tun_iface_node,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODEIFACE, "inet"),
        "to":   (TESTBED_ID, INTERNET, "devs"),
        "init_code": connect_node_iface_inet,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APPLICATION, "node"),
        "init_code": connect_dep,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "deps"),
        "to":   (TESTBED_ID, DEPENDENCY, "node"),
        "init_code": connect_dep,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "deps"),
        "to":   (TESTBED_ID, NEPIDEPENDENCY, "node"),
        "init_code": connect_dep,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "deps"),
        "to":   (TESTBED_ID, NS3DEPENDENCY, "node"),
        "init_code": connect_dep,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "pipes"),
        "to":   (TESTBED_ID, NETPIPE, "node"),
        "init_code": connect_node_netpipe,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNIFACE, "tcp"),
        "to":   (TESTBED_ID, TUNIFACE, "tcp"),
        "init_code": functools.partial(connect_tun_iface_peer,"tcp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNIFACE, "udp"),
        "to":   (TESTBED_ID, TUNIFACE, "udp"),
        "init_code": functools.partial(connect_tun_iface_peer,"udp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "tcp"),
        "to":   (TESTBED_ID, TAPIFACE, "tcp"),
        "init_code": functools.partial(connect_tun_iface_peer,"tcp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "udp"),
        "to":   (TESTBED_ID, TAPIFACE, "udp"),
        "init_code": functools.partial(connect_tun_iface_peer,"udp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNIFACE, "tcp"),
        "to":   (None, None, "tcp"),
        "init_code": functools.partial(crossconnect_tun_iface_peer_init,"tcp"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_compl,"tcp"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, TUNIFACE, "udp"),
        "to":   (None, None, "udp"),
        "init_code": functools.partial(crossconnect_tun_iface_peer_init,"udp"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_compl,"udp"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, TUNIFACE, "fd->"),
        "to":   (None, None, "->fd"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_both,"fd"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "tcp"),
        "to":   (None, None, "tcp"),
        "init_code": functools.partial(crossconnect_tun_iface_peer_init,"tcp"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_compl,"tcp"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "udp"),
        "to":   (None, None, "udp"),
        "init_code": functools.partial(crossconnect_tun_iface_peer_init,"udp"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_compl,"udp"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "fd->"),
        "to":   (None, None, "->fd"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_both,"fd"),
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
                "validation_function": validation.is_bool,
            }),
    "hostname": dict({      
                "name": "hostname",
                "help": "Constrain hostname during resource discovery. May use wildcards.",
                "type": Attribute.STRING, 
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string,
            }),
    "architecture": dict({      
                "name": "architecture",
                "help": "Constrain architexture during resource discovery.",
                "type": Attribute.ENUM, 
                "flags": Attribute.DesignOnly,
                "allowed": ["x86_64",
                            "i386"],
                "validation_function": validation.is_enum,
            }),
    "operating_system": dict({      
                "name": "operatingSystem",
                "help": "Constrain operating system during resource discovery.",
                "type": Attribute.ENUM, 
                "flags": Attribute.DesignOnly,
                "allowed": ["f8",
                            "f12",
                            "f14",
                            "centos",
                            "other"],
                "validation_function": validation.is_enum,
            }),
    "site": dict({      
                "name": "site",
                "help": "Constrain the PlanetLab site this node should reside on.",
                "type": Attribute.ENUM, 
                "flags": Attribute.DesignOnly,
                "allowed": ["PLE",
                            "PLC",
                            "PLJ"],
                "validation_function": validation.is_enum,
            }),
    "emulation": dict({      
                "name": "emulation",
                "help": "Enable emulation on this node. Enables NetfilterRoutes, bridges, and a host of other functionality.",
                "type": Attribute.BOOL,
                "value": False, 
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_bool,
            }),
    "min_reliability": dict({
                "name": "minReliability",
                "help": "Constrain reliability while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,100),
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_double,
            }),
    "max_reliability": dict({
                "name": "maxReliability",
                "help": "Constrain reliability while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,100),
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_double,
            }),
    "min_bandwidth": dict({
                "name": "minBandwidth",
                "help": "Constrain available bandwidth while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,2**31),
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_double,
            }),
    "max_bandwidth": dict({
                "name": "maxBandwidth",
                "help": "Constrain available bandwidth while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,2**31),
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_double,
            }),
            
    "up": dict({
                "name": "up",
                "help": "Link up",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "primary": dict({
                "name": "primary",
                "help": "This is the primary interface for the attached node",
                "type": Attribute.BOOL,
                "value": True,
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
                "range": (0,1500),
                "validation_function": validation.is_integer_range(0,1500)
            }),
    "mask":  dict({
                "name": "mask", 
                "help": "Network mask for the device (eg: 24 for /24 network)",
                "type": Attribute.INTEGER,
                "validation_function": validation.is_integer_range(8,24)
            }),
    "snat":  dict({
                "name": "snat", 
                "help": "Enable SNAT (source NAT to the internet) no this device",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "pointopoint":  dict({
                "name": "pointopoint", 
                "help": "If the interface is a P2P link, the remote endpoint's IP "
                        "should be set on this attribute.",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "txqueuelen":  dict({
                "name": "mask", 
                "help": "Transmission queue length (in packets)",
                "type": Attribute.INTEGER,
                "flags": Attribute.DesignOnly,
                "range" : (1,10000),
                "validation_function": validation.is_integer
            }),
            
    "command": dict({
                "name": "command",
                "help": "Command line string",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "sudo": dict({
                "name": "sudo",
                "help": "Run with root privileges",
                "type": Attribute.BOOL,
                "flags": Attribute.DesignOnly,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "stdin": dict({
                "name": "stdin",
                "help": "Standard input",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
            
    "depends": dict({
                "name": "depends",
                "help": "Space-separated list of packages required to run the application",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "build-depends": dict({
                "name": "buildDepends",
                "help": "Space-separated list of packages required to build the application",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "sources": dict({
                "name": "sources",
                "help": "Space-separated list of regular files to be deployed in the working path prior to building. "
                        "Archives won't be expanded automatically.",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "build": dict({
                "name": "build",
                "help": "Build commands to execute after deploying the sources. "
                        "Sources will be in the ${SOURCES} folder. "
                        "Example: tar xzf ${SOURCES}/my-app.tgz && cd my-app && ./configure && make && make clean.\n"
                        "Try to make the commands return with a nonzero exit code on error.\n"
                        "Also, do not install any programs here, use the 'install' attribute. This will "
                        "help keep the built files constrained to the build folder (which may "
                        "not be the home folder), and will result in faster deployment. Also, "
                        "make sure to clean up temporary files, to reduce bandwidth usage between "
                        "nodes when transferring built packages.",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    "install": dict({
                "name": "install",
                "help": "Commands to transfer built files to their final destinations. "
                        "Sources will be in the initial working folder, and a special "
                        "tag ${SOURCES} can be used to reference the experiment's "
                        "home folder (where the application commands will run).\n"
                        "ALL sources and targets needed for execution must be copied there, "
                        "if building has been enabled.\n"
                        "That is, 'slave' nodes will not automatically get any source files. "
                        "'slave' nodes don't get build dependencies either, so if you need "
                        "make and other tools to install, be sure to provide them as "
                        "actual dependencies instead.",
                "type": Attribute.STRING,
                "flags": Attribute.DesignOnly,
                "validation_function": validation.is_string
            }),
    
    "netpipe_mode": dict({      
                "name": "mode",
                "help": "Link mode:\n"
                        " * SERVER: applies to incoming connections\n"
                        " * CLIENT: applies to outgoing connections\n"
                        " * SERVICE: applies to both",
                "type": Attribute.ENUM, 
                "flags": Attribute.DesignOnly,
                "allowed": ["SERVER",
                            "CLIENT",
                            "SERVICE"],
                "validation_function": validation.is_enum,
            }),
    "port_list":  dict({
                "name": "portList", 
                "help": "Port list or range. Eg: '22', '22,23,27', '20-2000'",
                "type": Attribute.STRING,
                "validation_function": is_portlist,
            }),
    "addr_list":  dict({
                "name": "addrList", 
                "help": "Address list or range. Eg: '127.0.0.1', '127.0.0.1,127.0.1.1', '127.0.0.1/8'",
                "type": Attribute.STRING,
                "validation_function": is_addrlist,
            }),
    "bw_in":  dict({
                "name": "bwIn", 
                "help": "Inbound bandwidth limit (in Mbit/s)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_double,
            }),
    "bw_out":  dict({
                "name": "bwOut", 
                "help": "Outbound bandwidth limit (in Mbit/s)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_double,
            }),
    "plr_in":  dict({
                "name": "plrIn", 
                "help": "Inbound packet loss rate (0 = no loss, 1 = 100% loss)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_double,
            }),
    "plr_out":  dict({
                "name": "plrOut", 
                "help": "Outbound packet loss rate (0 = no loss, 1 = 100% loss)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_double,
            }),
    "delay_in":  dict({
                "name": "delayIn", 
                "help": "Inbound packet delay (in milliseconds)",
                "type": Attribute.INTEGER,
                "range": (0,60000),
                "validation_function": validation.is_integer,
            }),
    "delay_out":  dict({
                "name": "delayOut", 
                "help": "Outbound packet delay (in milliseconds)",
                "type": Attribute.INTEGER,
                "range": (0,60000),
                "validation_function": validation.is_integer,
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
    "buildlog": dict({
                "name": "buildlog",
                "help": "Output of the build process",
              }), 
    
    "netpipe_stats": dict({
                "name": "netpipeStats",
                "help": "Information about rule match counters, packets dropped, etc.",
              }),

    "packets": dict({
                "name": "packets",
                "help": "Detailled log of all packets going through the interface",
              }),
    })

create_order = [ INTERNET, NODE, NODEIFACE, TAPIFACE, TUNIFACE, NETPIPE, NEPIDEPENDENCY, NS3DEPENDENCY, DEPENDENCY, APPLICATION ]

configure_order = [ INTERNET, NODE, NODEIFACE, TAPIFACE, TUNIFACE, NETPIPE, NEPIDEPENDENCY, NS3DEPENDENCY, DEPENDENCY, APPLICATION ]

# Start (and prestart) node after ifaces, because the node needs the ifaces in order to set up routes
start_order = [ INTERNET, NODEIFACE, TAPIFACE, TUNIFACE, NODE, NETPIPE, NEPIDEPENDENCY, NS3DEPENDENCY, DEPENDENCY, APPLICATION ]

factories_info = dict({
    NODE: dict({
            "allow_routes": True,
            "help": "Virtualized Node (V-Server style)",
            "category": "topology",
            "create_function": create_node,
            "preconfigure_function": configure_node,
            "prestart_function": configure_node_routes,
            "box_attributes": [
                "forward_X11",
                "hostname",
                "architecture",
                "operating_system",
                "site",
                "emulation",
                "min_reliability",
                "max_reliability",
                "min_bandwidth",
                "max_bandwidth",
                
                # NEPI-in-NEPI attributes
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,
            ],
            "connector_types": ["devs", "apps", "pipes", "deps"]
       }),
    NODEIFACE: dict({
            "has_addresses": True,
            "help": "External network interface - they cannot be brought up or down, and they MUST be connected to the internet.",
            "category": "devices",
            "create_function": create_nodeiface,
            "preconfigure_function": configure_nodeiface,
            "box_attributes": [ ],
            "connector_types": ["node", "inet"]
        }),
    TUNIFACE: dict({
            "allow_addresses": True,
            "help": "Virtual TUN network interface (layer 3)",
            "category": "devices",
            "create_function": create_tuniface,
            "preconfigure_function": preconfigure_tuniface,
            "configure_function": postconfigure_tuniface,
            "prestart_function": wait_tuniface,
            "box_attributes": [
                "up", "device_name", "mtu", "snat", "pointopoint",
                "txqueuelen",
                "tun_proto", "tun_addr", "tun_port", "tun_key"
            ],
            "traces": ["packets"],
            "connector_types": ["node","udp","tcp","fd->"]
        }),
    TAPIFACE: dict({
            "allow_addresses": True,
            "help": "Virtual TAP network interface (layer 2)",
            "category": "devices",
            "create_function": create_tapiface,
            "preconfigure_function": preconfigure_tuniface,
            "configure_function": postconfigure_tuniface,
            "prestart_function": wait_tuniface,
            "box_attributes": [
                "up", "device_name", "mtu", "snat", "pointopoint",
                "txqueuelen",
                "tun_proto", "tun_addr", "tun_port", "tun_key"
            ],
            "traces": ["packets"],
            "connector_types": ["node","udp","tcp","fd->"]
        }),
    APPLICATION: dict({
            "help": "Generic executable command line application",
            "category": "applications",
            "create_function": create_application,
            "start_function": start_application,
            "status_function": status_application,
            "stop_function": stop_application,
            "configure_function": configure_application,
            "box_attributes": ["command", "sudo", "stdin",
                               "depends", "build-depends", "build", "install",
                               "sources" ],
            "connector_types": ["node"],
            "traces": ["stdout", "stderr", "buildlog"]
        }),
    DEPENDENCY: dict({
            "help": "Requirement for package or application to be installed on some node",
            "category": "applications",
            "create_function": create_dependency,
            "preconfigure_function": configure_dependency,
            "box_attributes": ["depends", "build-depends", "build", "install",
                               "sources" ],
            "connector_types": ["node"],
            "traces": ["buildlog"]
        }),
    NEPIDEPENDENCY: dict({
            "help": "Requirement for NEPI inside NEPI - required to run testbed instances inside a node",
            "category": "applications",
            "create_function": create_nepi_dependency,
            "preconfigure_function": configure_dependency,
            "box_attributes": [ ],
            "connector_types": ["node"],
            "traces": ["buildlog"]
        }),
    NS3DEPENDENCY: dict({
            "help": "Requirement for NS3 inside NEPI - required to run NS3 testbed instances inside a node. It also needs NepiDependency.",
            "category": "applications",
            "create_function": create_ns3_dependency,
            "preconfigure_function": configure_dependency,
            "box_attributes": [ ],
            "connector_types": ["node"],
            "traces": ["buildlog"]
        }),
    INTERNET: dict({
            "help": "Internet routing",
            "category": "topology",
            "create_function": create_internet,
            "connector_types": ["devs"],
        }),
    NETPIPE: dict({
            "help": "Link emulation",
            "category": "topology",
            "create_function": create_netpipe,
            "configure_function": configure_netpipe,
            "box_attributes": ["netpipe_mode",
                               "addr_list", "port_list",
                               "bw_in","plr_in","delay_in",
                               "bw_out","plr_out","delay_out"],
            "connector_types": ["node"],
            "traces": ["netpipe_stats"]
        }),
})

testbed_attributes = dict({
        "slice": dict({
            "name": "slice",
            "help": "The name of the PlanetLab slice to use",
            "type": Attribute.STRING,
            "flags": Attribute.DesignOnly | Attribute.HasNoDefaultValue,
            "validation_function": validation.is_string
        }),
        "auth_user": dict({
            "name": "authUser",
            "help": "The name of the PlanetLab user to use for API calls - it must have at least a User role.",
            "type": Attribute.STRING,
            "flags": Attribute.DesignOnly | Attribute.HasNoDefaultValue,
            "validation_function": validation.is_string
        }),
        "auth_pass": dict({
            "name": "authPass",
            "help": "The PlanetLab user's password.",
            "type": Attribute.STRING,
            "flags": Attribute.DesignOnly | Attribute.HasNoDefaultValue,
            "validation_function": validation.is_string
        }),
        "plc_host": dict({
            "name": "plcHost",
            "help": "The PlanetLab PLC API host",
            "type": Attribute.STRING,
            "value": "www.planet-lab.eu",
            "flags": Attribute.DesignOnly,
            "validation_function": validation.is_string
        }),
        "plc_url": dict({
            "name": "plcUrl",
            "help": "The PlanetLab PLC API url pattern - %(hostname)s is replaced by plcHost.",
            "type": Attribute.STRING,
            "value": "https://%(hostname)s:443/PLCAPI/",
            "flags": Attribute.DesignOnly,
            "validation_function": validation.is_string
        }),
        "slice_ssh_key": dict({
            "name": "sliceSSHKey",
            "help": "The controller-local path to the slice user's ssh private key. "
                    "It is the user's responsability to deploy this file where the controller "
                    "will run, it won't be done automatically because it's sensitive information. "
                    "It is recommended that a NEPI-specific user be created for this purpose and "
                    "this purpose alone.",
            "type": Attribute.STRING,
            "flags": Attribute.DesignOnly | Attribute.HasNoDefaultValue,
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
        return create_order

    @property
    def configure_order(self):
        return configure_order

    @property
    def prestart_order(self):
        return start_order

    @property
    def start_order(self):
        return start_order

    @property
    def factories_info(self):
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

