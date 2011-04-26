#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from constants import TESTBED_ID
from nepi.core import metadata
from nepi.core.attributes import Attribute
from nepi.util import validation
from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

NODE = "Node"
NODEIFACE = "NodeInterface"
TUNIFACE = "TunInterface"
APPLICATION = "Application"
INTERNET = "Internet"

PL_TESTBED_ID = "planetlab"

### Connection functions ####

def connect_node_iface_node(testbed_instance, node, iface):
    iface.node = node

def connect_node_iface_inet(testbed_instance, iface, inet):
    iface.has_internet = True

def connect_tun_iface_node(testbed_instance, node, iface):
    if not node.emulation:
        raise RuntimeError, "Usage of TUN interfaces requires emulation"
    iface.node = node
    node.required_vsys.update(('fd_tuntap', 'vif_up'))

def connect_app(testbed_instance, node, app):
    app.node = node
    
    if app.depends:
        node.required_packages.update(set(
            app.depends.split() ))
    

### Creation functions ###

def create_node(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    
    # create element with basic attributes
    element = testbed_instance._make_node(parameters)
    
    # add constraint on number of (real) interfaces
    # by counting connected devices
    dev_guids = testbed_instance.get_connected(guid, "node", "devs")
    num_open_ifaces = sum( # count True values
        TUNEIFACE == testbed_instance._get_factory_id(guid)
        for guid in dev_guids )
    element.min_num_external_ifaces = num_open_ifaces
    
    testbed_instance.elements[guid] = element

def create_nodeiface(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_node_iface(parameters)
    testbed_instance.elements[guid] = element

def create_tuniface(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_tun_iface(parameters)
    testbed_instance.elements[guid] = element

def create_application(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_application(parameters)
    testbed_instance.elements[guid] = element

def create_internet(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_internet(parameters)
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
        del testbed_instance._add_address[guid]
    
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

def configure_tuniface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    if not guid in testbed_instance._add_address:
        return
    
    addresses = testbed_instance._add_address[guid]
    for address in addresses:
        (address, netprefix, broadcast) = address
        raise NotImplementedError, "C'mon... TUNs are hard..."
    
    # Do some validations
    element.validate()

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

def configure_application(testbed_instance, guid):
    app = testbed_instance._elements[guid]
    
    # Just inject configuration stuff
    app.home_path = "nepi-app-%s" % (guid,)
    app.ident_path = testbed_instance.sliceSSHKey
    app.slicename = testbed_instance.slicename
    
    # Do some validations
    app.validate()
    
    # Wait for dependencies
    app.node.wait_dependencies()
    
    # Install stuff
    app.setup()

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
   })

connections = [
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, NODEIFACE, "node"),
        "code": connect_node_iface_node,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "devs"),
        "to":   (TESTBED_ID, TUNIFACE, "node"),
        "code": connect_tun_iface_node,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODEIFACE, "inet"),
        "to":   (TESTBED_ID, INTERNET, "devs"),
        "code": connect_node_iface_inet,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, APPLICATION, "node"),
        "code": connect_app,
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
    })

create_order = [ INTERNET, NODE, NODEIFACE, TUNIFACE, APPLICATION ]

configure_order = [ INTERNET, NODE, NODEIFACE, TUNIFACE, APPLICATION ]

factories_info = dict({
    NODE: dict({
            "allow_routes": False,
            "help": "Virtualized Node (V-Server style)",
            "category": "topology",
            "create_function": create_node,
            "preconfigure_function": configure_node,
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
            ],
            "connector_types": ["devs", "apps"]
       }),
    NODEIFACE: dict({
            "allow_addresses": True,
            "help": "External network interface - they cannot be brought up or down, and they MUST be connected to the internet.",
            "category": "devices",
            "create_function": create_nodeiface,
            "preconfigure_function": configure_nodeiface,
            "box_attributes": [ ],
            "connector_types": ["node", "inet"]
        }),
    TUNIFACE: dict({
            "allow_addresses": True,
            "help": "Virtual TUN network interface",
            "category": "devices",
            "create_function": create_tuniface,
            "preconfigure_function": configure_tuniface,
            "box_attributes": [
                "up", "device_name", "mtu", "snat",
            ],
            "connector_types": ["node"]
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
            "traces": ["stdout", "stderr"]
        }),
    INTERNET: dict({
            "help": "Internet routing",
            "category": "topology",
            "create_function": create_internet,
            "connector_types": ["devs"],
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
    def factories_info(self):
        return factories_info

    @property
    def testbed_attributes(self):
        return testbed_attributes

