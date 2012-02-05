# -*- coding: utf-8 -*-

"""
Experiment design API
"""

import copy
import getpass
import logging
import os
import weakref 

from nepi.design import attributes, connectors, tags 
from nepi.design.graphical import GraphicalInfo

from nepi.util.constants import DeploymentConfiguration as DC
from nepi.util.guid import GuidGenerator


class Box(tags.Taggable, attributes.AttributesMap, connectors.ConnectorsMap):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None):
        super(Box, self).__init__()
        self._guid_generator = guid_generator
        # guid -- global unique identifier
        self._guid = guid
        # Testbed identifier
        self._testbed_id = testbed_id
        # Box type identifier -- the box type
        self._box_id = box_id
        # Box class to instantiate
        # container -- container box instance
        self._container = None
        # graphical_info -- GUI position information
        self._graphical_info = GraphicalInfo()
        # aggregations -- dictionary of contained instances
        # -- dict(guid: box_ref)
        self._boxes = dict() 
        # List of box types that can contain this box type -- if None is 
        # included in the list then the box can be uncontained
        self._containers = list()

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
    def containers(self):
        return self._containers

    @property
    def guid(self):
        return self._guid

    @property
    def graphical_info(self):
        return self._graphical_info

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
        return self._container()

    def set_container(self, container):
        self._container = weakref.ref(container)

    container = property(get_container, set_container)

    def add_container(self, box_id):
        self._containers.append(box_id)

    def add(self, box):
        if self.box_id in box.containers:
            box.container = self
            self._boxes[box.guid] = box
        else:
            self._logger.error("Wrong box type %s to add to box type %s.", 
                    box.box_id, self.box_id)

    def remove(self, box):
        if box.guid in self.list_boxes():
            del self._boxes[box.guid]
            box.container = None
    
    def box(self, guid):
        if self.guid == guid:
            return self
        if not self._boxes:
            return None
        if guid in self._boxes:
            return self._boxes[guid]
        box = None
        for b in self._boxes.values():
             box = b.box(guid)
             if box: break
        return box

    def clone(self, **kwargs):
        guid = None
        if "guid" in kwargs:
            guid = kwargs["guid"]
            del kwargs["guid"]
        new = copy.copy(self)
        guid = self._guid_generator.next(guid)
        new._guid = guid
        new._graphical_info = GraphicalInfo()
        new._boxes = dict() 
        new.clone_attrs(self)
        new.clone_connectors(self)
        return new


"""
class ContainerBox(Box):
    def __init__(self, box_id, testbed_id, guid_generator = None, guid = None, **kwargs):
        super(ContainerBox).__init__(box_id, testbed_id, guid_generator, guid, **kwargs)
        self._exposed_connectors = dict()


    def expose_connector():

    def unexpose_connector()


    def copy(self, box):
        # TODO: Copy connections!
        new = copy.copy(box)
        guid = self._guid_generator.next(None)
        new._guid = guid
        new.clone_attrs(box)
        new.clone_connectors(box)
        return new
"""


class IPAddressBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None):
        super(IPAddressBox, self).__init__(testbed_id, box_id, 
                guid_generator = guid_generator, guid = guid)
        
        self.add_tag(tags.ADDRESS)
        
        self.add_attr(
                attributes.IPAttribute(
                    "Address", 
                    "IP Address number", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "NetPrefix", 
                    "Network prefix for the address", 
                    min = 0,
                    max = 128,
                    default_value = 24,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IPv4Attribute(
                    "Broadcast", 
                    "Broadcast network address", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )


class RouteBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None):
        super(RouteBox, self).__init__(testbed_id, box_id,
                guid_generator = guid_generator, guid = guid)
        
        self.add_tag(tags.ROUTE)

        self.add_attr(
                attributes.StringAttribute(
                    "Destination", 
                    "Network destination address", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "NetPrefix", 
                    "Network prefix for the address", 
                    min = 0,
                    max = 128,
                    default_value = 24,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.StringAttribute(
                    "NextHop", 
                    "Address of the next hop", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.IntegerAttribute(
                    "Metric", 
                    "Routing metric", 
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attr(
                attributes.BoolAttribute(
                    "Default gateway", 
                    "Indicate if this route points to the default gateway", 
                    default_value = False,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )


class TunnelBox(Box):
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None):
        super(TunnelBox, self).__init__(testbed_id, box_id,
                guid_generator = guid_generator, guid = guid)

        self.add_tag(tags.TUNNEL)

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
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None):
        super(ControllerBox, self).__init__(testbed_id, box_id,
                guid_generator = guid_generator, guid = guid)

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
    def __init__(self, testbed_id, box_id, guid_generator = None, guid = None):
        super(TestbedBox, self).__init__(testbed_id, box_id,
                guid_generator = guid_generator, guid = guid)
        self.add_container("Experiment")


class ExperimentBox(ControllerBox):
    def __init__(self, guid_generator = None, guid = None):
        super(ExperimentBox, self).__init__(None, "Experiment",
                guid_generator = guid_generator, guid = guid)
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

    @property
    def boxes(self):
        return self._boxes.keys()

    def load_user_containers(self, search_path):
        if not search_path:
            search_path = os.path.expanduser("~/user/.nepi/containers")
        if not os.path.exists(search_path):
            return
        files = [fn for fn in os.listdir(search_path) if fn.endswith('.xml')]
        for fn in files:
            f = fn.open(fn, "r")
            xml = f.read()
            f.close()
            box = self.from_xml(xml)
            self.add(box)

    def load_testbed_boxes(self, mods = None):
        if not mods:
            import pkgutil
            import nepi.testbeds
            pkgpath = os.path.dirname(nepi.testbdes.__file__)
            mods = [name for _, name, _ in pkgutil.iter_modules([pkgpath])]

        for mod in mods:
            self.add_all(mod.boxes)

    def from_xml(self, xml):
        from nepi.util.parser import XMLBoxParser
        parser = XMLBoxParser()
        box = parser.from_xml(self, xml)
        return box

    def add(self, box):
        if box.box_id not in self._boxes.keys():
            box._guid_generator = self._guid_generator
            self._boxes[box.box_id] = box

    def add_all(self, boxes):
        for box in boxes:
            self.add(box)

    def create(self, box_id, **kwargs):
        container = None
        if "container_" in kwargs:
            container = kwargs["container_"]
            del kwargs["container_"]
        box = self._boxes[box_id]
        new = box.clone(**kwargs)
        if container:
            container.add_box(new)
        return new


def create_provider(mods = None, search_path = None):
    # this factory provider instance will hold reference to all available factories 
    return BoxProvider(mods, search_path)


