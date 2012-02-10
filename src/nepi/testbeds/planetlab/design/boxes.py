
from attributes import *

from nepi.util import TESTBED_ENVIRONMENT_SETUP 
from nepi.design import attributes, connectors, tags
from nepi.design.boxes import TestbedBox, Box, IPAddressBox, ContainerBox, TunnelBox

TESTBED_ID = "planetlab"

SLICE = "pl::Slice"
CONTAINER = "pl::Container"

PACKETTRACE = "pl::PacketTrace"
PCAPTRACE = "pl::PcapTrace"
DROPSTATTRACE = "pl::DropStatTrace"
BUILDLOGTRACE = "pl::BuildLogTrace"
STDERRTRACE = "pl::StderrTrace"
STDOUTTRACE = "pl::StdoutTrace"
OUTPUTTRACE = "pl::OutputTRace"

NODE = "pl::Node"
NODEIFACE = "pl::NodeInterface"
TUNIFACE = "pl::TunInterface"
TAPIFACE = "pl::TapInterface"
APPLICATION = "pl::Application"
DEPENDENCY = "pl::Dependency"
NEPIDEPENDENCY = "pl::NepiDependency"
NS3DEPENDENCY = "pl::NS3Dependency"
INTERNET = "pl::Internet"
NETPIPE = "pl::NetPipe"
TUNFILTER = "plTunFilter"
CLASSQUEUEFILTER = "pl::ClassQueueFilter"
TOSQUEUEFILTER = "pl::TosQueueFilter"
MULTICASTFORWARDER = "pl::MulticastForwarder"
MULTICASTANNOUNCER = "pl::MulticastAnnouncer"
MULTICASTROUTER = "pl::MulticastRouter"

TUNFILTERS = (TUNFILTER, CLASSQUEUEFILTER, TOSQUEUEFILTER)
TAPFILTERS = (TUNFILTER, )
ALLFILTERS = (TUNFILTER, CLASSQUEUEFILTER, TOSQUEUEFILTER)

ADDRESS = "pl::IPv4Address"

boxes = list()

############ CONTROLLER #############

box = TestbedBox(TESTBED_ID, SLICE, help = "PlanetLab slice instance.")
boxes.append(box)

box.add_attr(
    attributes.StringAttribute(
        "sliceHrn",
        "The hierarchical Resource Name (HRN) for the PlanetLab slice.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        )
    )

box.add_attr(
    attributes.BoolAttribute(
        "sfa",
        "Activates the use of SFA for node reservation.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        default_value = False
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "slice",
        "The name of the PlanetLab slice to use",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "authUser",
        "The name of the PlanetLab user to use for API calls - it must have at least a User role.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "authPass",
        "The PlanetLab user's password.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "plcHost",
        "The PlanetLab PLC API host",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = "www.planet-lab.eu"
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "plcUrl",
        "The PlanetLab PLC API url pattern - %(hostname)s is replaced by plcHost.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = "https://%(hostname)s:443/PLCAPI/"
        )
    )

box.add_attr(
    attributes.BoolAttribute(
        "p2pDeployment",
        "Enable peer-to-peer deployment of applications and dependencies. When enabled, dependency packages and applications are deployed in a P2P fashion, picking a single node to do the building or repo download, while all the others cooperatively exchange resulting binaries or rpms. When deploying to many nodes, this is a far more efficient use of resources. It does require re-encrypting and distributing the slice's private key. Though it is implemented in a secure fashion, if they key's sole purpose is not PlanetLab, then this feature should be disabled.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        default_value = True
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "sliceSSHKey",
        "The controller-local path to the slice user's ssh private key. It is the user's responsability to deploy this file where the controller will run, it won't be done automatically because it's sensitive information. It is recommended that a NEPI-specific user be created for this purpose and this purpose alone.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.NoDefaultValue
        )
    )

box.add_attr(
    attributes.EnumAttribute(
        "plLogLevel",
        "Verbosity of logging of planetlab events.",
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default_value = "ERROR" 
        )
    )

box.add_attr(
    attributes.RangeAttribute(
        "tapPortBase", 
        "Base port to use when connecting TUN/TAPs. Effective port will be BASE + GUID.",
        range = (2000,30000),
        default_value = 15000 
        )
    )

box.add_attr(
    attributes.BoolAttribute(
        "dedicatedSlice",
        "Set to True if the slice will be dedicated to this experiment. NEPI will perform node and slice cleanup, making sure slices are in a clean, repeatable state before running the experiment.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = False
        )
    )

############ CONTAINER #############

box = ContainerBox(TESTBED_ID, CONTAINER, help = "Container for grouping PlanetLab box configurations.")
boxes.append(box)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)


