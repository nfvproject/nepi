#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core import testbed

CREATE = 0
SET = 1
CONNECT = 2
ADD_TRACE = 3
ADD_ADDRESS = 4
ADD_ROUTE = 5

class TestbedConfiguration(testbed.TestbedConfiguration):
    pass

class TestbedInstance(testbed.TestbedInstance):
    def __init__(self, configuration):
        self._netns = self._load_netns_module(configuration)
        self._elements = dict()
        self._configuration = configuration
        self._instructions = dict({
            CREATE: dict(),
            SET: dict(),
            CONNECT: dict(),
            ADD_TRACE: dict(),
            ADD_ADDRESS: dict(),
            ADD_ROUTE: dict()
        })
        self._factories = dict({
            "Node": list(),
            "P2PInterface": list(),
            "TapNodeInterface": list(),
            "NodeInterface": list(),
            "Switch": list(),
            "Application": list()
        })
        self._connections = list()

    def create(self, guid, factory_id):
        if guid in self._instructions[CREATE]:
            # XXX: Validation
            raise RuntimeError("cannot add two elements with the same guid")
        if factory_id not in self._factories:
            # XXX: Validation
            raise RuntimeError("%s is not an allowed factory_id" % factory_id)
        self._instructions[CREATE][guid] = factory_id
        self._factories[factory_id].append(guid)

    def create_set(self, guid, name, value):
        if guid not in self._instructions[SET]:
            self._instructions[SET][guid] = dict()
        self._instructions[SET][guid][name] = value
       
    def connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2):
        if not guid1 in self._instructions[CONNECT]:
            self._instructions[CONNECT] = dict()
        if not connector_type_name1 in self._instructions[CONNECT][guid1]:
             self._instructions[CONNECT][guid1][connector_type_name1] = dict()
        self._instructions[CONNECT][guid1][connector_type_name1][guid2] = \
                connector_type_name2
        self._connections.append((guid1, connector_type_name1, guid2, 
            connector_type_name2))

    def add_trace(self, guid, trace_id):
        if not guid in self._instructions[ADD_TRACE]:
            self._instructions[ADD_TRACE][guid] = list()
        self._instructions[ADD_TRACE][guid].append(trace_id)

    def add_adddress(self, guid, family, address, netprefix, broadcast):
        if not guid in self._instructions[ADD_ADDRESS]:
            self._instructions[ADD_ADDRESS][guid] = list()
        self._instructions[ADD_ADDRESS][guid].append((guid, family, address, 
                netprefix, broadcast))

    def add_route(self, guid, family, destination, netprefix, nexthop, 
            interface):
        if not guid in self._instructions[ADD_ROUTE]:
            self._instructions[ADD_ROUTE][guid] = list()
        self._instructions[ADD_ROUTE][guid].append((family, destination, 
                netprefix, nexthop, interface)) 

    def do_create(self):
        # nodes need to be created first
        factories_order = ["Node", "P2PInterface", "TapNodeInterface", 
                "NodeInterface", "Switch", "Application"]
        for guid in self._factories[factory_id] \
                for factory_id in factories_order:
            self._create_element(guid, factory_id)
        # free self._factories as it is not going to be used further
        # TODO: Check if this methods frees everithing... 
        # maybe there are still some references!
        self._factories = None

    def do_connect(self):
        cross_connections = list()
        for (guid1, connector_type_name1, guid2, connector_type_name2) \
                in self._connections:
            if guid1 not in self._elements or guid2 not in self._elements:
                # at least one of the elements does not belong to this
                # TestbedIntsance and so it needs to be treated as a cross 
                # testbed connection
                cross_connections.append(guid1, connector_type_name1, guid2,
                        connector_type_name2)
            else:
                # TODO: do Whatever is needed to connect
                pass
        self._connections = cross_connections

    def do_configure(self):
        raise NotImplementedError
        #self._object.add_route(
        #            prefix = destination, 
        #            prefix_len = netprefix, 
        #            nexthop = nexthop)

    def do_cross_connect(self):
        for (guid1, connector_type_name1, guid2, connector_type_name2) \
                in self._connections:
            # TODO: do Whatever is needed to connect
            pass
        # free connections list as is not going to be used further
        self._connections = None

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError

    def start(self, time):
        raise NotImplementedError

    def action(self, time, guid, action):
        raise NotImplementedError

    def stop(self, time):
        raise NotImplementedError

    def status(self, guid):
        raise NotImplementedError

    def trace(self, guid, trace_id):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def _netns_module(self, configuration):
        # TODO: Do something with the configuration!!!
        import sys
        __import__("netns")
        return sys.modules["netns"]

    def _create_element(self, guid, factory_id):
        paremeters = dict()
        if guid in self._instructions[SET]:
            parameters = self._instructions[SET][guid] 
        if guid not in self._elements.keys():
            if factory_id == "Node":
                self._create_node_element(guid, parameters)
            elif factory_id == "P2PInterface":
                self._create_p2piface_element(guid, parameters)
        self._set_attributes(guid, parameters)

    def _create_node_element(self, guid, parameters):
        forward_X11 = False
        if "forward_X11" in paremeters:
            forward_X11 = parameters["forward_X11"]
            del parameters["forward_X11"]
        element = self._netns.Node(forward_X11 = forward_X11)
        self._elements[guid] = element

    def _create_p2piface_element(self, guid, parameters):
                # search in the connections the node asociated with this
                # P2PInterface and the other P2PInterface to which it is 
                # connected
                connection = 
                node1 = 
                node2 = 
                element1, element2 = self._netns.P2PInterface.create_pair(
                        node1, node2)
                self._elements[guid] = element1
                self._elements[guid2] = element2

    def _set_attributes(self, guid, paramenters):
        for name, value in parameters:
            # TODO: Validate attribute does not exist!!!
            setattr(element, name, value)

