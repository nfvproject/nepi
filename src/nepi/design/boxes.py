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
        super(FactoriesProvider, self).__init__()
        self._factories = dict()
        self.experiment = experiment

    @property
    def factories(self):
        return self._factories.values()

    def factory(self, box_id):
        return self._factories[box_id]

    def add_factory(self, factory):
        if factory.box_id not in self._factories.keys():
                self._factories[factory.box_id] = factory

    def remove_factory(self, factory):
        del self._factories[factory.box_id]

    def create(self, box_id, guid = None):
        guid = self.experiment.guid_generator.next(guid)
        factory = self.factory(box_id)
        box = factory.create(guid, self.experiment)
        return box


class BoxFactory(tags.Taggable):
    """ The Factory instances hold information about a Box class
    and 'know' how to create a box instance."""
    def __init__(self, tesbed_id, box_id, clazz):
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
        # List of boxes types that can be aggregated to the object
        self._box_ids = list()
        # connectors -- list of available connectors for the box
        self._connectors = dict()

        self.add_attribute_info(
                attribute.AttributeInfo(
                    "label", 
                    "A unique user-defined identifier for referring to this box",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly |\
                        attribute.AttributeFlags.ExecImmutable |\
                        attribute.AttributeFlags.Metadata
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
        self._connectors[connector.connector_type.name] = connector

    def add_attribute_info(self, attr_info):
        self._attrs_info[attr_info.name] = attr_info

    def get_attribute_info(self, attr_name, info = "help"):
        attr = self._attrs_info[attr_name]
        return getattr(attr, info)

    def list_attributes(self):
        return self._attrs_info.keys()

    def add_box_id(self, box_id):
        self._aggr_boxes.append(box_id)

    def list_box_ids(self):
        return self._box_ids

    def create(self, guid, experiment, container = None):
        box = self._clazz(guid, self, experiment)
        if container:
            container.add_box(box)
        # add attributes
        for attr_info in self._attrs_info:
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
        return "Box(%s, %s, %s)" % (self.guid, self.factory.type_id, 
                self.factory.testbed_id)

    @property
    def guid(self):
        return self._guid

    @property
    def factory(self):
        return self._factory

    @property
    def graphical_info(self):
        return self._graphical_info

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
        if connector.can_connect():
            could_connect = True
            if connect_other_side:
                could_connect = other_box.connect(other_connector_name, self, 
                        connector_name, False)
            if could_connect:
                self._connections[connector_name].append((other_box, other_connector_name))
                return True
        self._logger.warn("connect(): could not connect %d %s from %d %s.", 
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
        self._logger.warn("disconnect(): could not disconnect %d %s from %d %s.", 
                    self.guid, connector_name, other_box.guid, other_connector_name)
        return False

    def list_connections(self):
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
        box_id = box.factory.box_id
        box_ids = self.factory.list_box_ids()
        if bid in box_ids:
            box.container = self
            self._boxes[guid] = box
        else:
            self._logger.warn("add_box(): Wrong box type %s to add to box type %s.", 
                    box_id, self.factory.box_id)

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


class IPAdressBoxFactory(BoxFactory):
    def __init__(self, tesbed_id, box_id, clazz):
        super(IPAddressBoxFactory, self).__init__(testbed_id, box_id, clazz)
        
        self.add_tag(tags.ADDRESS)
        
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "Address", 
                    "IP Address number", 
                    attribute.AttributeTypes.STRING,
                    attribute.IPAttribute,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "NetPrefix", 
                    "Network prefix for the address", 
                    attribute.AttributeTypes.INTEGER,
                    attribute.IntegerAttribute,
                    args = {"min":0, "max":128},
                    default_value = 24,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "Broadcast", 
                    "Broadcast network address", 
                    attribute.AttributeTypes.STRING,
                    attribute.IPv4Attribute,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )


class RouteBoxFactory(BoxFactory):
    def __init__(self, tesbed_id, box_id, clazz):
        super(RouteBoxFactory, self).__init__(testbed_id, box_id, clazz)
        
        self.add_tag(tags.ROUTE)

        self.add_attribute_info(
                attribute.AttributeInfo(
                    "Destination", 
                    "Network destination address", 
                    attribute.AttributeTypes.STRING,
                    attribute.NetRefAttribute,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "NetPrefix", 
                    "Network prefix for the address", 
                    attribute.AttributeTypes.INTEGER,
                    attribute.IntegerAttribute,
                    args = {"min":0, "max":128},
                    default_value = 24,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "NextHop", 
                    "Address of the next hop", 
                    attribute.AttributeTypes.STRING,
                    attribute.IPAttribute,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "Metric", 
                    "Routing metric", 
                    attribute.AttributeTypes.INTEGER,
                    attribute.IntegerAttribute,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "Default gateway", 
                    "Indicate if this route points to the default gateway", 
                    attribute.AttributeTypes.BOOL,
                    attribute.BoolAttribute,
                    default_value = False,
                    flags = attribute.AttributeFlags.NoDefaultValue
                    )
                )


class TunnelBoxFactory(BoxFactory):
    def __init__(self, tesbed_id, box_id, clazz):
        super(TunnelBoxFactory, self).__init__(testbed_id, box_id, clazz)

        self.add_tag(tags.TUNNEL)

        self.add_attribute_info(
                attribute.AttributeInfo(
                    "tunProto", 
                    "TUNneling protocol used",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "tunKey",
                    "Randomly selected TUNneling protocol cryptographic key. "
                     "Endpoints must agree to use the minimum (in lexicographic order) "
                     "of both the remote and local sides.",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "tunAddr",
                    "Address (IP, unix socket, whatever) of the tunnel endpoint",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "tunPort",
                    "IP port of the tunnel endpoint",
                    attribute.AttributeTypes.INTEGER,
                    attribute.IntegerAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    "tunCipher",
                    "Cryptographic cipher used for tunnelling",
                    attribute.AttributeTypes.ENUM,
                    attribute.EnumAttribute,
                    args = {'allowed': ["AES", "Blowfish", "DES3", "DES", "PLAIN"]},
                    default_value = "AES",
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata
                    )
                )


class ControllerBoxFactory(BoxFactory):
    def __init__(self, tesbed_id, box_id, clazz):
        super(ControllerBoxFactory, self).__init__(testbed_id, box_id, clazz)

        self.add_tag(tags.CONTROLLER)

        self.add_attribute_info(
                attribute.AttributeInfo(
                    "homeDirectory", 
                    "Path to the directory where traces and other files will be stored",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    default_value = "",
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_ENVIRONMENT_SETUP,
                    "Shell commands to run before spawning Controller processes",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_ENVIRONMENT_MODE,
                    "Controller execution mode",
                    attribute.AttributeTypes.ENUM,
                    attribute.EnumAttribute,
                    args = {"allowed": [DC.MODE_DAEMON, DC.MODE_SINGLE_PROCESS]},
                    default_value = DC.MODE_SINGLE_PROCESS,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_ENVIRONMENT_COMMUNICATION,
                    "Controller communication mode",
                    attribute.AttributeTypes.ENUM,
                    attribute.EnumAttribute,
                    args = {"allowed": [DC.ACCESS_LOCAL, DC.ACCESS_SSH]},
                    default_value = DC.ACCESS_LOCAL,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_HOST,
                    "Host where the testbed will be executed",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    default_value = "localhost",
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_USER,
                    "User on the Host to execute the testbed",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    default_value = getpass.getuser(),
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_KEY,
                    "Path to SSH key to use for connecting",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.DEPLOYMENT_PORT,
                    "Port on the Host",
                    attribute.AttributeTypes.INTEGER,
                    attribute.IntegerAttribute,
                    default_value = 22,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.ROOT_DIRECTORY,
                    "Root directory for storing process files",
                    attribute.AttributeTypes.STRING,
                    attribute.StringAttribute,
                    default_value = ".",
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.USE_AGENT,
                    "Use -A option for forwarding of the authentication agent, if ssh access is used", 
                    attribute.AttributeTypes.BOOL,
                    attribute.BoolAttribute,
                    default_value = False,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.USE_SUDO,
                    "Use sudo to run the deamon process. This option only take flace when the server runs in daemon mode.", 
                    attribute.AttributeTypes.BOOL,
                    attribute.BoolAttribute,
                    default_value = False,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.CLEAN_ROOT,
                    "Clean server root directory (Warning: This will erase previous data).", 
                    attribute.AttributeTypes.BOOL,
                    attribute.BoolAttribute,
                    default_value = False,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.LOG_LEVEL,
                    "Log level for controller",
                    attribute.AttributeTypes.ENUM,
                    attribute.EnumAttribute,
                    args = {"allowed": [DC.ERROR_LEVEL, DC.DEBUG_LEVEL]},
                    default_value = DC.ERROR_LEVEL,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.RECOVERY_POLICY,
                    "Specifies what action to take in the event of a failure.", 
                    attribute.AttributeTypes.ENUM,
                    attribute.EnumAttribute,
                    args = {"allowed": [DC.POLICY_FAIL, DC.POLICY_RECOVER, DC.POLICY_RESTART]},
                    default_value = DC.POLICY_FAIL,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )
        self.add_attribute_info(
                attribute.AttributeInfo(
                    DC.RECOVERY,
                    "Do not intantiate testbeds, rather, reconnect to already-running instances. Used to recover from a dead controller.", 
                    attribute.AttributeTypes.BOOL,
                    attribute.BoolAttribute,
                    default_value = False,
                    flags = attribute.AttributeFlags.ExecReadOnly | \
                            attribute.AttributeFlags.ExecImmutable | \
                            attribute.AttributeFlags.DesignInvisible | \
                            attribute.AttributeFlags.Metadata,
                    tags = [tags.DEPLOYMENT],
                    )
                )


class TestbedBoxFactory(ControllerBoxFactory):
    def create(self, guid, experiment, container = None):
        box = super(TestbedBoxFactory, self).create(guid, experiment, None)
        experiment.add_box(box)
        return box


class ExperimentBox(Box):
    def __init__(self, guid, factory, None):
        super(ExperimentBox, self).__init__(guid, factory, None)
        self._guid_generator = GuidGenerator()

    def add_box(self, box):
        if tags.CONTROLLER not in box.tags:
            self._logger.warn("ExperimentBox.add_box(): wrong box %d, can only add boxes with tag CONTROLLER", 
                    box.factory.box_id)
            return 
        super(ExperimentBox, self).add_box(box)
 

def create_experiment():
    factory = ControllerFactory("all", "Experiment", ExperimentBox)
    return factory.create(0, None)

def create_provider():
    # this factory provider instance will hold reference to all available factories 
    return BoxFactoryProvider()


