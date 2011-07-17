#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute, AttributesMap
from nepi.core.connector import ConnectorType
from nepi.core.factory import Factory
import sys
import getpass
from nepi.util import tags, validation
from nepi.util.constants import ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP, \
        DeploymentConfiguration as DC, \
        AttributeCategories as AC

class MetadataInfo(object):
    @property
    def connector_types(self):
        """ dictionary of dictionaries with allowed connection information.
            connector_id: dict({
                "help": help text, 
                "name": connector type name,
                "max": maximum number of connections allowed (-1 for no limit),
                "min": minimum number of connections allowed
            }),
        """
        raise NotImplementedError

    @property
    def connections(self):
        """ array of dictionaries with allowed connection information.
        dict({
            "from": (testbed_id1, factory_id1, connector_type_name1),
            "to": (testbed_id2, factory_id2, connector_type_name2),
            "init_code": connection function to invoke for connection initiation
            "compl_code": connection function to invoke for connection 
                completion
            "can_cross": whether the connection can be done across testbed 
                            instances
         }),
        """
        raise NotImplementedError

    @property
    def attributes(self):
        """ dictionary of dictionaries of all available attributes.
            attribute_id: dict({
                "name": attribute name,
                "help": help text,
                "type": attribute type, 
                "value": default attribute value,
                "range": (maximum, minimun) values else None if not defined,
                "allowed": array of posible values,
                "flags": attributes flags,
                "validation_function": validation function for the attribute
                "category": category for the attribute
            })
        """
        raise NotImplementedError

    @property
    def traces(self):
        """ dictionary of dictionaries of all available traces.
            trace_id: dict({
                "name": trace name,
                "help": help text
            })
        """
        raise NotImplementedError

    @property
    def create_order(self):
        """ list of factory ids that indicates the order in which the elements
        should be instantiated.
        """
        raise NotImplementedError

    @property
    def configure_order(self):
        """ list of factory ids that indicates the order in which the elements
        should be configured.
        """
        raise NotImplementedError

    @property
    def preconfigure_order(self):
        """ list of factory ids that indicates the order in which the elements
        should be preconfigured.
        
        Default: same as configure_order
        """
        return self.configure_order

    @property
    def prestart_order(self):
        """ list of factory ids that indicates the order in which the elements
        should be prestart-configured.
        
        Default: same as configure_order
        """
        return self.configure_order

    @property
    def start_order(self):
        """ list of factory ids that indicates the order in which the elements
        should be started.
        
        Default: same as configure_order
        """
        return self.configure_order

    @property
    def factories_info(self):
        """ dictionary of dictionaries of factory specific information
            factory_id: dict({
                "help": help text,
                "category": category the element belongs to,
                "create_function": function for element instantiation,
                "start_function": function for element starting,
                "stop_function": function for element stoping,
                "status_function": function for retrieving element status,
                "preconfigure_function": function for element preconfiguration,
                    (just after connections are made, 
                    just before netrefs are resolved)
                "configure_function": function for element configuration,
                "prestart_function": function for pre-start
                    element configuration (just before starting applications),
                    useful for synchronization of background setup tasks or
                    lazy instantiation or configuration of attributes
                    that require connection/cross-connection state before
                    being created.
                    After this point, all applications should be able to run.
                "factory_attributes": list of references to attribute_ids,
                "box_attributes": list of regerences to attribute_ids,
                "traces": list of references to trace_id
                "tags": list of references to tag_id
                "connector_types": list of references to connector_types
           })
        """
        raise NotImplementedError

    @property
    def testbed_attributes(self):
        """ dictionary of attributes for testbed instance configuration
            attributes_id = dict({
                "name": attribute name,
                "help": help text,
                "type": attribute type, 
                "value": default attribute value,
                "range": (maximum, minimun) values else None if not defined,
                "allowed": array of posible values,
                "flags": attributes flags,
                "validation_function": validation function for the attribute
                "category": category for the attribute
             })
            ]
        """
        raise NotImplementedError

    @property
    def testbed_id(self):
        """ ID for the testbed """
        raise NotImplementedError

    @property
    def testbed_version(self):
        """ version for the testbed """
        raise NotImplementedError