############ ADDRESS #############

box = IPAddressBox(TESTBED_ID, ADDRESS, help = "IP Address box.")
boxes.append(box)

conn = connectors.Connector("iface", "Connector from to PlanetLab interface", max = 1, min = 1)
rule = connectors.ConnectionRule(ADDRESS, "iface", NODEIFACE, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ADDRESS, "iface", TAPIFACE, "addrs", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(ADDRESS, "iface", TUNIFACE, "addrs", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

box.add_tag(tags.ADDRESS)


############ NODE #############

box = Box(TESTBED_ID, NODE, help = "Virtualized Node (V-Server style)")
boxes.append(box)

conn = connectors.Connector("ifaces", "Connector PlanetLab network interfaces", max = -1, min = 1)
rule = connectors.ConnectionRule(NODE, "ifaces", NODEIFACE, "node", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(NODE, "ifaces", TAPIFACE, "node", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(NODE, "ifaces", TUNIFACE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("apps", "Connector to %s" % APPLICATION, max = -1, min = 0)
rule = connectors.ConnectionRule(NODE, "apps", APPLICATION, "node", False)
rule = connectors.ConnectionRule(NODE, "apps", MULTICASTFORWARDER, "node", False)
rule = connectors.ConnectionRule(NODE, "apps", DEPENDENCY, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("pipes", "Connector to a %s" % NETPIPE, max = 2, min = 0)
rule = connectors.ConnectionRule(NODE, "pipes", NETPIPE, "node", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

box.add_tag(tags.NODE)

box.add_attr(
    attributes.StringAttribute(
        "hostname",
        "Constrain hostname during resource discovery. May use wildcards.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable 
        )
    )

box.add_attr(
    attributes.EnumAttribute(
        "architecture",
        "Constrain architexture during resource discovery.",
        allowed = ["x86_64", "i386"],
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable, 
        default_value = "x86_64" 
        )
    )

box.add_attr(
    attributes.EnumAttribute(
        "operating_system",
        "Constrain operating system during resource discovery.",
        allowed =  ["f8", "f12", "f14", "centos", "other"],
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable 
        default_value = "f12"
        )
    )

box.add_attr(
    attributes.StringAttribute(
        "site",
        "Constrain the PlanetLab site this node should reside on.",
        allowed = ["PLE", "PLC", "PLJ"],
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = "PLE" 
        )
    )

box.add_attr(
    attributes.RangeAttribute(
        "min_reliability",
        "Constrain reliability while picking PlanetLab nodes. Specifies a lower acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        range = (0,100)
        )
    )

box.add_attr(
    attributes.RangeAttribute(
        "max_reliability",
        "Constrain reliability while picking PlanetLab nodes. Specifies an upper acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        range = (0,100)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "min_bandwidth",
        "Constrain available bandwidth while picking PlanetLab nodes. Specifies a lower acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = (0,2**31)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "max_bandwidth",
        "Constrain available bandwidth while picking PlanetLab nodes. Specifies an upper acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = (0,2**31)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "min_load",
        "Constrain node load average while picking PlanetLab nodes. Specifies a lower acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = (0,2**31)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "max_load",
        "Constrain node load average while picking PlanetLab nodes. Specifies an upper acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = (0,2**31)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "min_cpu",
        "Constrain available cpu time while picking PlanetLab nodes. Specifies a lower acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        range = (0,100)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "max_cpu",
        "Constrain available cpu time while picking PlanetLab nodes. Specifies an upper acceptable bound.",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        range = (0, 100) 
        )
    )

box.add_attr(
    attributes.StringAttribute(
        TESTBED_ENVIRONMENT_SETUP,
        "Commands to set up the environment needed to run NEPI testbeds",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable | \
                attributes.AttributeFlags.DesignInvisible | \
                attributes.AttributeFlags.Metadata 
        )
    )

############ INTERFACES #############

class TapBox(TunnelBox):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(TapBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_tag(tags.INTERFACE)

        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "node", NODE, "ifaces", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("gre", "IP or Ethernet tunneling using the GRE protocol", max = 1, min = 0)
        rule = connectors.ConnectionRule(self._box_id, "gre", TUNIFACE, "gre", True)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
        rule = connectors.ConnectionRule(self._box_id, "traces", PACKETTRACE, "iface", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self._box_id, "traces", PCAPTRACE, "iface", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
            attributes.BoolAttribute(
                "up", 
                "Link up",
                default_value = True
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                "if_name", 
                "Device name",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable,
                )
            )

        self.add_attr(
            attributes.RangeAttribute(
                "mtu", 
                "Maximum transmition unit for device",
                range = (0,1500)
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                "snat", 
                "Enable SNAT (source NAT to the internet) no this device",
                default_value = False 
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                "pointopoint",
                "If the interface is a P2P link, the remote endpoint's IP should be set on this attribute.",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                "multicast",
                "help": "Enable multicast forwarding on this device. Note that you still need a multicast routing daemon in the node.",
                default_value = False
                )
            )

        self.add_attr(
            attributes.RangeAttribute(
                "bwlimit",
                "Emulated transmission speed (in kbytes per second)",
                range = (1,10*2**20),
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.RangeAttribute(
                "txqueuelen",
                "Transmission queue length (in packets)",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable,
                range = (1,10000),
                default_value = 1000
                )
            )


#########
box = Box(TESTBED_ID, NODEIFACE, 
        help = "External network interface - they cannot be brought up or down, and they MUST be connected to the internet.")
boxes.append(box)

box.add_tag(tags.INTERFACE)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = connectors.ConnectionRule(NODEIFACE, "node", NODE, "ifaces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("inet", "Connector to %s" % INTERNET, max = 1, min = 1)
rule = connectors.ConnectionRule(NODEIFACE, "inet", INTERNET, "ifaces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(NODEIFACE, "traces", PCAPTRACE, "iface", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


#######
box = TapBox(TESTBED_ID, TUNIFACE, help = "Virtual TUN network interface (layer 3)")
boxes.append(box)

#######
box = TapBox(TESTBED_ID, TAPIFACE, help = "Virtual TAP network interface (layer 2)")
boxes.append(box)


############ FILTERS  #############

class FilterBox(TunnelBox):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(FilterBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_tag(tags.FILTER)

        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        self.add_attr(
            attributes.StringAttribute(
                "args",
                "Module arguments - comma-separated list of name=value pairs",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable,
                )
            )

#########
box = FilterBox(TESTBED_ID, TUNFILTER,
            help = "TUN/TAP stream filter\n\n"
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
                    "len(q) and clear.")

boxes.append(box)

box.add_attr(
    attributes.StringAttribute(
        "module",
        "Path to a .c or .py source for a filter module, or a binary .so",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable
        )
    )
 

#########
box = FilterBox(TESTBED_ID, CLASSQUEUEFILTER,
            "help" = "TUN classfull queue, uses a separate queue for each user-definable class.\n\n"
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
                    "priority.")
boxes.append(box)

conn = connectors.Connector("traces", "Connector to traces", max = 1, min = 1)
rule = connectors.ConnectionRule(CLASSQUEUEFILTER, "traces", DROPSTATTRACE, "filter", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

#########
box = FilterBox(TESTBED_ID, TOSQUEUEFILTER,
            help = "TUN classfull queue that classifies according to the TOS (RFC 791) IP field.\n\n"
                    "It takes a size argument that specifies the size of each class. As TOS is a "
                    "subset of DiffServ, this queue half-implements DiffServ.")
boxes.append(box)


############ APPLICATIONS  #############

class BaseApplicationBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(BaseApplicationBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_tag(tags.APPLICATION)

        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "node", NODE, "apps", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

class BaseDependencyBox(BaseApplicationBox):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(BaseDependencyBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
        rule = connectors.ConnectionRule(self._box_id, "traces", BUILDLOGTRACE, "app", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

class DependencyBox(BaseDependencyBox):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(DependencyBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_attr(
            attributes.StringAttribute(
                "depends", 
                "Space-separated list of packages required to run the application",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                "build-depends", 
                "Space-separated list of packages required to build the application",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                "build",
                "Build commands to execute after deploying the sources. "
                    "Sources will be in the ${SOURCES} folder. "
                    "Example: tar xzf ${SOURCES}/my-app.tgz && cd my-app && ./configure && make && make clean.\n"
                    "Try to make the commands return with a nonzero exit code on error.\n"
                    "Also, do not install any programs here, use the 'install' attribute. This will "
                    "help keep the built files constrained to the build folder (which may "
                    "not be the home folder), and will result in faster deployment. Also, "
                    "make sure to clean up temporary files, to reduce bandwidth usage between "
                    "nodes when transferring built packages.",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                "install",
                "Commands to transfer built files to their final destinations. "
                    "Sources will be in the initial working folder, and a special "
                    "tag ${SOURCES} can be used to reference the experiment's "
                    "home folder (where the application commands will run).\n"
                    "ALL sources and targets needed for execution must be copied there, "
                    "if building has been enabled.\n"
                    "That is, 'slave' nodes will not automatically get any source files. "
                    "'slave' nodes don't get build dependencies either, so if you need "
                    "make and other tools to install, be sure to provide them as "
                    "actual dependencies instead.",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.StringAttribute(
                "sources",
                "Space-separated list of regular files to be deployed in the working path prior to building. "
                    "Archives won't be expanded automatically.",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable
                )
            )

        self.add_attr(
            attributes.BoolAttribute(
                "rpm-fusion"
                "True if required packages can be found in the RpmFusion repository",
                flags = attributes.AttributeFlags.ExecReadOnly | \
                        attributes.AttributeFlags.ExecImmutable,
                default_value = False
                )
            )

#######
box = BaseDependencyBox(TESTBED_ID, NEPIDEPENDENCY, 
    help = "Requirement for NEPI inside NEPI - required to run testbed instances inside a node")
boxes.append(box)

#######
box = BaseDependencyBox(TESTBED_ID, NS3DEPENDENCY,
    help = "Requirement for NS3 inside NEPI - required to run NS3 testbed instances inside a node. It also needs NepiDependency.")
boxes.append(box)

#######
box = DependencyBox(TESTBED_ID, DEPENDENCY, help = "Requirement for package or application to be installed on some node")
boxes.append(box)

######
box = DependencyBox(TESTBED_ID, APPLICATION, help = "Generic executable command line application")
boxes.append(box)

conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(APPLICATION, "traces", STDOUTTRACE, "app", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(APPLICATION, "traces", STDERRTRACE, "app", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(APPLICATION, "traces", OUTPUTTRACE, "app", False)
conn.add_connection_rule(rule)
rule = connectors.ConnectionRule(APPLICATION, "traces", BUILDLOGTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
    attributes.StringAttribute(
        "command",
        "Command line string",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable
        )
    )

box.add_attr(
    attributes.BoolAttribute(
        "sudo",
        "Run with root privileges",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = False
        )
    )

box.add_attr(
    attributes.BoolAttribute(
        "stdin",
        "Standard input",
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable
        )
    )


############ MULTICAST  #############

box = Box(TESTBED_ID, MULTICASTFORWARDER,
    help = "This application installs a userspace packet forwarder that, when connected to a node, filters all packets flowing through multicast-capable virtual interfaces and applies custom-specified routing policies.")
boxes.append(box)

box.add_tag(tags.APPLICATION)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(MULTICASTFORWARDER, "traces", BUILDLOGTRACE, "app", False)
rule = connectors.ConnectionRule(MULTICASTFORWARDER, "traces", STDERRTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = connectors.ConnectionRule(MULTICASTFORWARDER, "node", NODE, "apps", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("router", "Connector to  a multicast router", max = 1, min = 1)
rule = connectors.ConnectionRule(MULTICASTFORWARDER, "router", MULTICASTROUTER, "fwd", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


#######
box = Box(TESTBED_ID, MULTICASTANNOUNCER,
        help =  "This application installs a userspace daemon that monitors multicast membership and announces it on all multicast-capable interfaces.\n This does not usually happen automatically on PlanetLab slivers.")
boxes.append(box)

conn = connectors.Connector("node", "Connector to %s" % NODE, max = 1, min = 1)
rule = connectors.ConnectionRule(MULTICASTANNOUNCER, "node", NODE, "apps", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(APPLICATION, "traces", STDERRTRACE, "app", False)
rule = connectors.ConnectionRule(APPLICATION, "traces", BUILDLOGTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


#######
box = Box(TESTBED_ID, MULTICASTROUTER, 
        help = "This application installs a userspace daemon that monitors multicast membership and announces it on all multicast-capable interfaces.\n This does not usually happen automatically on PlanetLab slivers.")
boxes.append(box)

box.add_tag(tags.APPLICATION)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(MULTICASTRPOUTER, "traces", BUILDLOGTRACE, "app", False)
rule = connectors.ConnectionRule(MULTICASTROUTER, "traces", STDERRTRACE, "app", False)
rule = connectors.ConnectionRule(MULTICASTROUTER, "traces", STDOUTTRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("fwd", "Connector to a multicast forwarder", max = 1, min = 1)
rule = connectors.ConnectionRule(MULTICASTROUTER, "fwd", MULTICASTFORWARDER, "router", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
    attributes.EnumAttribute(
        "routing_algorithm",
        "Routing algorithm.",
        allowed = ["dvmrp"],
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable,
        default_value = "dvmrp"
        )
    )


############ INTERNET #############
box = Box(TESTBED_ID, INTERNET, help = "Internet routing")
boxes.append(box)

box.add_tag(tags.INTERNET)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("ifaces", "Connector to %s" % NODEIFACE, max = -1, min = 1)
rule = connectors.ConnectionRule(INTERNET, "iafces", NODEIFACE, "inet", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


############ NETPIPE #############
box = Box(TESTBED_ID, NETPIPE, help = "Link emulation")
boxes.append(box)
        
box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("traces", "Connector to traces", max = -1, min = 0)
rule = connectors.ConnectionRule(NETPIPE, "traces", NETPIPETRACE, "app", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

conn = connectors.Connector("node", "Connector to %s" % NODE, max = -1, min = 0)
rule = connectors.ConnectionRule(NETPIPE, "node", NODE, "pipe", False)
conn.add_connection_rule(rule)
box.add_connector(conn)

box.add_attr(
    attributes.EnumAttribute(
        "mode",
        "Link mode:\n"
                " * SERVER: applies to incoming connections\n"
                " * CLIENT: applies to outgoing connections\n"
                " * SERVICE: applies to both",
        allowed = ["SERVER", "CLIENT", "SERVICE"],
        flags = attributes.AttributeFlags.ExecReadOnly | \
                attributes.AttributeFlags.ExecImmutable
        )
    )

box.add_attr(
    AddrListAttribute(
        "addrList", 
        "Address list or range. Eg: '127.0.0.1', '127.0.0.1,127.0.1.1', '127.0.0.1/8'"
        )
    )

box.add_attr(
    PortListAttribute(
        "portList",
        "Port list or range. Eg: '22', '22,23,27', '20-2000'"
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "bwIn",
        "Inbound bandwidth limit (in Mbit/s)"
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "plrIn",
        "Inbound packet loss rate (0 = no loss, 1 = 100% loss)"
        )
    )

box.add_attr(
    attributes.RangeAttribute(
        "delayIn",
        "Inbound packet delay (in milliseconds)",
        range = (0,60000)
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "bwOut",
        "Outbound bandwidth limit (in Mbit/s)"
        )
    )

box.add_attr(
    attributes.DoubleAttribute(
        "plrOut",
        "Outbound packet loss rate (0 = no loss, 1 = 100% loss)"
        )
    )

box.add_attr(
    attributes.RangeAttribute(
        "delayOut"
        "Outbound packet delay (in milliseconds)",
        range = (0,60000)
        )
    )


############ TRACES  #############

class ApplicationTraceBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(ApplicationTraceBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_tag(tags.TRACE)

        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("app", "Connector to %s" % APPLICATION, max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "app", APPLICATION, "traces", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

class TunTraceBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(TunTraceBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_tag(tags.TRACE)

        self.add_container_info(TESTBED_ID, tags.CONTROLLER)
        self.add_container_info(TESTBED_ID, tags.CONTAINER)

        conn = connectors.Connector("iface", "Connector to TUN/TAP device", max = 1, min = 1)
        rule = connectors.ConnectionRule(self._box_id, "iface", TUNIFACE, "traces", False)
        conn.add_connection_rule(rule)
        rule = connectors.ConnectionRule(self._box_id, "iface", TAPIFACE, "traces", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)


######
box = ApplicationTraceBox(TESTBED_ID, BUILDLOGTRACE, help = "Build log output for dependency installation")
boxes.append(box)
 
######
box = ApplicationTraceBox(TESTBED_ID, STDERRTRACE, help = "Standard error output from application")
boxes.append(box)
 
######
box = ApplicationTraceBox(TESTBED_ID, STDOUTTRACE, help = "Standard output from application")
boxes.append(box)
 
######
box = ApplicationTraceBox(TESTBED_ID, OUTPUTTRACE, help = "Application output")
boxes.append(box)
 
######
box = TraceBox(TESTBED_ID, PACKETTRACE, help = "Text format packet trace")
boxes.append(box)
 
######
box = TunTraceBox(TESTBED_ID, PCAPTRACE, help = "Pcap packet trace")
boxes.append(box)

######
box = Box(TESTBED_ID, DROPSTATTRACE, help = "")
boxes.append(box)

box.add_tag(tags.TRACE)

box.add_container_info(TESTBED_ID, tags.CONTROLLER)
box.add_container_info(TESTBED_ID, tags.CONTAINER)

conn = connectors.Connector("filter", "Connector to a filter", max = 1, min = 1)
rule = connectors.ConnectionRule(DROPSTATETRACE, "filter", CLASSQUEUEFILTER, "traces", False)
conn.add_connection_rule(rule)
box.add_connector(conn)


