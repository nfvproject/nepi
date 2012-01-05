# -*- coding: utf-8 -*-

"""
Experiment design API
"""

import getpass
import logging

from nepi.design import attributes 
from nepi.design import tags
from nepi.design.graphical import GraphicalInfo

from nepi.util.constants import DeploymentConfiguration as DC
from nepi.util.guid import GuidGenerator
from nepi.util.parser._xml import XMLBoxParser


class BoxFactoryProvider(object):
    """Holds references to available box factory instances"""
    def __init__(self, experiment = None):
        super(BoxFactoryProvider, self).__init__()
        self._factories = dict()

    @property
    def factories(self):
        return self._factories.values()

    def factory(self, box_id):
        return self._factories[box_id]

    def add_factory(self, factory):
        if factory.box_id not in self._factories.keys():
                self._factories[factory.box_id] = factory

    def add_factories(self, module):
        for factory in module.factories:
            self.add_factory(factory)

    def remove_factory(self, factory):
        del self._factories[factory.box_id]

    def create(self, experiment, box_id, guid = None):
        guid = experiment.next_guid(guid)
        factory = self.factory(box_id)
        box = factory.create(guid, experiment)
        return box

    def create_add(self, experiment, box_id, container, guid = None):
        """ Creates a box and aggregates it to a box container """
        box = self.create(self, experiment, box_id, guid)
        container.add_box(box)
        return box


class BoxFactory(tags.Taggable):
    """ The Factory instances hold information about a Box class
    and 'know' how to create a box instance."""
    def __init__(self, testbed_id, box_id, clazz):
        super(BoxFactory, self).__init__()
        # Testbed identifier
        self._testbed_id = testbed_id
        # Box type identifier -- the box type
        self._box_id = box_id
        # Box class to instantiate
        self._clazz = clazz
        # Static (metadata) attributes info. Doesn't hold values
        # -- dict(attr_id: attr_info_ref)
        self._attrs_info = dict()
        # connectors -- list of available connectors for the box
        self._connectors = dict()
        # List of box types that can contain this box id -- if None is 
        # included in the list then the box can be uncontained
        self._container_box_ids = list()

        self.add_attribute_info(
                attributes.AttributeInfo(
                    "label", 
                    "A unique user-defined identifier for referring to this box",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
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

    def list_connectors(self):
        return self._connectors.keys()

    def connector(self, connector_name):
        return self._connectors[connector_name]

    def add_connector(self, connector):
        self._connectors[connector.name] = connector

    def add_attribute_info(self, attr_info):
        self._attrs_info[attr_info.name] = attr_info

    def get_attribute_info(self, attr_name, info = "help"):
        attr = self._attrs_info[attr_name]
        return getattr(attr, info)

    def list_attributes(self):
        return self._attrs_info.keys()

    def add_container_box_id(self, box_id):
        self._container_box_ids.append(box_id)

    def list_container_box_ids(self):
        return self._container_box_ids

    def create(self, guid, experiment):
        box = self._clazz(guid, self, experiment)
        # add attributes
        for attr_info in self._attrs_info.values():
            attr = attr_info.clazz(attr_info)
            box.add_attribute(attr)
        # add connector
        for connector_name in self._connectors.keys():
            box.add_connector(connector_name)
        return box


class Box(object):
    def __init__(self, guid, factory, experiment):
        super(Box, self).__init__()
        # guid -- global unique identifier
        self._guid = guid
        # factory_id -- factory instance
        self._factory = factory
        # container -- container box instance
        self.container = None
        # experiment -- reference to the experiment
        self._experiment = experiment
        # graphical_info -- GUI position information
        self._graphical_info = GraphicalInfo()
        # attributes -- dict of attribute instances
        # The box instance holds the collection of attribute
        # instances ti get/set value, while the factory holds
        # the static attribute info
        # -- dict(attr_id: attr_ref)
        self._attributes = dict()
        # aggregations -- dictionary of contained instances
        # -- dict(guid: box_ref)
        self._boxes = dict() 
        # connections -- list of all connected objects by connector
        self._connections = dict()

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
    def experiment(self):
        return self._experiment

    @property
    def controller(self):
        return self.container if not self.container or \
                (tags.CONTROLLER in self.container.tags) else \
                self.container.controller

    def add_connector(self, connector_name):
        self._connections[connector_name] = list()

    def list_connectors(self):
        return self._connections.keys()

    def is_connected(self, connector_name, other_box, other_connector_name):
        return (other_box, other_connector_name) in self._connections[connector_name]

    def connect(self, connector_name, other_box, other_connector_name, 
            connect_other_side = True):
        connector = self.factory.connector(connector_name)
        if connector.can_connect(self, connector_name, other_box, other_connector_name):
            could_connect = True
            if connect_other_side:
                could_connect = other_box.connect(other_connector_name, self, 
                        connector_name, False)
            if could_connect:
                self._connections[connector_name].append((other_box, other_connector_name))
                return True
        self._logger.error("could not connect %d %s from %d %s.", 
                    self.guid, connector_name, other_box.guid, other_connector_name)
        return False

    def disconnect(self, connector_name, other_box, other_connector_name,
            disconnect_other_side = True):
        if (other_box, other_connector_name) in self._connections[connector_name]:
            could_disconnect = True
            if disconnect_other_side:
                could_disconnect = other_box.disconnect(other_connector_name, self,
                        connector_name, False)
            if could_disconnect:
                self._connections[connector_name].remove((other_box, other_connector_name))
                return True
        self._logger.error("could not disconnect %d %s from %d %s.", 
                    self.guid, connector_name, other_box.guid, other_connector_name)
        return False

    def list_connections(self, connector = None):
        if connector:
            return self._connections[connector]
        connections = list()
        for connector_name in self._connections.keys():
            for (other_box, other_connector_name) in self._connections[connector_name]:
                connections.append(self, connector_name, other_box, other_connector_name)
        return connections

    def add_attribute(self, attr):
        attr.container = self
        self._attributes[attr.name] = attr

    def set_attribute(self, attr_name, attr_value):
        attr = self._attributes[attr_name]
        # The attribute object will perform the validation when the value
        # is set
        attr.value = attr_value

    def get_attribute(self, attr_name, info="value"):
        attr = self._attributes[attr_name]
        return getattr(attr, info)

    def list_attributes(self):
        return self._attributes.keys()

    def add_box(self, box):
        if self.box_id in box.factory.list_container_box_ids():
            box.container = self
            self._boxes[box.guid] = box
        else:
            self._logger.error("Wrong box type %s to add to box type %s.", 
                    box.box_id, self.box_id)

    def remove_box(self, box):
        if box.guid in self.list_boxes():
            del self._boxes[box.guid]
            box.container = None

    def list_boxes(self):
        return self._boxes.keys()

    def box(self, guid):
        return self._boxes[guid]

    def to_xml(self):
        parser = XMLBoxParser()
        return parser.to_xml(self)


class IPAddressBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz):
        super(IPAddressBoxFactory, self).__init__(testbed_id, box_id, clazz)
        
        self.add_tag(tags.ADDRESS)
        
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "Address", 
                    "IP Address number", 
                    attributes.AttributeTypes.STRING,
                    attributes.IPAttribute,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "NetPrefix", 
                    "Network prefix for the address", 
                    attributes.AttributeTypes.INTEGER,
                    attributes.IntegerAttribute,
                    args = {"min":0, "max":128},
                    default_value = 24,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "Broadcast", 
                    "Broadcast network address", 
                    attributes.AttributeTypes.STRING,
                    attributes.IPv4Attribute,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )


class RouteBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz):
        super(RouteBoxFactory, self).__init__(testbed_id, box_id, clazz)
        
        self.add_tag(tags.ROUTE)

        self.add_attribute_info(
                attributes.AttributeInfo(
                    "Destination", 
                    "Network destination address", 
                    attributes.AttributeTypes.STRING,
                    attributes.NetRefAttribute,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "NetPrefix", 
                    "Network prefix for the address", 
                    attributes.AttributeTypes.INTEGER,
                    attributes.IntegerAttribute,
                    args = {"min":0, "max":128},
                    default_value = 24,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "NextHop", 
                    "Address of the next hop", 
                    attributes.AttributeTypes.STRING,
                    attributes.IPAttribute,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "Metric", 
                    "Routing metric", 
                    attributes.AttributeTypes.INTEGER,
                    attributes.IntegerAttribute,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "Default gateway", 
                    "Indicate if this route points to the default gateway", 
                    attributes.AttributeTypes.BOOL,
                    attributes.BoolAttribute,
                    default_value = False,
                    flags = attributes.AttributeFlags.NoDefaultValue
                    )
                )


class TunnelBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz):
        super(TunnelBoxFactory, self).__init__(testbed_id, box_id, clazz)

        self.add_tag(tags.TUNNEL)

        self.add_attribute_info(
                attributes.AttributeInfo(
                    "tunProto", 
                    "TUNneling protocol used",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "tunKey",
                    "Randomly selected TUNneling protocol cryptographic key. "
                     "Endpoints must agree to use the minimum (in lexicographic order) "
                     "of both the remote and local sides.",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "tunAddr",
                    "Address (IP, unix socket, whatever) of the tunnel endpoint",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "tunPort",
                    "IP port of the tunnel endpoint",
                    attributes.AttributeTypes.INTEGER,
                    attributes.IntegerAttribute,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    "tunCipher",
                    "Cryptographic cipher used for tunnelling",
                    attributes.AttributeTypes.ENUM,
                    attributes.EnumAttribute,
                    args = {'allowed': ["AES", "Blowfish", "DES3", "DES", "PLAIN"]},
                    default_value = "AES",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )


class ControllerBoxFactory(BoxFactory):
    def __init__(self, testbed_id, box_id, clazz):
        super(ControllerBoxFactory, self).__init__(testbed_id, box_id, clazz)

        self.add_tag(tags.CONTROLLER)

        self.add_attribute_info(
                attributes.AttributeInfo(
                    "homeDirectory", 
                    "Path to the directory where traces and other files will be stored",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    default_value = "",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_ENVIRONMENT_SETUP,
                    "Shell commands to run before spawning Controller processes",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_MODE,
                    "Controller execution mode",
                    attributes.AttributeTypes.ENUM,
                    attributes.EnumAttribute,
                    args = {"allowed": [DC.MODE_DAEMON, DC.MODE_SINGLE_PROCESS]},
                    default_value = DC.MODE_SINGLE_PROCESS,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_COMMUNICATION,
                    "Controller communication mode",
                    attributes.AttributeTypes.ENUM,
                    attributes.EnumAttribute,
                    args = {"allowed": [DC.ACCESS_LOCAL, DC.ACCESS_SSH]},
                    default_value = DC.ACCESS_LOCAL,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_HOST,
                    "Host where the testbed will be executed",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    default_value = "localhost",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_USER,
                    "User on the Host to execute the testbed",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    default_value = getpass.getuser(),
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_KEY,
                    "Path to SSH key to use for connecting",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.DEPLOYMENT_PORT,
                    "Port on the Host",
                    attributes.AttributeTypes.INTEGER,
                    attributes.IntegerAttribute,
                    default_value = 22,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.ROOT_DIRECTORY,
                    "Root directory for storing process files",
                    attributes.AttributeTypes.STRING,
                    attributes.StringAttribute,
                    default_value = ".",
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.USE_AGENT,
                    "Use -A option for forwarding of the authentication agent, if ssh access is used", 
                    attributes.AttributeTypes.BOOL,
                    attributes.BoolAttribute,
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.USE_SUDO,
                    "Use sudo to run the deamon process. This option only take flace when the server runs in daemon mode.", 
                    attributes.AttributeTypes.BOOL,
                    attributes.BoolAttribute,
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.CLEAN_ROOT,
                    "Clean server root directory (Warning: This will erase previous data).", 
                    attributes.AttributeTypes.BOOL,
                    attributes.BoolAttribute,
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.LOG_LEVEL,
                    "Log level for controller",
                    attributes.AttributeTypes.ENUM,
                    attributes.EnumAttribute,
                    args = {"allowed": [DC.ERROR_LEVEL, DC.DEBUG_LEVEL]},
                    default_value = DC.ERROR_LEVEL,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.RECOVERY_POLICY,
                    "Specifies what action to take in the event of a failure.", 
                    attributes.AttributeTypes.ENUM,
                    attributes.EnumAttribute,
                    args = {"allowed": [DC.POLICY_FAIL, DC.POLICY_RECOVER, DC.POLICY_RESTART]},
                    default_value = DC.POLICY_FAIL,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attributes.AttributeInfo(
                    DC.RECOVER,
                    "Do not intantiate testbeds, rather, reconnect to already-running instances. Used to recover from a dead controller.", 
                    attributes.AttributeTypes.BOOL,
                    attributes.BoolAttribute,
                    default_value = False,
                    flags = attributes.AttributeFlags.ExecReadOnly | \
                            attributes.AttributeFlags.ExecImmutable | \
                            attributes.AttributeFlags.DesignInvisible | \
                            attributes.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )


class TestbedBoxFactory(ControllerBoxFactory):
    def __init__(self, testbed_id, box_id, clazz):
        super(TestbedBoxFactory, self).__init__(testbed_id, box_id, clazz)
        self.add_container_box_id("Experiment")

    def create(self, guid, experiment):
        box = super(TestbedBoxFactory, self).create(guid, experiment)
        experiment.add_box(box)
        return box


class ExperimentBox(Box):
    def __init__(self, factory):
        super(ExperimentBox, self).__init__(0, factory, None)
        self._guid_generator = GuidGenerator()

    def next_guid(self, guid):
        return self._guid_generator.next(guid)

class ExperimentBoxFactory(ControllerBoxFactory):
    def __init__(self):
        super(ExperimentBoxFactory, self).__init__(None, "Experiment", ExperimentBox)

    def create(self):
        box = ExperimentBox(self)
        # add attributes
        for attr_info in self._attrs_info.values():
            clazz = attr_info.clazz
            attr = clazz(attr_info)
            box.add_attribute(attr)
        # add connector
        for connector_name in self._connectors.keys():
            box.add_connector(connector_name)
        return box


def create_experiment():
    factory = ExperimentBoxFactory()
    return factory.create()

def create_provider():
    # this factory provider instance will hold reference to all available factories 
    return BoxFactoryProvider()


