# -*- coding: utf-8 -*-

import time

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import metadata
from nepi.core.metadata import Parallel
from nepi.core.attributes import Attribute
from nepi.util import tags, validation
from nepi.util.constants import ApplicationStatus as AS, \
        FactoryCategories as FC, \
        ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP, \
        DeploymentConfiguration as DC

import functools
import os
import os.path
import weakref

NODE = "Node"
NODEIFACE = "NodeInterface"
TUNIFACE = "TunInterface"
TAPIFACE = "TapInterface"
APPLICATION = "Application"
CCNXDAEMON = "CCNxDaemon"
DEPENDENCY = "Dependency"
NEPIDEPENDENCY = "NepiDependency"
NS3DEPENDENCY = "NS3Dependency"
INTERNET = "Internet"
NETPIPE = "NetPipe"
TUNFILTER = "TunFilter"
CLASSQUEUEFILTER = "ClassQueueFilter"
TOSQUEUEFILTER = "TosQueueFilter"
MULTICASTFORWARDER = "MulticastForwarder"
MULTICASTANNOUNCER = "MulticastAnnouncer"
MULTICASTROUTER = "MulticastRouter"

TUNFILTERS = (TUNFILTER, CLASSQUEUEFILTER, TOSQUEUEFILTER)
TAPFILTERS = (TUNFILTER, )
ALLFILTERS = (TUNFILTER, CLASSQUEUEFILTER, TOSQUEUEFILTER)

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
    iface.node = node
    node.required_vsys.update(('fd_tuntap', 'vif_up', 'vif_down'))
    node.required_packages.update(('python', 'python-crypto', 'python-setuptools', 'gcc'))

def connect_tun_iface_peer(proto, testbed_instance, iface_guid, peer_iface_guid):
    iface = testbed_instance._elements[iface_guid]
    peer_iface = testbed_instance._elements[peer_iface_guid]
    iface.peer_iface = peer_iface
    peer_iface.peer_iface = iface
    iface.peer_proto = \
    iface.tun_proto = \
    peer_iface.peer_proto = \
    peer_iface.tun_proto = proto
    iface.tun_key = peer_iface.tun_key

def connect_tun_iface_filter(testbed_instance, iface_guid, filter_guid):
    iface = testbed_instance._elements[iface_guid]
    filt = testbed_instance._elements[filter_guid]
    traces = testbed_instance._get_traces(filter_guid)
    if 'dropped_stats' in traces: 
        args = filt.args if filt.args else ""
        filt.args = ','.join(filt.args.split(',') + ["logdropped=true",])
    iface.filter_module = filt
    filt.iface_guid = iface_guid
    filt.iface = weakref.ref(iface)

    if filt.peer_guid:
        connect_tun_iface_peer(filt.peer_proto, testbed_instance, filt.iface_guid, filt.peer_guid)

def connect_filter_peer(proto, testbed_instance, filter_guid, peer_guid):
    peer = testbed_instance._elements[peer_guid]
    filt = testbed_instance._elements[filter_guid]
    filt.peer_proto = proto
    filt.peer_guid = peer_guid
    if filt.iface_guid:
        connect_tun_iface_peer(filt.peer_proto, testbed_instance, filt.iface_guid, filt.peer_guid)

def connect_filter_filter(proto, testbed_instance, filter_guid, peer_guid):
    peer = testbed_instance._elements[peer_guid]
    filt = testbed_instance._elements[filter_guid]
    filt.peer_proto = proto
    peer.peer_proto = proto
    if filt.iface_guid:
        peer.peer_guid = filt.iface_guid
    if peer.iface_guid:
        filt.peer_guid = peer.iface_guid
    if filt.iface_guid and filt.peer_guid:
        connect_tun_iface_peer(filt.peer_proto, testbed_instance, filt.iface_guid, filt.peer_guid)

def crossconnect_tun_iface_peer_init(proto, testbed_instance, iface_guid, peer_iface_data):
    iface = testbed_instance._elements[iface_guid]
    iface.peer_iface = None
    iface.peer_addr = peer_iface_data.get("tun_addr")
    iface.peer_proto = peer_iface_data.get("tun_proto") or proto
    iface.peer_port = peer_iface_data.get("tun_port")
    iface.peer_cipher = peer_iface_data.get("tun_cipher")
    iface.tun_key = min(iface.tun_key, peer_iface_data.get("tun_key"))
    iface.tun_proto = proto
    
    preconfigure_tuniface(testbed_instance, iface_guid)

def crossconnect_tun_iface_peer_compl(proto, testbed_instance, iface_guid, peer_iface_data):
    # refresh (refreshable) attributes for second-phase
    iface = testbed_instance._elements[iface_guid]
    iface.peer_addr = peer_iface_data.get("tun_addr")
    iface.peer_proto = peer_iface_data.get("tun_proto") or proto
    iface.peer_port = peer_iface_data.get("tun_port")
    iface.peer_cipher = peer_iface_data.get("tun_cipher")
    
    postconfigure_tuniface(testbed_instance, iface_guid)

def crossconnect_tun_iface_peer_both(proto, testbed_instance, iface_guid, peer_iface_data):
    crossconnect_tun_iface_peer_init(proto, testbed_instance, iface_guid, peer_iface_data)
    crossconnect_tun_iface_peer_compl(proto, testbed_instance, iface_guid, peer_iface_data)

