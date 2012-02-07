# -*- coding: utf-8 -*-

"""
Experiment design API
"""

import copy
import getpass
import logging
import os
import sys
import weakref 

from nepi.design import attributes, connectors, tags 
from nepi.design.graphical import GraphicalInfo

from nepi.util.constants import DeploymentConfiguration as DC
from nepi.util.guid import GuidGenerator


class Box(tags.Taggable, attributes.AttributesMap, connectors.ConnectorsMap):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(Box, self).__init__()
        self._guid_generator = guid_generator
        # guid -- global unique identifier
        self._guid = guid
        # Testbed identifier
        self._testbed_id = testbed_id
        # Box type identifier -- the box type
        self._box_id = box_id
        # Help text
        self._help = help
        # Box class to instantiate
        # container -- container box instance
        self._container = None
        # graphical_info -- GUI position information
        self._graphical_info = GraphicalInfo()
        # aggregations -- dictionary of contained instances
        # -- dict(guid: box_ref)
        self._boxes = dict() 
        # Information of containers that can contain this box type
        # -- dict(testbed_id: tags)
        self._container_info = dict()

        self.add_attr(
                attributes.StringAttribute(
                    "label", 
                    "A unique user-defined identifier for referring to this box",
                    flags = attributes.AttributeFlags.ExecReadOnly |\
                        attributes.AttributeFlags.ExecImmutable |\
                        attributes.AttributeFlags.Metadata
                    )
                )
 

        self._logger = logging.getLogger("nepi.design.boxes")

    def __str__(self):
        return "Box(%s, %s, %s)" % (self.guid, self.box_id, 
                self.testbed_id)
    
    @property
    def testbed_id(self):
        return self._testbed_id

    @property
    def box_id(self):
         return self._box_id

    @property
    def container_info(self):
        return self._container_info

    @property
    def guid(self):
        return self._guid

    @property
    def graphical_info(self):
        return self._graphical_info

    @property
    def help(self):
        return self._help

    @property
    def boxes(self):
        return self._boxes.values()

    @property
    def xml(self):
        from nepi.util.parser import XMLBoxParser
        parser = XMLBoxParser()
        return parser.to_xml(self)

    @property
    def controller(self):
        if tags.CONTROLLER in self.tags:
            return self
        return self.container if not self.container or \
                (tags.CONTROLLER in self.container.tags) else self.container.controller

    def get_container(self):
        # Gives back a strong-reference not a weak one
        if not self._container:
            return None
        return self._container()

    def set_container(self, container):
        self._container = weakref.ref(container)

    container = property(get_container, set_container)

    def add_container_info(self, testbed_id, must_have_one, must_have_all = None):
        if testbed_id not in self._container_info:
            self._container_info[testbed_id] = dict()

        if must_have_one:
            if not isinstance(must_have_one, list):
                must_have_one = [must_have_one]
            if 'must_have_one' not in self._container_info[testbed_id]:
                self._container_info[testbed_id]['must_have_one'] = set(must_have_one)
            else:
                self._container_info[testbed_id]['must_have_one'].update(set(must_have_one))

        if must_have_all:
            if not isinstance(must_have_all, list):
                must_have_all = [must_have_all]
            if 'must_have_all' not in self._container_info[testbed_id]:
                self._container_info[testbed_id]['must_have_all'] = set(must_have_all)
            else:
                self._container_info[testbed_id]['must_have_all'].update(set(must_have_all))


    def add(self, box):
        # TODO: Check cycles in containers!
        tags = box.container_info.get(self.testbed_id, 'miss')
        must_have_one = tags.get('must_have_one', 'miss')
        must_have_all = tags.get('must_have_all', 'miss')
        # The testbed_id must be allowed
        if tags != 'miss' and \
                ( 
                    # self must have at least one of the must_have_one tags
                    (must_have_one != 'miss' and [t for t in self.tags if t in must_have_one]) or \
                    # self must have all the must_have_all tags
                    (must_have_all != 'miss' and  not [ t for t in tags if t not in self.tags ])
                ):
            box.container = self
            self._boxes[box.guid] = box
        else:
            self._logger.error("Can't add box type %s to box type %s.", 
                    box.box_id, self.box_id)

    def remove(self, box):
        if box.guid in self.list_boxes():
            del self._boxes[box.guid]
            box.container = None
    
    def box(self, id):
        if self.guid == id or self.a.label.value == id:
            return self
        if not self._boxes:
            return None
        box = None
        for b in self._boxes.values():
            box = b.box(id)
            if box: break
        return box

    def clone(self, **kwargs):
        guid = None
        if "guid" in kwargs:
            guid = kwargs["guid"]
            del kwargs["guid"]
        
        container = None
        if "container" in kwargs:
            container = kwargs["container"]
            del kwargs["container"]
        
        new = copy.copy(self)
        guid = self._guid_generator.next(guid)
        new._guid = guid
        new._graphical_info = GraphicalInfo()
        if container:
            container.add(new)
        new._boxes = dict()
        new.clone_attrs(self)
        new.clone_connectors(self)

        for k,v in kwargs.iteritems():
            attr = getattr(new.a, k)
            attr.value = v
        return new