class Metadata(object):
    # These attributes should be added to all boxes
    STANDARD_BOX_ATTRIBUTES = dict({
        "label" : dict({
            "name" : "label",
            "validation_function" : validation.is_string,
            "type" : Attribute.STRING,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "help" : "A unique identifier for referring to this box",
        }),
     })

    # These are the attribute definitions for tagged attributes
    STANDARD_TAGGED_ATTRIBUTES_DEFINITIONS = dict({
        "maxAddresses" : dict({
            "name" : "maxAddresses",
            "validation_function" : validation.is_integer,
            "type" : Attribute.INTEGER,
            "value" : 1,
            "flags" : Attribute.DesignReadOnly |\
                    Attribute.ExecInvisible |\
                    Attribute.Metadata,
            "help" : "The maximum allowed number of addresses",
            }),
        })

    # Attributes to be added to all boxes with specific tags
    STANDARD_TAGGED_BOX_ATTRIBUTES = dict({
        tags.ALLOW_ADDRESSES : ["maxAddresses"],
        tags.HAS_ADDRESSES : ["maxAddresses"],
    })

    # These attributes should be added to all testbeds
    STANDARD_TESTBED_ATTRIBUTES = dict({
        "home_directory" : dict({
            "name" : "homeDirectory",
            "validation_function" : validation.is_string,
            "help" : "Path to the directory where traces and other files will be stored",
            "type" : Attribute.STRING,
            "value" : "",
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            }),
        "label" : dict({
            "name" : "label",
            "validation_function" : validation.is_string,
            "type" : Attribute.STRING,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "help" : "A unique identifier for referring to this testbed",
            }),
        })
    
    # These attributes should be added to all testbeds
    DEPLOYMENT_ATTRIBUTES = dict({
        # TESTBED DEPLOYMENT ATTRIBUTES
        DC.DEPLOYMENT_ENVIRONMENT_SETUP : dict({
            "name" : DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "validation_function" : validation.is_string,
            "help" : "Shell commands to run before spawning TestbedController processes",
            "type" : Attribute.STRING,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "category" : AC.CATEGORY_DEPLOYMENT,
        }),
        DC.DEPLOYMENT_MODE: dict({
            "name" : DC.DEPLOYMENT_MODE,
            "help" : "Instance execution mode",
            "type" : Attribute.ENUM,
            "value" : DC.MODE_SINGLE_PROCESS,
            "allowed" : [
                    DC.MODE_DAEMON,
                    DC.MODE_SINGLE_PROCESS
                ],
           "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_enum,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.DEPLOYMENT_COMMUNICATION : dict({
            "name" : DC.DEPLOYMENT_COMMUNICATION,
            "help" : "Instance communication mode",
            "type" : Attribute.ENUM,
            "value" : DC.ACCESS_LOCAL,
            "allowed" : [
                    DC.ACCESS_LOCAL,
                    DC.ACCESS_SSH
                ],
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_enum,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.DEPLOYMENT_HOST : dict({
            "name" : DC.DEPLOYMENT_HOST,
            "help" : "Host where the testbed will be executed",
            "type" : Attribute.STRING,
            "value" : "localhost",
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_string,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.DEPLOYMENT_USER : dict({
            "name" : DC.DEPLOYMENT_USER,
            "help" : "User on the Host to execute the testbed",
            "type" : Attribute.STRING,
            "value" : getpass.getuser(),
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_string,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.DEPLOYMENT_KEY : dict({
            "name" : DC.DEPLOYMENT_KEY,
            "help" : "Path to SSH key to use for connecting",
            "type" : Attribute.STRING,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_string,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.DEPLOYMENT_PORT : dict({
            "name" : DC.DEPLOYMENT_PORT,
            "help" : "Port on the Host",
            "type" : Attribute.INTEGER,
            "value" : 22,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_integer,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.ROOT_DIRECTORY : dict({
            "name" : DC.ROOT_DIRECTORY,
            "help" : "Root directory for storing process files",
            "type" : Attribute.STRING,
            "value" : ".",
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_string, # TODO: validation.is_path
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.USE_AGENT : dict({
            "name" : DC.USE_AGENT,
            "help" : "Use -A option for forwarding of the authentication agent, if ssh access is used", 
            "type" : Attribute.BOOL,
            "value" : False,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_bool,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.LOG_LEVEL : dict({
            "name" : DC.LOG_LEVEL,
            "help" : "Log level for instance",
            "type" : Attribute.ENUM,
            "value" : DC.ERROR_LEVEL,
            "allowed" : [
                    DC.ERROR_LEVEL,
                    DC.DEBUG_LEVEL
                ],
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_enum,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        DC.RECOVER : dict({
            "name" : DC.RECOVER,
            "help" : "Do not intantiate testbeds, rather, reconnect to already-running instances. Used to recover from a dead controller.", 
            "type" : Attribute.BOOL,
            "value" : False,
            "flags" : Attribute.ExecReadOnly |\
                    Attribute.ExecImmutable |\
                    Attribute.Metadata,
            "validation_function" : validation.is_bool,
            "category" : AC.CATEGORY_DEPLOYMENT,
            }),
        })
  
    # These attributes could appear in the boxes attribute list
    STANDARD_BOX_ATTRIBUTE_DEFINITIONS = dict({
        "tun_proto" : dict({
            "name" : "tun_proto", 
            "help" : "TUNneling protocol used",
            "type" : Attribute.STRING,
            "flags" : Attribute.DesignInvisible | \
                    Attribute.ExecInvisible | \
                    Attribute.ExecImmutable | \
                    Attribute.Metadata,
            "validation_function" : validation.is_string,
            }),
        "tun_key" : dict({
            "name" : "tun_key", 
            "help" : "Randomly selected TUNneling protocol cryptographic key. "
                     "Endpoints must agree to use the minimum (in lexicographic order) "
                     "of both the remote and local sides.",
            "type" : Attribute.STRING,
            "flags" : Attribute.DesignInvisible | \
                    Attribute.ExecInvisible | \
                    Attribute.ExecImmutable | \
                    Attribute.Metadata,
            "validation_function" : validation.is_string,
            }),
        "tun_addr" : dict({
            "name": "tun_addr", 
            "help" : "Address (IP, unix socket, whatever) of the tunnel endpoint",
            "type" : Attribute.STRING,
            "flags" : Attribute.DesignInvisible | \
                    Attribute.ExecInvisible | \
                    Attribute.ExecImmutable | \
                    Attribute.Metadata,
            "validation_function" : validation.is_string,
            }),
        "tun_port" : dict({
            "name" : "tun_port", 
            "help" : "IP port of the tunnel endpoint",
            "type" : Attribute.INTEGER,
            "flags" : Attribute.DesignInvisible | \
                    Attribute.ExecInvisible | \
                    Attribute.ExecImmutable | \
                    Attribute.Metadata,
            "validation_function" : validation.is_integer,
            }),
        ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP : dict({
            "name" : ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,
            "help" : "Commands to set up the environment needed to run NEPI testbeds",
            "type" : Attribute.STRING,
            "flags" : Attribute.DesignInvisible | \
                    Attribute.ExecInvisible | \
                    Attribute.ExecImmutable | \
                    Attribute.Metadata,
            "validation_function" : validation.is_string
            }),
        })
    
    STANDARD_TESTBED_ATTRIBUTES.update(DEPLOYMENT_ATTRIBUTES.copy())

    def __init__(self, testbed_id):
        self._testbed_id = testbed_id
        metadata_module = self._load_metadata_module()
        self._metadata = metadata_module.MetadataInfo()
        if testbed_id != self._metadata.testbed_id:
            raise RuntimeError("Bad testbed id. Asked for %s, got %s" % \
                    (testbed_id, self._metadata.testbed_id ))

    @property
    def create_order(self):
        return self._metadata.create_order

    @property
    def configure_order(self):
        return self._metadata.configure_order

    @property
    def preconfigure_order(self):
        return self._metadata.preconfigure_order

    @property
    def prestart_order(self):
        return self._metadata.prestart_order

    @property
    def start_order(self):
        return self._metadata.start_order

    @property
    def testbed_version(self):
        return self._metadata.testbed_version

    @property
    def testbed_id(self):
        return self._testbed_id

    def testbed_attributes(self):
        attributes = AttributesMap()
        testbed_attributes = self._testbed_attributes()
        self._add_attributes(attributes.add_attribute, testbed_attributes)
        return attributes

    def build_factories(self):
        factories = list()
        for factory_id, info in self._metadata.factories_info.iteritems():
            create_function = info.get("create_function")
            start_function = info.get("start_function")
            stop_function = info.get("stop_function")
            status_function = info.get("status_function")
            configure_function = info.get("configure_function")
            preconfigure_function = info.get("preconfigure_function")
            prestart_function = info.get("prestart_function")
            help = info["help"]
            category = info["category"]
            factory = Factory(factory_id, 
                    create_function, 
                    start_function,
                    stop_function, 
                    status_function, 
                    configure_function, 
                    preconfigure_function,
                    prestart_function,
                    help,
                    category)
                    
            factory_attributes = self._factory_attributes(info)
            self._add_attributes(factory.add_attribute, factory_attributes)
            box_attributes = self._box_attributes(info)
            self._add_attributes(factory.add_box_attribute, box_attributes)
            
            self._add_traces(factory, info)
            self._add_tags(factory, info)
            self._add_connector_types(factory, info)
            factories.append(factory)
        return factories

    def _load_metadata_module(self):
        mod_name = "nepi.testbeds.%s.metadata" % (self._testbed_id.lower())
        if not mod_name in sys.modules:
            __import__(mod_name)
        return sys.modules[mod_name]

    def _testbed_attributes(self):
        # standar attributes
        attributes = self.STANDARD_TESTBED_ATTRIBUTES.copy()
        # custom attributes
        attributes.update(self._metadata.testbed_attributes.copy())
        return attributes
        
    def _factory_attributes(self, info):
        tagged_attributes = self._tagged_attributes(info)
        if "factory_attributes" in info:
            definitions = self._metadata.attributes.copy()
            # filter attributes corresponding to the factory_id
            factory_attributes = self._filter_attributes(info["factory_attributes"], 
                definitions)
        else:
            factory_attributes = dict()
        attributes = dict(tagged_attributes.items() + \
                factory_attributes.items())
        return attributes

    def _box_attributes(self, info):
        tagged_attributes = self._tagged_attributes(info)
        if "box_attributes" in info:
            definitions = self.STANDARD_BOX_ATTRIBUTE_DEFINITIONS.copy()
            definitions.update(self._metadata.attributes)
            box_attributes = self._filter_attributes(info["box_attributes"], 
                definitions)
        else:
            box_attributes = dict()
        attributes = dict(tagged_attributes.items() + \
                box_attributes.items())
        attributes.update(self.STANDARD_BOX_ATTRIBUTES.copy())
        return attributes

    def _tagged_attributes(self, info):
        tagged_attributes = dict()
        for tag_id in info.get("tags", []):
            if tag_id in self.STANDARD_TAGGED_BOX_ATTRIBUTES:
                attr_list = self.STANDARD_TAGGED_BOX_ATTRIBUTES[tag_id]
                attributes = self._filter_attributes(attr_list,
                    self.STANDARD_TAGGED_ATTRIBUTES_DEFINITIONS)
                tagged_attributes.update(attributes)
        return tagged_attributes

    def _filter_attributes(self, attr_list, definitions):
        # filter attributes not corresponding to the factory
        attributes = dict((attr_id, definitions[attr_id]) \
           for attr_id in attr_list)
        return attributes

    def _add_attributes(self, add_attr_func, attributes):
        for attr_id, attr_info in attributes.iteritems():
            name = attr_info["name"]
            help = attr_info["help"]
            type = attr_info["type"] 
            value = attr_info.get("value")
            range = attr_info.get("range")
            allowed = attr_info.get("allowed")
            flags = attr_info.get("flags")
            validation_function = attr_info["validation_function"]
            category = attr_info.get("category")
            add_attr_func(name, help, type, value, range, allowed, flags, 
                    validation_function, category)

    def _add_traces(self, factory, info):
        for trace_id in info.get("traces", []):
            trace_info = self._metadata.traces[trace_id]
            name = trace_info["name"]
            help = trace_info["help"]
            factory.add_trace(name, help)

    def _add_tags(self, factory, info):
        for tag_id in info.get("tags", []):
            factory.add_tag(tag_id)

    def _add_connector_types(self, factory, info):
        if "connector_types" in info:
            from_connections = dict()
            to_connections = dict()
            for connection in self._metadata.connections:
                from_ = connection["from"]
                to = connection["to"]
                can_cross = connection["can_cross"]
                init_code = connection.get("init_code")
                compl_code = connection.get("compl_code")
                if from_ not in from_connections:
                    from_connections[from_] = list()
                if to not in to_connections:
                    to_connections[to] = list()
                from_connections[from_].append((to, can_cross, init_code, 
                    compl_code))
                to_connections[to].append((from_, can_cross, init_code,
                    compl_code))
            for connector_id in info["connector_types"]:
                connector_type_info = self._metadata.connector_types[
                        connector_id]
                name = connector_type_info["name"]
                help = connector_type_info["help"]
                max = connector_type_info["max"]
                min = connector_type_info["min"]
                testbed_id = self._testbed_id
                factory_id = factory.factory_id
                connector_type = ConnectorType(testbed_id, factory_id, name, 
                        help, max, min)
                connector_key = (testbed_id, factory_id, name)
                if connector_key in to_connections:
                    for (from_, can_cross, init_code, compl_code) in \
                            to_connections[connector_key]:
                        (testbed_id_from, factory_id_from, name_from) = from_
                        connector_type.add_from_connection(testbed_id_from, 
                                factory_id_from, name_from, can_cross, 
                                init_code, compl_code)
                if connector_key in from_connections:
                    for (to, can_cross, init_code, compl_code) in \
                            from_connections[(testbed_id, factory_id, name)]:
                        (testbed_id_to, factory_id_to, name_to) = to
                        connector_type.add_to_connection(testbed_id_to, 
                                factory_id_to, name_to, can_cross, init_code,
                                compl_code)
                factory.add_connector_type(connector_type)
 