def crossconnect_filter_peer_init(proto, testbed_instance, filter_guid, peer_data):
    filt = testbed_instance._elements[filter_guid]
    filt.peer_proto = proto
    crossconnect_tun_iface_peer_init(filt.peer_proto, testbed_instance, filt.iface_guid, peer_data)

def crossconnect_filter_peer_compl(proto, testbed_instance, filter_guid, peer_data):
    filt = testbed_instance._elements[filter_guid]
    filt.peer_proto = proto
    crossconnect_tun_iface_peer_compl(filt.peer_proto, testbed_instance, filt.iface_guid, peer_data)

def crossconnect_filter_peer_both(proto, testbed_instance, filter_guid, peer_data):
    crossconnect_filter_peer_init(proto, testbed_instance, iface_guid, peer_iface_data)
    crossconnect_filter_peer_compl(proto, testbed_instance, iface_guid, peer_iface_data)

def connect_dep(testbed_instance, node_guid, app_guid, node=None, app=None):
    node = node or testbed_instance._elements[node_guid]
    app = app or testbed_instance._elements[app_guid]
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
    
    if app.rpmFusion:
        node.rpmFusion = True

def connect_forwarder(testbed_instance, node_guid, fwd_guid):
    node = testbed_instance._elements[node_guid]
    fwd = testbed_instance._elements[fwd_guid]
    node.multicast_forwarder = fwd
    
    if fwd.router:
        connect_dep(testbed_instance, node_guid, None, app=fwd.router)

    connect_dep(testbed_instance, node_guid, fwd_guid)

def connect_router(testbed_instance, fwd_guid, router_guid):
    fwd = testbed_instance._elements[fwd_guid]
    router = testbed_instance._elements[router_guid]
    fwd.router = router
    
    if fwd.node:
        connect_dep(testbed_instance, None, router_guid, node=fwd.node)

def connect_node_netpipe(testbed_instance, node_guid, netpipe_guid):
    node = testbed_instance._elements[node_guid]
    netpipe = testbed_instance._elements[netpipe_guid]
    netpipe.node = node
    node.required_vsys.add('ipfw-be')
    node.required_packages.add('ipfwslice')
    

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
        vsys = element.routing_method(routes,
            testbed_instance.vsys_vnet)
        element.required_vsys.add(vsys)
    
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