class ContainerBox(Box):
    def __init__(self, box_id, testbed_id, guid_generator = None, guid = None,
            help = None):
        super(ContainerBox, self).__init__(box_id, testbed_id, guid_generator, 
                guid, help)
        
        self.add_tag(tags.CONTAINER)

        self.add_attr(
                attributes.BoolAttribute(
                    "opaque", 
                    "Marks wether internal elements should be visible or not.",
                    flags = attributes.AttributeFlags.ExecReadOnly |\
                        attributes.AttributeFlags.ExecImmutable |\
                        attributes.AttributeFlags.Metadata
                    )
                )

        self.add_attr(
                attributes.StringAttribute(
                    "boxId", 
                    "Id to identify the container type.",
                    flags = attributes.AttributeFlags.ExecReadOnly |\
                        attributes.AttributeFlags.ExecImmutable |\
                        attributes.AttributeFlags.Metadata
                    )
                )

    def expose_connector(self, name, connector):
        if connector.owner in self.boxes:
            self._connectors[name] = connector

    def unexpose_connector(self, name):
        if name in self._exposed_connectors:
            del self._connectors[name]

    def expose_attribute(self, name, attribute):
        if attribute.owner in self.boxes:
            self._attributes[name] = attribute

    def unexpose_attribute(self, name):
        if name in self._attributes:
            del self._attributes[name]

    def remove(self, box):
        super(ContainerBox, self).remove(box)
        for name, attr in self._attributes.iteritems():
            if attr.owner == box:
                self.unexpose_attribute(name)
        for name, conn in self._connectors.iteritems():
            if conn.owner == box:
                self.unexpose_connector(name)

    def is_connected(self, connector, other_connector):
        if connector not in self._connectors.values():
            return False
        # It is not an exposed connector
        if self._connectors.get(connector.name):
            conn = self._connector[connector.name]
            if conn == connector:
                return super(ContainerBox, self).is_connected(connector, other_connector)
        # It is an exposed connector... so go to the real owner for answers
        return (other_connector.owner, other_connector.name) in connector.owner._connections[connector.name]

    @property
    def connections(self):
        connections = list()
        for name, connector in self._connectors.iteritems():
            # It is not an exposed connector
            if name == connector.name:
                for (other_box, other_connector_name) in self._connections[name]:
                    connections.append((self, name, other_box, other_connector_name))
            # It is an exposed connector... so go to the real owner for answers
            else:
                for (other_box, other_connector_name) in connector.owner._connections[connector.name]:
                    connections.append((connector.owner, connector.name, other_box, other_connector_name))
        return connections

    def clone_attrs(self, other):
        self._a = attributes.AttributesMapProxy(self)
        self._attributes = dict()
        for name, attr in other._attributes.iteritems():
            # Only clone natural attributes, not exposed ones
            if name != attr.name:
                continue
            new = attr.clone()
            self.add_attr(new)

    def clone_connectors(self, other):
        self._c = connectors.ConnectorsMapProxy(self)
        self._connectors = dict()
        self._cn = connectors.ConnectionsProxy(self)
        self._connections = dict()

    def clone_boxes(self, other):
        cloned = dict()
        connections = list()
        self._boxes = dict()
        for box in other.boxes:
            new = box.clone()
            cloned[box.guid] = new.guid
            self.add(new)
            for conx in box.connections:
                (b, connector, other_b, other_connector) = conx
                # Don't repeat connections are always pairwise
                if not (other_b.guid, other_connector, b.guid, connector) in connections:
                    connections.append((b.guid, connector, other_b.guid, other_connector))

        # expose attributes
        for name, attr in other._attributes.iteritems():
            # Expose only foreign attributes
            if name == attr.name:
                continue
            cloned_guid = cloned[attr.owner.guid]
            box = self._boxes[cloned_guid]
            attribute = getattr(box.a, attr.name)
            self.expose_attribute(name, attribute)
        # expose connectors
        for name, conn in other._connectors.iteritems():
            # Expose only foreign attributes
            if name == conn.name:
                continue
            cloned_guid = cloned[conn.owner.guid]
            box = self._boxes[cloned_guid]
            connector = getattr(box.c, conn.name)
            self.expose_connector(name, connector)
        # clone internal connections
        for conx in connections:
            (guid, connector, other_guid, other_connector) = conx
            if other_guid in cloned.keys():
                cloned_guid = cloned[guid]
                cloned_box = self._boxes[cloned_guid]
                cloned_other_guid = cloned[other_guid]
                cloned_other_box = self._boxes[cloned_other_guid]
                conn = getattr(cloned_box.c, connector)
                other_conn = getattr(cloned_other_box.c, other_connector)
                conn.connect(other_conn)

    def clone(self, **kwargs):
        guid = None
        if "guid" in kwargs:
            guid = kwargs["guid"]
            del kwargs["guid"]

        container = None
        if "container" in kwargs:
            container = kwargs["container"]
            del kwargs["container"]

        new = copy.copy(self)
        guid = self._guid_generator.next(guid)
        new._guid = guid
        new._graphical_info = GraphicalInfo()
        if container:
            container.add(new)
        new.clone_attrs(self)
        new.clone_connectors(self)
        new.clone_boxes(self)
        return new


class IPAddressBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None,
            help = None):
        super(IPAddressBox, self).__init__(testbed_id, box_id, guid_generator, 
                guid, help)
        
        self.add_tag(tags.ADDRESS)
        
        self.add_attr(
                attributes.IPAttribute(
                    "address", 
                    "IP Address number", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "netPrefix", 
                    "Network prefix for the address", 
                    min = 0,
                    max = 128,
                    default_value = 24,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IPv4Attribute(
                    "broadcast", 
                    "Broadcast network address", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )


class RouteBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None,
            help = None):
        super(RouteBox, self).__init__(testbed_id, box_id, guid_generator, 
                guid, help)
        
        self.add_tag(tags.ROUTE)

        self.add_attr(
                attributes.StringAttribute(
                    "destination", 
                    "Network destination address", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "netPrefix", 
                    "Network prefix for the address", 
                    min = 0,
                    max = 128,
                    default_value = 24,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    "nextHop", 
                    "Address of the next hop", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "metric", 
                    "Routing metric", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.BoolAttribute(
                    "default gateway", 
                    "Indicate if this route points to the default gateway", 
                    default_value = False,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )


class TunnelBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(TunnelBox, self).__init__(testbed_id, box_id, guid_generator,
            guid, help)

        self.add_tag(tags.TUNNEL)

        conn = connectors.Connector("->fd", help = "File descriptor receptor for devices with file descriptors",
                max = 1, min = 0)
        rule = connectors.ConnectionRule(self.box_id, "->fd", None, "->fd", False)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("tcp", help = "ip-ip tunneling over TCP link", 
                max = 1, min = 0)
        rule = connectors.ConnectionRule(self.box_id, "tcp", None, "tcp", True)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        conn = connectors.Connector("udp", help = "ip-ip tunneling over UDP datagrams",
                max = 1, min = 0)
        rule = connectors.ConnectionRule(self.box_id, "tcp", None, "tcp", True)
        conn.add_connection_rule(rule)
        self.add_connector(conn)

        self.add_attr(
                attributes.StringAttribute(
                    "tunProto", 
                    "TUNneling protocol used",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    "tunKey",
                    "Randomly selected TUNneling protocol cryptographic key. "
                     "Endpoints must agree to use the minimum (in lexicographic order) "
                     "of both the remote and local sides.",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    "tunAddr",
                    "Address (IP, unix socket, whatever) of the tunnel endpoint",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "tunPort",
                    "IP port of the tunnel endpoint",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.EnumAttribute(
                    "tunCipher",
                    "Cryptographic cipher used for tunnelling",
                    allowed = ["AES", "Blowfish", "DES3", "DES", "PLAIN"],
                    default_value = "AES",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )


class ControllerBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None, 
            help = None):
        super(ControllerBox, self).__init__(testbed_id, box_id, guid_generator,
                guid, help)

        self.add_tag(tags.CONTROLLER)

        self.add_attr(
                attributes.StringAttribute(
                    "homeDirectory", 
                    "Path to the directory where traces and other files will be stored",
                    default_value = "",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    DC.DEPLOYMENT_ENVIRONMENT_SETUP,
                    "Shell commands to run before spawning Controller processes",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.EnumAttribute(
                    DC.DEPLOYMENT_MODE,
                    "Controller execution mode",
                    allowed = [DC.MODE_DAEMON, DC.MODE_SINGLE_PROCESS],
                    default_value = DC.MODE_SINGLE_PROCESS,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.EnumAttribute(
                    DC.DEPLOYMENT_COMMUNICATION,
                    "Controller communication mode",
                    allowed = [DC.ACCESS_LOCAL, DC.ACCESS_SSH],
                    default_value = DC.ACCESS_LOCAL,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    DC.DEPLOYMENT_HOST,
                    "Host where the testbed will be executed",
                    default_value = "localhost",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    DC.DEPLOYMENT_USER,
                    "User on the Host to execute the testbed",
                    default_value = getpass.getuser(),
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    DC.DEPLOYMENT_KEY,
                    "Path to SSH key to use for connecting",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    DC.DEPLOYMENT_PORT,
                    "Port on the Host",
                    default_value = 22,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    DC.ROOT_DIRECTORY,
                    "Root directory for storing process files",
                    default_value = ".",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.BoolAttribute(
                    DC.USE_AGENT,
                    "Use -A option for forwarding of the authentication agent, if ssh access is used", 
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.BoolAttribute(
                    DC.USE_SUDO,
                    "Use sudo to run the deamon process. This option only take flace when the server runs in daemon mode.", 
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.BoolAttribute(
                    DC.CLEAN_ROOT,
                    "Clean server root directory (Warning: This will erase previous data).", 
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.EnumAttribute(
                    DC.LOG_LEVEL,
                    "Log level for controller",
                    allowed = [DC.ERROR_LEVEL, DC.DEBUG_LEVEL],
                    default_value = DC.ERROR_LEVEL,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.EnumAttribute(
                    DC.RECOVERY_POLICY,
                    "Specifies what action to take in the event of a failure.", 
                    allowed = [DC.POLICY_FAIL, DC.POLICY_RECOVER, DC.POLICY_RESTART],
                    default_value = DC.POLICY_FAIL,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attr(
                attributes.BoolAttribute(
                    DC.RECOVER,
                    "Do not intantiate testbeds, rather, reconnect to already-running instances. Used to recover from a dead controller.", 
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.DesignInvisible | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )


class TestbedBox(ControllerBox):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None,
            help = None):
        super(TestbedBox, self).__init__(testbed_id, box_id, guid_generator,
                guid, help)
        self.add_container_info(None, tags.EXPERIMENT)


class ExperimentBox(ControllerBox):
    def __init__(self, guid_generator = None, guid = None):
        super(ExperimentBox, self).__init__(None, "Experiment",
                guid_generator, guid, "Experiment box")
        self.add_tag(tags.EXPERIMENT)


class BoxProvider(object):
    """Holds references to available box factory instances"""
    def __init__(self, mods = None, search_path = None):
        super(BoxProvider, self).__init__()
        self._guid_generator = GuidGenerator()
        exp = ExperimentBox(self._guid_generator, None)
        self._boxes = dict({exp.box_id: exp})
    
        self.load_testbed_boxes(mods)
        self.load_user_containers(search_path)
        self._logger = logging.getLogger("nepi.design.boxes.BoxProvider")

    @property
    def boxes(self):
        return self._boxes.keys()

    def load_user_containers(self, search_path = None):
        if not search_path:
            search_path = os.path.expanduser("~/user/.nepi/containers")
        if not os.path.exists(search_path):
            return
       
        files = [os.path.join(search_path, fn) for fn in os.listdir(search_path) if fn.endswith('.xml')]
        
        for fn in files:
            f = open(fn, "r")
            xml = f.read()
            f.close()
            box = self.from_xml(xml)
            box._box_id = box.a.boxId.value
            self.add(box)

    def store_user_container(self, box, search_path = None):
        if not search_path:
            search_path = os.path.expanduser("~/user/.nepi/containers")
        if not os.path.exists(search_path):
            os.mkdirs(search_path)

        if not box.a.boxId.value:
            self._logger.error("Could not serialize container: Value is required for guid(%d).a.boxId .", 
                    box.guid)
            return False
        
        from nepi.util.parser import XMLBoxParser
        parser = XMLBoxParser()
        xml = parser.to_xml(box)
        
        fn = "%s.xml" % box.a.boxId.value.replace("::", "_")
        fp = os.path.join(search_path, fn)
        f = open(fp, "w")
        f.write(xml)
        f.close()
        return True

    def load_testbed_boxes(self, mods = None):
        if not mods:
            import pkgutil
            import nepi.testbeds
            pkgpath = os.path.dirname(nepi.testbeds.__file__)
            modnames = ["nepi.testbeds.%s" % name for _, name, _ in pkgutil.iter_modules([pkgpath])]

            mods = []
            for modname in modnames:
                if modname not in sys.modules:
                    __import__(modname)
                    mod = sys.modules[modname]
                    mods.append(mod)

        for mod in mods:
            self.add_all(mod.boxes)

    def from_xml(self, xml):
        from nepi.util.parser import XMLBoxParser
        parser = XMLBoxParser()
        self._guid_generator.off = True
        box = parser.from_xml(self, xml)
        self._guid_generator.off = False
        return box

    def add(self, box):
        if box.box_id not in self._boxes.keys():
            box._guid_generator = self._guid_generator
            self._boxes[box.box_id] = box

    def add_all(self, boxes):
        for box in boxes:
            self.add(box)

    def create(self, box_id, **kwargs):
        box = self._boxes[box_id]
        new = box.clone(**kwargs)
        return new


def create_provider(mods = None, search_path = None):
    # this factory provider instance will hold reference to all available factories 
    return BoxProvider(mods, search_path)


