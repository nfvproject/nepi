#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute, AttributesMap
import sys

class VersionedMetadataInfo(object):
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
            "code": connection function to invoke upon connection creation
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
    def factories_order(self):
        """ list of factory ids that indicates the order in which the elements
        should be instantiated.
        """
        raise NotImplementedError

    @property
    def factories_info(self):
        """ dictionary of dictionaries of factory specific information
            factory_id: dict({
                "allow_addresses": whether the box allows adding IP addresses,
                "allow_routes": wether the box allows adding routes,
                "help": help text,
                "category": category the element belongs to,
                "create_function": function for element instantiation,
                "start_function": function for element starting,
                "stop_function": function for element stoping,
                "status_function": function for retrieving element status,
                "factory_attributes": list of references to attribute_ids,
                "box_attributes": list of regerences to attribute_ids,
                "traces": list of references to trace_id
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
             })
            ]
        """
        raise NotImplementedError

class Metadata(object):
    def __init__(self, testbed_id, version):
        self._version = version
        self._testbed_id = testbed_id
        metadata_module = self._load_versioned_metadata_module()
        self._metadata = metadata_module.VersionedMetadataInfo()

    @property
    def factories_order(self):
        return self._metadata.factories_order

    def testbed_attributes(self):
        attributes = AttributesMap()
        for attribute_info in self._metadata.testbed_attributes.values():
            name = attribute_info["name"]
            help = attribute_info["help"]
            type = attribute_info["type"] 
            value = attribute_info["value"]
            range = attribute_info["range"]
            allowed = attribute_info["allowed"]
            flags =  attribute_info["flags"] if "flags" in attribute_info \
                    else Attribute.NoFlags
            validation_function = attribute_info["validation_function"]
            attributes.add_attribute(name, help, type, value, 
                    range, allowed, flags, validation_function)
        return attributes            

    def build_design_factories(self):
        from nepi.core.design import Factory
        factories = list()
        for factory_id, info in self._metadata.factories_info.iteritems():
            help = info["help"]
            category = info["category"]
            allow_addresses = info["allow_addresses"] \
                    if "allow_addresses" in info else False
            allow_routes = info["allow_routes"] \
                    if "allow_routes" in info else False
            factory = Factory(factory_id, allow_addresses, allow_routes,
                    help, category)
            self._add_attributes(factory, info, "factory_attributes")
            self._add_attributes(factory, info, "box_attributes", True)
            self._add_design_traces(factory, info)
            self._add_design_connector_types(factory, info)
            factories.append(factory)
        return factories

    def build_execute_factories(self):
        from nepi.core.execute import Factory
        factories = list()
        for factory_id, info in self._metadata.factories_info.iteritems():
            create_function = info["create_function"]
            start_function = info["start_function"]
            stop_function = info["stop_function"]
            status_function = info["status_function"]
            allow_addresses = info["allow_addresses"] \
                    if "allow_addresses" in info else False
            allow_routes = info["allow_routes"] \
                    if "allow_routes" in info else False
            factory = Factory(factory_id, create_function, start_function,
                    stop_function, status_function, allow_addresses, 
                    allow_routes)
            self._add_attributes(factory, info, "factory_attributes")
            self._add_attributes(factory, info, "box_attributes", True)
            self._add_execute_traces(factory, info)
            self._add_execute_connector_types(factory, info)
            factories.append(factory)
        return factories

    def _load_versioned_metadata_module(self):
        mod_name = "nepi.testbeds.%s.metadata_v%s" % (self._testbed_id.lower(),
                self._version)
        if not mod_name in sys.modules:
            __import__(mod_name)
        return sys.modules[mod_name]

    def _add_attributes(self, factory, info, attributes_key, 
            box_attributes = False):
        if attributes_key in info:
            for attribute_id in info[attributes_key]:
                try:
                    attribute_info = self._metadata.attributes[attribute_id]
                except:
                   print "\"%s\"," % attribute_id
                   continue
                name = attribute_info["name"]
                help = attribute_info["help"]
                type = attribute_info["type"] 
                value = attribute_info["value"]
                range = attribute_info["range"]
                allowed = attribute_info["allowed"]
                flags = attribute_info["flags"] if "flags" in attribute_info \
                        and attribute_info["flags"] != None \
                        else Attribute.NoFlags
                validation_function = attribute_info["validation_function"]
                if box_attributes:
                    factory.add_box_attribute(name, help, type, value, range, 
                            allowed, flags, validation_function)
                else:
                    factory.add_attribute(name, help, type, value, range, 
                            allowed, flags, validation_function)

    def _add_design_traces(self, factory, info):
        if "traces" in info:
            for trace in info["traces"]:
                trace_info = self._metadata.traces[trace]
                trace_id = trace_info["name"]
                help = trace_info["help"]
                factory.add_trace(trace_id, help)

    def _add_execute_traces(self, factory, info):
        if "traces" in info:
            for trace in info["traces"]:
                trace_info = self._metadata.traces[trace]
                trace_id = trace_info["name"]
                factory.add_trace(trace_id)

    def _add_design_connector_types(self, factory, info):
        from nepi.core.design import ConnectorType
        if "connector_types" in info:
            connections = dict()
            for connection in self._metadata.connections:
                from_ = connection["from"]
                to = connection["to"]
                can_cross = connection["can_cross"]
                if from_ not in connections:
                    connections[from_] = list()
                if to not in connections:
                    connections[to] = list()
                connections[from_].append((to, can_cross))
                connections[to].append((from_, can_cross))
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
                for (to, can_cross) in connections[(testbed_id, factory_id, 
                        name)]:
                    (testbed_id_to, factory_id_to, name_to) = to
                    connector_type.add_allowed_connection(testbed_id_to, 
                            factory_id_to, name_to, can_cross)
                factory.add_connector_type(connector_type)

    def _add_execute_connector_types(self, factory, info):
        from nepi.core.execute import ConnectorType
        if "connector_types" in info:
            from_connections = dict()
            to_connections = dict()
            for connection in self._metadata.connections:
                from_ = connection["from"]
                to = connection["to"]
                can_cross = connection["can_cross"]
                code = connection["code"]
                if from_ not in from_connections:
                    from_connections[from_] = list()
                if to not in to_connections:
                    to_connections[to] = list()
                from_connections[from_].append((to, can_cross, code))
                to_connections[to].append((from_, can_cross, code))
            for connector_id in info["connector_types"]:
                connector_type_info = self._metadata.connector_types[
                        connector_id]
                name = connector_type_info["name"]
                max = connector_type_info["max"]
                min = connector_type_info["min"]
                testbed_id = self._testbed_id
                factory_id = factory.factory_id
                connector_type = ConnectorType(testbed_id, factory_id, name, 
                        max, min)
                connector_key = (testbed_id, factory_id, name)
                if connector_key in to_connections:
                    for (from_, can_cross, code) in to_connections[connector_key]:
                        (testbed_id_from, factory_id_from, name_from) = from_
                        connector_type.add_from_connection(testbed_id_from, 
                                factory_id_from, name_from, can_cross, code)
                if connector_key in from_connections:
                    for (to, can_cross, code) in from_connections[(testbed_id, 
                            factory_id, name)]:
                        (testbed_id_to, factory_id_to, name_to) = to
                        connector_type.add_to_connection(testbed_id_to, 
                                factory_id_to, name_to, can_cross, code)
                factory.add_connector_type(connector_type)
 