def create_tunfilter(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_tun_filter(parameters)
    testbed_instance.elements[guid] = element

def create_classqueuefilter(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_class_queue_filter(parameters)
    testbed_instance.elements[guid] = element

def create_tosqueuefilter(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_tos_queue_filter(parameters)
    testbed_instance.elements[guid] = element

def create_application(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_application(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-app-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_ccnxdaemon(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_application(parameters,
            clazz  = testbed_instance._app.CCNxDaemon )
    
    # Just inject configuration stuff
    element.home_path = "nepi-ccnd-%s" % (guid,)
    
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

def create_multicast_forwarder(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_multicast_forwarder(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-mcfwd-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_multicast_announcer(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_multicast_announcer(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-mcann-%s" % (guid,)
    
    testbed_instance.elements[guid] = element

def create_multicast_router(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    element = testbed_instance._make_multicast_router(parameters)
    
    # Just inject configuration stuff
    element.home_path = "nepi-mcrt-%s" % (guid,)
    
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

def prestart_ccnxdaemon(testbed_instance, guid):
    # ccnx daemon needs to start before the rest of the
    # ccn applications
    start_application(testbed_instance, guid)

def stop_ccndaemon(testbed_instance, guid):
    app = testbed_instance.elements[guid]
    app.kill()

def start_application(testbed_instance, guid):
    parameters = testbed_instance._get_parameters(guid)
    traces = testbed_instance._get_traces(guid)
    app = testbed_instance.elements[guid]
    
    app.stdout = "stdout" in traces
    app.stderr = "stderr" in traces
    app.buildlog = "buildlog" in traces
    app.outout = "output" in traces
    
    app.start()

def stop_application(testbed_instance, guid):
    app = testbed_instance.elements[guid]
    app.kill()

### Status functions ###

def status_application(testbed_instance, guid):
    if guid not in testbed_instance.elements.keys():
        return AS.STATUS_NOT_STARTED
    
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
        element.tun_port = testbed_instance.tapPortBase + int(guid)

    # Set enabled traces
    traces = testbed_instance._get_traces(guid)
    for capmode in ('pcap', 'packets'):
        if capmode in traces:
            element.capture = capmode
            break
    else:
        element.capture = False
    
    # Do some validations
    element.validate()
    
    # First-phase setup
    element.prepare('tun-%s' % (guid,))

def postconfigure_tuniface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    
    # Second-phase setup
    element.launch()
    
def prestart_tuniface(testbed_instance, guid):
    element = testbed_instance._elements[guid]
    
    # Second-phase setup
    element.wait()

def configure_node(testbed_instance, guid):
    node = testbed_instance._elements[guid]
    
    # Just inject configuration stuff
    node.home_path = "nepi-node-%s" % (guid,)
    node.ident_path = testbed_instance.sliceSSHKey
    node.slicename = testbed_instance.slicename
    
    # Do some validations
    node.validate()
    
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
    
        vsys = testbed_instance.vsys_vnet
        
        node.configure_routes(routes, devs, vsys)

def configure_application(testbed_instance, guid):
    app = testbed_instance._elements[guid]
    
    # Do some validations
    app.validate()
    
    # Wait for dependencies
    app.node.wait_dependencies()
    
    # Install stuff
    app.async_setup()

def configure_dependency(testbed_instance, guid):
    dep = testbed_instance._elements[guid]
    
    # Do some validations
    dep.validate()
    
    # Wait for dependencies
    dep.node.wait_dependencies()
    
    # Install stuff
    dep.async_setup()

def configure_announcer(testbed_instance, guid):
    # Link ifaces
    fwd = testbed_instance._elements[guid]
    fwd.ifaces = [ dev
        for node_guid in testbed_instance.get_connected(guid, "node", "apps")
        for dev_guid in testbed_instance.get_connected(node_guid, "devs", "node")
        for dev in ( testbed_instance._elements.get(dev_guid) ,)
        if dev and isinstance(dev, testbed_instance._interfaces.TunIface)
            and dev.multicast ]
    
    # Install stuff
    configure_dependency(testbed_instance, guid)

def configure_forwarder(testbed_instance, guid):
    configure_announcer(testbed_instance, guid)
    
    # Link ifaces to forwarder
    fwd = testbed_instance._elements[guid]
    for iface in fwd.ifaces:
        iface.multicast_forwarder = '/var/run/mcastfwd'

def configure_router(testbed_instance, guid):
    # Link ifaces
    rt = testbed_instance._elements[guid]
    rt.nonifaces = [ dev
        for fwd_guid in testbed_instance.get_connected(guid, "fwd", "router")
        for node_guid in testbed_instance.get_connected(fwd_guid, "node", "apps")
        for dev_guid in testbed_instance.get_connected(node_guid, "devs", "node")
        for dev in ( testbed_instance._elements.get(dev_guid) ,)
        if dev and isinstance(dev, testbed_instance._interfaces.TunIface)
            and not dev.multicast ]
    
    # Install stuff
    configure_dependency(testbed_instance, guid)

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
    "router": dict({
                "help": "Connector to a routing daemon", 
                "name": "router",
                "max": 1, 
                "min": 0
            }),
    "fwd": dict({
                "help": "Forwarder this routing daemon communicates with", 
                "name": "fwd",
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
    "gre": dict({
                "help": "IP or Ethernet tunneling using the GRE protocol", 
                "name": "gre",
                "max": 1, 
                "min": 0
            }),
    "fd->": dict({
                "help": "TUN device file descriptor provider", 
                "name": "fd->",
                "max": 1, 
                "min": 0
            }),
    "->fd": dict({
                "help": "TUN device file descriptor slot", 
                "name": "->fd",
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
        "to":   (TESTBED_ID, (APPLICATION, CCNXDAEMON, MULTICASTANNOUNCER), "node"),
        "init_code": connect_dep,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, NODE, "deps"),
        "to":   (TESTBED_ID, (DEPENDENCY, NEPIDEPENDENCY, NS3DEPENDENCY), "node"),
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
        "from": (TESTBED_ID, NODE, "apps"),
        "to":   (TESTBED_ID, MULTICASTFORWARDER, "node"),
        "init_code": connect_forwarder,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, MULTICASTFORWARDER, "router"),
        "to":   (TESTBED_ID, MULTICASTROUTER, "fwd"),
        "init_code": connect_router,
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
        "from": (TESTBED_ID, TUNIFACE, "gre"),
        "to":   (TESTBED_ID, TUNIFACE, "gre"),
        "init_code": functools.partial(connect_tun_iface_peer,"gre"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNIFACE, "fd->"),
        "to":   (TESTBED_ID, TUNFILTERS, "->fd"),
        "init_code": connect_tun_iface_filter,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNFILTERS, "tcp"),
        "to":   (TESTBED_ID, TUNIFACE, "tcp"),
        "init_code": functools.partial(connect_filter_peer,"tcp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNFILTERS, "udp"),
        "to":   (TESTBED_ID, TUNIFACE, "udp"),
        "init_code": functools.partial(connect_filter_peer,"udp"),
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
        "from": (TESTBED_ID, TAPIFACE, "gre"),
        "to":   (TESTBED_ID, TAPIFACE, "gre"),
        "init_code": functools.partial(connect_tun_iface_peer,"gre"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPIFACE, "fd->"),
        "to":   (TESTBED_ID, TAPFILTERS, "->fd"),
        "init_code": connect_tun_iface_filter,
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPFILTERS, "tcp"),
        "to":   (TESTBED_ID, TAPIFACE, "tcp"),
        "init_code": functools.partial(connect_filter_peer,"tcp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPFILTERS, "udp"),
        "to":   (TESTBED_ID, TAPIFACE, "udp"),
        "init_code": functools.partial(connect_filter_peer,"udp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNFILTERS, "tcp"),
        "to":   (TESTBED_ID, TUNFILTERS, "tcp"),
        "init_code": functools.partial(connect_filter_filter,"tcp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TUNFILTERS, "udp"),
        "to":   (TESTBED_ID, TUNFILTERS, "udp"),
        "init_code": functools.partial(connect_filter_filter,"udp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPFILTERS, "tcp"),
        "to":   (TESTBED_ID, TAPFILTERS, "tcp"),
        "init_code": functools.partial(connect_filter_filter,"tcp"),
        "can_cross": False
    }),
    dict({
        "from": (TESTBED_ID, TAPFILTERS, "udp"),
        "to":   (TESTBED_ID, TAPFILTERS, "udp"),
        "init_code": functools.partial(connect_filter_filter,"udp"),
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
        "from": (TESTBED_ID, TUNIFACE, "gre"),
        "to":   (None, None, "gre"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_both,"gre"),
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
    # EGRE is an extension of PlanetLab, so we can't connect externally
    # if the other testbed isn't another PlanetLab
    dict({
        "from": (TESTBED_ID, TAPIFACE, "gre"),
        "to":   (TESTBED_ID, None, "gre"),
        "compl_code": functools.partial(crossconnect_tun_iface_peer_both,"gre"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, ALLFILTERS, "tcp"),
        "to":   (None, None, "tcp"),
        "init_code": functools.partial(crossconnect_filter_peer_init,"tcp"),
        "compl_code": functools.partial(crossconnect_filter_peer_compl,"tcp"),
        "can_cross": True
    }),
    dict({
        "from": (TESTBED_ID, ALLFILTERS, "udp"),
        "to":   (None, None, "udp"),
        "init_code": functools.partial(crossconnect_filter_peer_init,"udp"),
        "compl_code": functools.partial(crossconnect_filter_peer_compl,"udp"),
        "can_cross": True
    }),
]

attributes = dict({
    "forward_X11": dict({      
                "name": "forward_X11",
                "help": "Forward x11 from main namespace to the node",
                "type": Attribute.BOOL, 
                "value": False,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_bool,
            }),
    "hostname": dict({      
                "name": "hostname",
                "help": "Constrain hostname during resource discovery. May use wildcards.",
                "type": Attribute.STRING, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string,
            }),
    "city": dict({      
                "name": "city",
                "help": "Constrain location (city) during resource discovery. May use wildcards.",
                "type": Attribute.STRING, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string,
            }),
    "country": dict({      
                "name": "hostname",
                "help": "Constrain location (country) during resource discovery. May use wildcards.",
                "type": Attribute.STRING, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string,
            }),
    "region": dict({      
                "name": "hostname",
                "help": "Constrain location (region) during resource discovery. May use wildcards.",
                "type": Attribute.STRING, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string,
            }),
    "architecture": dict({      
                "name": "architecture",
                "help": "Constrain architexture during resource discovery.",
                "type": Attribute.ENUM, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "allowed": ["x86_64",
                            "i386"],
                "validation_function": validation.is_enum,
            }),
    "operating_system": dict({      
                "name": "operatingSystem",
                "help": "Constrain operating system during resource discovery.",
                "type": Attribute.ENUM, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
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
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "allowed": ["PLE",
                            "PLC",
                            "PLJ"],
                "validation_function": validation.is_enum,
            }),
    "min_reliability": dict({
                "name": "minReliability",
                "help": "Constrain reliability while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,100),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "max_reliability": dict({
                "name": "maxReliability",
                "help": "Constrain reliability while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,100),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "min_bandwidth": dict({
                "name": "minBandwidth",
                "help": "Constrain available bandwidth while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,2**31),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "max_bandwidth": dict({
                "name": "maxBandwidth",
                "help": "Constrain available bandwidth while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,2**31),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "min_load": dict({
                "name": "minLoad",
                "help": "Constrain node load average while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,2**31),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "max_load": dict({
                "name": "maxLoad",
                "help": "Constrain node load average while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,2**31),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "min_cpu": dict({
                "name": "minCpu",
                "help": "Constrain available cpu time while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,100),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
            }),
    "max_cpu": dict({
                "name": "maxCpu",
                "help": "Constrain available cpu time while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                "type": Attribute.DOUBLE,
                "range": (0,100),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_number,
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
    "if_name": dict({
                "name": "if_name",
                "help": "Device name",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
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
    "multicast":  dict({
                "name": "multicast", 
                "help": "Enable multicast forwarding on this device. "
                        "Note that you still need a multicast routing daemon "
                        "in the node.",
                "type": Attribute.BOOL,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "pointopoint":  dict({
                "name": "pointopoint", 
                "help": "If the interface is a P2P link, the remote endpoint's IP "
                        "should be set on this attribute.",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "bwlimit":  dict({
                "name": "bwlimit", 
                "help": "Emulated transmission speed (in kbytes per second)",
                "type": Attribute.INTEGER,
                "range" : (1,10*2**20),
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_integer
            }),
    "txqueuelen":  dict({
                "name": "txqueuelen", 
                "help": "Transmission queue length (in packets)",
                "type": Attribute.INTEGER,
                "value": 1000,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "range" : (1,10000),
                "validation_function": validation.is_integer
            }),
            
    "command": dict({
                "name": "command",
                "help": "Command line string",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "ccnroutes": dict({
                "name": "ccnRoutes",
                "help": "Route can be static (e.g. udp ip) or multicast (e.g. udp 224.0.0.204 2869). To separate different route use '|' ",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
     "sudo": dict({
                "name": "sudo",
                "help": "Run with root privileges",
                "type": Attribute.BOOL,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "stdin": dict({
                "name": "stdin",
                "help": "Standard input",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
            
    "depends": dict({
                "name": "depends",
                "help": "Space-separated list of packages required to run the application",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "build-depends": dict({
                "name": "buildDepends",
                "help": "Space-separated list of packages required to build the application",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "rpm-fusion": dict({
                "name": "rpmFusion",
                "help": "True if required packages can be found in the RpmFusion repository",
                "type": Attribute.BOOL,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "value": False,
                "validation_function": validation.is_bool
            }),
    "sources": dict({
                "name": "sources",
                "help": "Space-separated list of regular files to be deployed in the working path prior to building. "
                        "Archives won't be expanded automatically.",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "ccnxversion": dict({      
                "name": "ccnxVersion",
                "help": "Version of ccnx source code to install in the node.",
                "type": Attribute.ENUM, 
                "value": "ccnx-0.6.0",
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "allowed": ["ccnx-0.6.0",
                            "ccnx-0.5.1"],
                "validation_function": validation.is_enum,
            }),
     "ccnlocalport" : dict({
            "name" : "ccnLocalPort", 
            "help" : "Local port to bind the ccn daemon. (i.e. CCN_LOCAL_PORT=)",
            "type" : Attribute.INTEGER,
            "flags" : Attribute.DesignInvisible | \
                    Attribute.ExecInvisible | \
                    Attribute.ExecImmutable | \
                    Attribute.Metadata,
            "validation_function" : validation.is_integer,
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
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
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
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    
    "netpipe_mode": dict({      
                "name": "mode",
                "help": "Link mode:\n"
                        " * SERVER: applies to incoming connections\n"
                        " * CLIENT: applies to outgoing connections\n"
                        " * SERVICE: applies to both",
                "type": Attribute.ENUM, 
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
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
                "validation_function": validation.is_number,
            }),
    "bw_out":  dict({
                "name": "bwOut", 
                "help": "Outbound bandwidth limit (in Mbit/s)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_number,
            }),
    "plr_in":  dict({
                "name": "plrIn", 
                "help": "Inbound packet loss rate (0 = no loss, 1 = 100% loss)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_number,
            }),
    "plr_out":  dict({
                "name": "plrOut", 
                "help": "Outbound packet loss rate (0 = no loss, 1 = 100% loss)",
                "type": Attribute.DOUBLE,
                "validation_function": validation.is_number,
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
    "module": dict({
                "name": "module",
                "help": "Path to a .c or .py source for a filter module, or a binary .so",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "args": dict({
                "name": "args",
                "help": "Module arguments - comma-separated list of name=value pairs",
                "type": Attribute.STRING,
                "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
                "validation_function": validation.is_string
            }),
    "routing_algorithm": dict({      
            "name": "algorithm",
            "help": "Routing algorithm.",
            "value": "dvmrp",
            "type": Attribute.ENUM, 
            "allowed": ["dvmrp"],
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_enum,
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
    "pcap": dict({
                "name": "pcap",
                "help": "PCAP trace of all packets going through the interface",
              }),
    "output": dict({
                "name": "output",
                "help": "Extra output trace for applications. When activated this trace can be referenced with wildcard a reference from an Application command line. Ex: command: 'tcpdump -w {#[elemet-label].trace[trace-id].[name|path]#}' ",
              }),
    "dropped_stats": dict({
                "name": "dropped_stats",
                "help": "Information on dropped packets on a filer or queue associated to a network interface",
            }),
    })

create_order = [ 
    INTERNET, NODE, NODEIFACE, CLASSQUEUEFILTER, TOSQUEUEFILTER, 
    MULTICASTANNOUNCER, MULTICASTFORWARDER, MULTICASTROUTER, 
    TUNFILTER, TAPIFACE, TUNIFACE, NETPIPE, 
    NEPIDEPENDENCY, NS3DEPENDENCY, DEPENDENCY, CCNXDAEMON, APPLICATION ]

configure_order = [ 
    INTERNET, Parallel(NODE), 
    NODEIFACE, 
    Parallel(MULTICASTANNOUNCER), Parallel(MULTICASTFORWARDER), Parallel(MULTICASTROUTER), 
    Parallel(TAPIFACE), Parallel(TUNIFACE), NETPIPE, 
    Parallel(NEPIDEPENDENCY), Parallel(NS3DEPENDENCY), Parallel(DEPENDENCY), Parallel(CCNXDAEMON),
    Parallel(APPLICATION)]

# Start (and prestart) node after ifaces, because the node needs the ifaces in order to set up routes
start_order = [ INTERNET, 
    NODEIFACE, 
    Parallel(TAPIFACE), Parallel(TUNIFACE), 
    Parallel(NODE), NETPIPE, 
    Parallel(MULTICASTANNOUNCER), Parallel(MULTICASTFORWARDER), Parallel(MULTICASTROUTER), 
    Parallel(NEPIDEPENDENCY), Parallel(NS3DEPENDENCY), Parallel(DEPENDENCY), Parallel(CCNXDAEMON),
    Parallel(APPLICATION)]

# cleanup order
shutdown_order = [ 
    Parallel(APPLICATION), 
    Parallel (CCNXDAEMON),
    Parallel(MULTICASTROUTER), Parallel(MULTICASTFORWARDER), Parallel(MULTICASTANNOUNCER), 
    Parallel(TAPIFACE), Parallel(TUNIFACE), Parallel(NETPIPE), 
    Parallel(NEPIDEPENDENCY), Parallel(NS3DEPENDENCY), Parallel(DEPENDENCY), 
    NODEIFACE, Parallel(NODE) ]

factories_info = dict({
    NODE: dict({
            "help": "Virtualized Node (V-Server style)",
            "category": FC.CATEGORY_NODES,
            "create_function": create_node,
            "preconfigure_function": configure_node,
            "prestart_function": configure_node_routes,
            "box_attributes": [
                "forward_X11",
                "hostname",
                "architecture",
                "operating_system",
                "site",
                "min_reliability",
                "max_reliability",
                "min_bandwidth",
                "max_bandwidth",
                "min_load",
                "max_load",
                "min_cpu",
                "max_cpu",
                
                # NEPI-in-NEPI attributes
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,
            ],
            "connector_types": ["devs", "apps", "pipes", "deps"],
            "tags": [tags.NODE, tags.ALLOW_ROUTES],
       }),
    NODEIFACE: dict({
            "help": "External network interface - they cannot be brought up or down, and they MUST be connected to the internet.",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create_nodeiface,
            "preconfigure_function": configure_nodeiface,
            "box_attributes": [ ],
            "connector_types": ["node", "inet"],
            "tags": [tags.INTERFACE, tags.HAS_ADDRESSES],
        }),
    TUNIFACE: dict({
            "help": "Virtual TUN network interface (layer 3)",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create_tuniface,
            "preconfigure_function": preconfigure_tuniface,
            "configure_function": postconfigure_tuniface,
            "prestart_function": prestart_tuniface,
            "box_attributes": [
                "up", "if_name", "mtu", "snat", "pointopoint", "multicast", "bwlimit",
                "txqueuelen",
                "tun_proto", "tun_addr", "tun_port", "tun_key", "tun_cipher",
            ],
            "traces": ["packets", "pcap"],
            "connector_types": ["node","udp","tcp","fd->","gre"],
            "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
        }),
    TAPIFACE: dict({
            "help": "Virtual TAP network interface (layer 2)",
            "category": FC.CATEGORY_DEVICES,
            "create_function": create_tapiface,
            "preconfigure_function": preconfigure_tuniface,
            "configure_function": postconfigure_tuniface,
            "prestart_function": prestart_tuniface,
            "box_attributes": [
                "up", "if_name", "mtu", "snat", "pointopoint", "multicast", "bwlimit",
                "txqueuelen",
                "tun_proto", "tun_addr", "tun_port", "tun_key", "tun_cipher",
            ],
            "traces": ["packets", "pcap"],
            "connector_types": ["node","udp","tcp","fd->","gre"],
            "tags": [tags.INTERFACE, tags.ALLOW_ADDRESSES],
        }),
    TUNFILTER: dict({
            "help": "TUN/TAP stream filter\n\n"
                    "If specified, it should be either a .py or .so module. "
                    "It will be loaded, and all incoming and outgoing packets "
                    "will be routed through it. The filter will not be responsible "
                    "for buffering, packet queueing is performed in tun_connect "
                    "already, so it should not concern itself with it. It should "
                    "not, however, block in one direction if the other is congested.\n"
                    "\n"
                    "Modules are expected to have the following methods:\n"
                    "\tinit(**args)\n"
                    "\t\tIf arguments are given, this method will be called with the\n"
                    "\t\tgiven arguments (as keyword args in python modules, or a single\n"
                    "\taccept_packet(packet, direction):\n"
                    "\t\tDecide whether to drop the packet. Direction is 0 for packets "
                        "coming from the local side to the remote, and 1 is for packets "
                        "coming from the remote side to the local. Return a boolean, "
                        "true if the packet is not to be dropped.\n"
                    "\tfilter_init():\n"
                    "\t\tInitializes a filtering pipe (filter_run). It should "
                        "return two file descriptors to use as a bidirectional "
                        "pipe: local and remote. 'local' is where packets from the "
                        "local side will be written to. After filtering, those packets "
                        "should be written to 'remote', where tun_connect will read "
                        "from, and it will forward them to the remote peer. "
                        "Packets from the remote peer will be written to 'remote', "
                        "where the filter is expected to read from, and eventually "
                        "forward them to the local side. If the file descriptors are "
                        "not nonblocking, they will be set to nonblocking. So it's "
                        "better to set them from the start like that.\n"
                    "\tfilter_run(local, remote):\n"
                    "\t\tIf filter_init is provided, it will be called repeatedly, "
                        "in a separate thread until the process is killed. It should "
                        "sleep at most for a second.\n"
                    "\tfilter_close(local, remote):\n"
                    "\t\tCalled then the process is killed, if filter_init was provided. "
                        "It should, among other things, close the file descriptors.\n"
                    "\n"
                    "Python modules are expected to return a tuple in filter_init, "
                    "either of file descriptors or file objects, while native ones "
                    "will receive two int*.\n"
                    "\n"
                    "Python modules can additionally contain a custom queue class "
                    "that will replace the FIFO used by default. The class should "
                    "be named 'queueclass' and contain an interface compatible with "
                    "collections.deque. That is, indexing (especiall for q[0]), "
                    "bool(q), popleft, appendleft, pop (right), append (right), "
                    "len(q) and clear.",
            "category": FC.CATEGORY_CHANNELS,
            "create_function": create_tunfilter,
            "box_attributes": [
                "module", "args",
                "tun_proto", "tun_addr", "tun_port", "tun_key", "tun_cipher",
            ],
            "connector_types": ["->fd","udp","tcp"],
        }),
    CLASSQUEUEFILTER : dict({
            "help": "TUN classfull queue, uses a separate queue for each user-definable class.\n\n"
                    "It takes two arguments, both of which have sensible defaults:\n"
                    "\tsize: the base size of each class' queue\n"
                    "\tclasses: the class definitions, which follow the following syntax:\n"
                    '\t   <CLASSLIST> ::= <CLASS> ":" CLASSLIST\n'
                    '\t                |  <CLASS>\n'
                    '\t   <CLASS>     ::= <PROTOLIST> "*" <PRIORITYSPEC>\n'
                    '\t                |  <DFLTCLASS>\n'
                    '\t   <DFLTCLASS> ::= "*" <PRIORITYSPEC>\n'
                    '\t   <PROTOLIST> ::= <PROTO> "." <PROTOLIST>\n'
                    '\t                |  <PROTO>\n'
                    '\t   <PROTO>     ::= <NAME> | <NUMBER>\n'
                    '\t   <NAME>      ::= --see http://en.wikipedia.org/wiki/List_of_IP_protocol_numbers --\n'
                    '\t                   --only in lowercase, with special characters removed--\n'
                    '\t                   --or see below--\n'
                    '\t   <NUMBER>    ::= [0-9]+\n'
                    '\t   <PRIORITYSPEC> ::= <THOUGHPUT> [ "#" <SIZE> ] [ "p" <PRIORITY> ]\n'
                    '\t   <THOUGHPUT> ::= NUMBER -- default 1\n'
                    '\t   <PRIORITY>  ::= NUMBER -- default 0\n'
                    '\t   <SIZE>      ::= NUMBER -- default 1\n'
                    "\n"
                    "Size, thoughput and priority are all relative terms. "
                    "Sizes are multipliers for the size argument, thoughput "
                    "is applied relative to other classes and the same with "
                    "priority.",
            "category": FC.CATEGORY_CHANNELS,
            "create_function": create_classqueuefilter,
            "box_attributes": [
                "args",
                "tun_proto", "tun_addr", "tun_port", "tun_key", "tun_cipher",
            ],
            "connector_types": ["->fd","udp","tcp"],
            "traces": ["dropped_stats"],
        }),
    TOSQUEUEFILTER : dict({
            "help": "TUN classfull queue that classifies according to the TOS (RFC 791) IP field.\n\n"
                    "It takes a size argument that specifies the size of each class. As TOS is a "
                    "subset of DiffServ, this queue half-implements DiffServ.",
            "category": FC.CATEGORY_CHANNELS,
            "create_function": create_tosqueuefilter,
            "box_attributes": [
                "args",
                "tun_proto", "tun_addr", "tun_port", "tun_key", "tun_cipher",
            ],
            "connector_types": ["->fd","udp","tcp"],
        }),

    APPLICATION: dict({
            "help": "Generic executable command line application",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_application,
            "start_function": start_application,
            "status_function": status_application,
            "stop_function": stop_application,
            "configure_function": configure_application,
            "box_attributes": ["command", "sudo", "stdin",
                               "depends", "build-depends", "build", "install",
                               "sources", "rpm-fusion" ],
            "connector_types": ["node"],
            "traces": ["stdout", "stderr", "buildlog", "output"],
            "tags": [tags.APPLICATION],
        }),

    CCNXDAEMON: dict({
            "help": "CCNx daemon",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_ccnxdaemon,
            "prestart_function": prestart_ccnxdaemon,
            "status_function": status_application,
            "stop_function": stop_application,
            "configure_function": configure_application,
            "box_attributes": ["ccnroutes", "build", "ccnlocalport",
                "install", "ccnxversion", "sources"],
            "connector_types": ["node"],
            "traces": ["stdout", "stderr", "buildlog", "output"],
            "tags": [tags.APPLICATION],
        }),
    DEPENDENCY: dict({
            "help": "Requirement for package or application to be installed on some node",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_dependency,
            "preconfigure_function": configure_dependency,
            "box_attributes": ["depends", "build-depends", "build", "install",
                               "sources", "rpm-fusion" ],
            "connector_types": ["node"],
            "traces": ["buildlog"],
        }),
    NEPIDEPENDENCY: dict({
            "help": "Requirement for NEPI inside NEPI - required to run testbed instances inside a node",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_nepi_dependency,
            "preconfigure_function": configure_dependency,
            "box_attributes": [],
            "connector_types": ["node"],
            "traces": ["buildlog"],
        }),
    NS3DEPENDENCY: dict({
            "help": "Requirement for NS3 inside NEPI - required to run NS3 testbed instances inside a node. It also needs NepiDependency.",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_ns3_dependency,
            "preconfigure_function": configure_dependency,
            "box_attributes": [ ],
            "connector_types": ["node"],
            "traces": ["buildlog"],
        }),
    MULTICASTFORWARDER: dict({
            "help": "This application installs a userspace packet forwarder "
                    "that, when connected to a node, filters all packets "
                    "flowing through multicast-capable virtual interfaces "
                    "and applies custom-specified routing policies.",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_multicast_forwarder,
            "preconfigure_function": configure_forwarder,
            "start_function": start_application,
            "status_function": status_application,
            "stop_function": stop_application,
            "box_attributes": [ ],
            "connector_types": ["node","router"],
            "traces": ["buildlog","stderr"],
        }),
    MULTICASTANNOUNCER: dict({
            "help": "This application installs a userspace daemon that "
                    "monitors multicast membership and announces it on all "
                    "multicast-capable interfaces.\n"
                    "This does not usually happen automatically on PlanetLab slivers.",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_multicast_announcer,
            "preconfigure_function": configure_announcer,
            "start_function": start_application,
            "status_function": status_application,
            "stop_function": stop_application,
            "box_attributes": [ ],
            "connector_types": ["node"],
            "traces": ["buildlog","stderr"],
        }),
    MULTICASTROUTER: dict({
            "help": "This application installs a userspace daemon that "
                    "monitors multicast membership and announces it on all "
                    "multicast-capable interfaces.\n"
                    "This does not usually happen automatically on PlanetLab slivers.",
            "category": FC.CATEGORY_APPLICATIONS,
            "create_function": create_multicast_router,
            "preconfigure_function": configure_router,
            "start_function": start_application,
            "status_function": status_application,
            "stop_function": stop_application,
            "box_attributes": ["routing_algorithm"],
            "connector_types": ["fwd"],
            "traces": ["buildlog","stdout","stderr"],
        }),
    INTERNET: dict({
            "help": "Internet routing",
            "category": FC.CATEGORY_CHANNELS,
            "create_function": create_internet,
            "connector_types": ["devs"],
            "tags": [tags.INTERNET],
        }),
    NETPIPE: dict({
            "help": "Link emulation",
            "category": FC.CATEGORY_CHANNELS,
            "create_function": create_netpipe,
            "configure_function": configure_netpipe,
            "box_attributes": ["netpipe_mode",
                               "addr_list", "port_list",
                               "bw_in","plr_in","delay_in",
                               "bw_out","plr_out","delay_out"],
            "connector_types": ["node"],
            "traces": ["netpipe_stats"],
        }),
})

testbed_attributes = dict({
        "slice_hrn": dict({
            "name": "sliceHrn",
            "help": "The hierarchical Resource Name (HRN) for the PlanetLab slice.",
            "type": Attribute.STRING,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.NoDefaultValue,
            "validation_function": validation.is_string
        }),
        "sfa": dict({
            "name": "sfa",
            "help": "Activates the use of SFA for node reservation.",
            "type": Attribute.BOOL,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.NoDefaultValue,
            "validation_function": validation.is_bool
        }),
        "slice": dict({
            "name": "slice",
            "help": "The name of the PlanetLab slice to use",
            "type": Attribute.STRING,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.NoDefaultValue,
            "validation_function": validation.is_string
        }),
        "auth_user": dict({
            "name": "authUser",
            "help": "The name of the PlanetLab user to use for API calls - it must have at least a User role.",
            "type": Attribute.STRING,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.NoDefaultValue,
            "validation_function": validation.is_string
        }),
        "auth_pass": dict({
            "name": "authPass",
            "help": "The PlanetLab user's password.",
            "type": Attribute.STRING,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.NoDefaultValue,
            "validation_function": validation.is_string
        }),
        "plc_host": dict({
            "name": "plcHost",
            "help": "The PlanetLab PLC API host",
            "type": Attribute.STRING,
            "value": "www.planet-lab.eu",
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_string
        }),
        "plc_url": dict({
            "name": "plcUrl",
            "help": "The PlanetLab PLC API url pattern - %(hostname)s is replaced by plcHost.",
            "type": Attribute.STRING,
            "value": "https://%(hostname)s:443/PLCAPI/",
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_string
        }),
        "p2p_deployment": dict({
            "name": "p2pDeployment",
            "help": "Enable peer-to-peer deployment of applications and dependencies. "
                    "When enabled, dependency packages and applications are "
                    "deployed in a P2P fashion, picking a single node to do "
                    "the building or repo download, while all the others "
                    "cooperatively exchange resulting binaries or rpms. "
                    "When deploying to many nodes, this is a far more efficient "
                    "use of resources. It does require re-encrypting and distributing "
                    "the slice's private key. Though it is implemented in a secure "
                    "fashion, if they key's sole purpose is not PlanetLab, then this "
                    "feature should be disabled.",
            "type": Attribute.BOOL,
            "value": True,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_bool
        }),
        "slice_ssh_key": dict({
            "name": "sliceSSHKey",
            "help": "The controller-local path to the slice user's ssh private key. "
                    "It is the user's responsability to deploy this file where the controller "
                    "will run, it won't be done automatically because it's sensitive information. "
                    "It is recommended that a NEPI-specific user be created for this purpose and "
                    "this purpose alone.",
            "type": Attribute.STRING,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable | Attribute.NoDefaultValue,
            "validation_function": validation.is_string
        }),
        "pl_log_level": dict({      
            "name": "plLogLevel",
            "help": "Verbosity of logging of planetlab events.",
            "value": "ERROR",
            "type": Attribute.ENUM, 
            "allowed": ["DEBUG",
                        "INFO",
                        "WARNING",
                        "ERROR",
                        "CRITICAL"],
            "validation_function": validation.is_enum,
        }),
        "tap_port_base":  dict({
            "name": "tapPortBase", 
            "help": "Base port to use when connecting TUN/TAPs. Effective port will be BASE + GUID.",
            "type": Attribute.INTEGER,
            "value": 15000,
            "range": (2000,30000),
            "validation_function": validation.is_integer_range(2000,30000)
        }),
        "clean_proc": dict({
            "name": "cleanProc",
            "help": "Set to True if the slice will be dedicated to this experiment. "
                    "NEPI will perform node and slice process cleanup, making sure slices are "
                    "in a clean, repeatable state before running the experiment.",
            "type": Attribute.BOOL,
            "value": False,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_bool
        }),
        "clean_home": dict({
            "name": "cleanHome",
            "help": "Set to True all preexistent directories in the home "
                    "directory of each sliver will be removed before the "
                    "start of the experiment.",
            "type": Attribute.BOOL,
            "value": False,
            "flags": Attribute.ExecReadOnly | Attribute.ExecImmutable,
            "validation_function": validation.is_bool
        }),
    })

supported_recovery_policies = [
        DC.POLICY_FAIL,
        DC.POLICY_RESTART,
        DC.POLICY_RECOVER,
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

    @property
    def testbed_id(self):
        return TESTBED_ID

    @property
    def testbed_version(self):
        return TESTBED_VERSION

    @property
    def supported_recovery_policies(self):
        return supported_recovery_policies


