# -*- coding: utf-8 -*-

"""
Experiment design API
"""

import copy
import getpass
import logging

from nepi.design import attributes, connectors, tags 
from nepi.design.graphical import GraphicalInfo

from nepi.util.constants import DeploymentConfiguration as DC
from nepi.util.guid import GuidGenerator
from nepi.util.parser import XMLBoxParser


class BoxFactory(tags.Taggable, attributes.AttributesMap, 
        connectors.ConnectorsMap):
    """ The Factory instances hold information about a Box class
    and 'know' how to create a box instance."""
    def __init__(self, testbed_id, box_id, clazz = Box):
        super(BoxFactory, self).__init__()
        # Testbed identifier
        self._testbed_id = testbed_id
        # Box type identifier -- the box type
        self._box_id = box_id
        # Box class to instantiate
        self._clazz = clazz
        # List of box types that can contain this box type -- if None is 
        # included in the list then the box can be uncontained
        self._container_box_ids = list()

        self.add_attr(
                attributes.StringAttribute(
                    "label", 
                    "A unique user-defined identifier for referring to this box",
                    flags = attributes.AttributeFlags.ExecReadOnly |\
                        attributes.AttributeFlags.ExecImmutable |\
                        attributes.AttributeFlags.Metadata
                    )
                )
    
    @property
    def testbed_id(self):
        return self._testbed_id

    @property
    def box_id(self):
         return self._box_id

    def add_container_box_id(self, box_id):
        self._container_box_ids.append(box_id)

    @properties
    def container_box_ids(self):
        return self._container_box_ids

    def create(self, guid):
        box = self._clazz(guid, self)
        new.clone_attrs(self)
        new.clone_connectors(self)
        return box

    def clone(self, guid, box):
        new = copy.copy(box)
        new._guid = guid
        new.clone_attrs(box)
        new.clone_connectors(box)
        return new


class Box(attributes.AttributesMap, connectors.ConnectorsMap):
    def __init__(self, guid, factory):
        super(Box, self).__init__()
        # guid -- global unique identifier
        self._guid = guid
        # factory_id -- factory instance
        self._factory = factory
        # container -- container box instance
        self._container = None
        # graphical_info -- GUI position information
        self._graphical_info = GraphicalInfo()
        # aggregations -- dictionary of contained instances
        # -- dict(guid: box_ref)
        self._boxes = dict() 

        self._logger = logging.getLogger("nepi.design.boxes")

    def __str__(self):
        return "Box(%s, %s, %s)" % (self.guid, self.box_id, 
                self.testbed_id)

    @property
    def guid(self):
        return self._guid

    @property
    def box_id(self):
        return self._factory.box_id

    @property
    def testbed_id(self):
        return self._factory.testbed_id
 
    @property
    def factory(self):
        return self._factory

    @property
    def graphical_info(self):
        return self._graphical_info

    @property
    def tags(self):
        return self._factory.tags

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

    def add_box(self, box):
        if self.box_id in box.factory.container_box_ids:
            box.container = self
            self._boxes[box.guid] = box
        else:
            self._logger.error("Wrong box type %s to add to box type %s.", 
                    box.box_id, self.box_id)

    def remove_box(self, box):
        if box.guid in self.list_boxes():
            del self._boxes[box.guid]
            box.container = None

    @property
    def boxes(self):
        return self._boxes

    def to_xml(self):
        parser = XMLBoxParser()
        return parser.to_xml(self)


class IPAddressBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz = Box):
        super(IPAddressBoxFactory, self).__init__(testbed_id, box_id, clazz)
        
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


class RouteBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz = Box):
        super(RouteBoxFactory, self).__init__(testbed_id, box_id, clazz)
        
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
                    args = {"min":0, "max":128},
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


class TunnelBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz = Box):
        super(TunnelBoxFactory, self).__init__(testbed_id, box_id, clazz)

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
                    args = {'allowed': ["AES", "Blowfish", "DES3", "DES", "PLAIN"]},
                    default_value = "AES",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )


class ControllerBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz = Box):
        super(ControllerBoxFactory, self).__init__(testbed_id, box_id, clazz)

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
                    args = {"allowed": [DC.MODE_DAEMON, DC.MODE_SINGLE_PROCESS]},
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
                    args = {"allowed": [DC.ACCESS_LOCAL, DC.ACCESS_SSH]},
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
                attributes.BoolAttribute(
                    DC.LOG_LEVEL,
                    "Log level for controller",
                    args = {"allowed": [DC.ERROR_LEVEL, DC.DEBUG_LEVEL]},
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
                    args = {"allowed": [DC.POLICY_FAIL, DC.POLICY_RECOVER, DC.POLICY_RESTART]},
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


class TestbedBoxFactory(ControllerBoxFactory):
    def __init__(self, testbed_id, box_id, clazz = Box):
        super(TestbedBoxFactory, self).__init__(testbed_id, box_id, clazz)
        self.add_container_box_id("Experiment")


class ExperimentBoxFactory(ControllerBoxFactory):
    def __init__(self):
        super(ExperimentBoxFactory, self).__init__("", "Experiment", Box)

class BoxFactoryProvider(object):
    """Holds references to available box factory instances"""
    def __init__(self):
        super(BoxFactoryProvider, self).__init__()
        self._guid_generator = GuidGenerator()
        self._factories = dict({ExperimentBoxFactory()})

    def factory(self, factory):
        return self._factories[box_id]

    @property
    def factories(self):
        return self._factories.keys()

    def add(self, factory):
        if factory.box_id not in self._factories.keys():
            self._factories[factory.box_id] = factory

    def add_all(self, factories):
        for factory in factories:
            self.add(factory)

    def remove(self, factory):
        del self._factories[factory.box_id]

    def create(self, box_id, **kwargs):
        guid = None
        if "guid_" in kwargs:
            guid = kwargs["guid_"]
            del kwargs["guid_"]
        container = None
        if "container_" in kwargs:
            container = kwargs["container_"]
            del kwargs["container_"]
        guid = self._guid_generator.next(guid)
        factory = self._factories[box_id]
        box = factory.create(guid, kwargs)
        if container:
            container.add_box(box)
        return box

    def clone(self, box):
        guid = self._guid_generator.next(None)
        new = box.factory.clone(guid, box)
        if box.container:
            box.container.add_box(new)
        return new


def create_provider():
    # this factory provider instance will hold reference to all available factories 
    return BoxFactoryProvider()