def connect_switch(switch_connector, interface_connector):
    switch = switch_connector.container_element
    interface = interface_connector.container_element
    if switch.is_installed() and interface.is_installed():
        switch._object.connect(interface._object)
        return True
    return False
   
#XXX: This connection function cannot be use to transfer a file descriptor
# to a remote tap device
def connect_fd_local(tap_connector, fdnd_connector):
    tap = tap_connector.container_element
    fdnd = fdnd_connector.container_element
    if fdnd.is_installed() and tap.is_installed():
        socket = tap.server.modules.socket
        passfd = tap.server.modules.passfd
        fd = tap.file_descriptor
        address = fdnd.socket_address
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.connect(address)
        passfd.sendfd(sock, fd, '0')
        # TODO: after succesful transfer, the tap device should close the fd
        return True
    return False

connections = [
    dict({
        'from' : [ "netns", "Node", "devs" ],
        'to' :   [ "netns", "P2PInterface", "node" ],
        'code' : do_nothing,
        'can_cross' : False
    }),
    dict({
        'from' : [ "netns", "Node", "devs" ],
        'to' :   [ "netns", "TapNodeInterface", "node" ],
        'code' : do_nothing,
        'can_cross' : False
    }),
    dict({
        'from' : [ "netns", "Node", "devs" ],
        'to' :   [ "netns", "NodeInterface", "node" ],
        'code' : do_nothing,
        'can_cross' : False
    }),
    dict({
        'from' : [ "netns", "P2PInterface", "p2p" ],
        'to' :   [ "netns", "P2PInterface", "p2p" ],
        'code' : do_nothing,
        'can_cross' : False
    }),
    dict({
        'from' : [ "netns", "TapNodeInterface", "fd" ],
        'to' :   [ "ns3", "ns3::FileDescriptorNetDevice", "fd" ],
        'code' : connect_fd_local,
        'can_cross' : True
    }),
     dict({
        'from' : [ "netns", "Switch", "devs" ],
        'to' :   [ "netns", "NodeInterface", "switch" ],
        'code' : connect_switch,
        'can_cross' : False
    }),
    dict({
        'from' : [ "netns", "Node", "apps" ],
        'to' :   [ "netns", "Application", "node" ],
        'code' : do_nothing,
        'can_cross' : False
    })
]

class TapNodeInterface(object):
    def __init__(self):
        # GET THE NODE!
        self._object = node._object.add_tap()

class NodeInterface(object):
    def __init__(self):
        # GET NODE
        self._object = n.add_if()

class Switch(Topo_ChannelMixin, NetnsElement):
    def __init__(self, factory, server, container = None):
        self._object = self.server.modules.netns.Switch()

class NetnsApplication(NetnsElement):
    def __init__(self, factory, server, container = None):
        super(NetnsApplication, self).__init__(factory, server, container)
        # attributes
        self.add_string_attribute(name = "command",
            help = "Command name")
        self.add_string_attribute(name = "user",
            help = "system user")
        self.add_string_attribute(name = "stdin",
            help = "Standard input")
        #traces
        stdout = StdTrace(
                name='StdoutTrace',
                help='Application standard output',
                filename='stdout.txt',
                element=self)
        stderr = StdTrace(
                name='StderrTrace',
                help='Application standard error',
                filename='stderr.txt',
                element=self)
        self._add_trace(stdout)
        self._add_trace(stderr)
 
    def start(self):
        user = self.get_attribute("user").value

        stdin = stdout = stderr = None
        if self.get_attribute('stdin').value:
            filename = self.get_attribute('stdin')
            stdin = self.server.modules.__builtin__.open(filename, 'rb')

        trace = self.get_trace("StdoutTrace")
        if trace.is_enabled:
            filename = trace.real_filepath
            stdout = self.server.modules.__builtin__.open(filename, 'wb')

        trace = self.get_trace("StderrTrace")
        if trace.is_enabled:
            filename = trace.real_filepath
            stderr = self.server.modules.__builtin__.open(filename, 'wb')

        cnctr = self.connector("node")
        node = iter(cnctr.connections).next().get_other(cnctr)\
            .container_element
        force_install(node)    
        n = node._object
        command = self.get_attribute('command').value
        targets = re.findall(r"%target:(.*?)%", command)
        for target in targets:
            try:
                (family, address, port) = resolve_netref(target, AF_INET, 
                    self.server.experiment )
                command = command.replace("%%target:%s%%" % target, address.address)
            except:
                continue

        self._object  = n.Popen(command, shell = True,  stdout = stdout, stdin = stdin,
            stderr = stderr, user = user)

    def is_completed(self):
        if self._object is not None:
            returncode = self._object.poll()
            if returncode is not None:
                return True
        return False

class StdTrace(Trace):
    def install(self):
        pass

    @property
    def real_filepath(self):
        filename = self.get_attribute("Filename").value
        return self.element.server.get_trace_filepath(filename)

    def read_trace(self):
        filename = self.get_attribute("Filename").value
        return self.element.server.read_trace(filename)

def force_install(object):
    if not object.is_installed():
        object.install()

