#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core import description 
import sys

TESTBED_ID = "netns"

def add_connector_types(factory, connector_types_metadata):
    for (connector_type_id, help, name, max, min, 
            allowed_connector_type_ids) in connector_types_metadata:
        factory.add_connector_type(connector_type_id, help, name, max,
            min, allowed_connector_type_ids)

def add_traces(factory, traces_metadata):
    for (name, help) in traces_metadata: 
            factory.add_trace(name, help)

def add_attributes(factory, attributes_metadata):
    for (name, help, type, value, range, allowed, readonly, 
            validation_function) in attributes_metadata:
        factory.add_attribute(name, help, type, value, range, allowed,
            readonly, validation_function)

def add_element_attributes(factory, element_attributes_metadata):
    for (name, help, type, value, range, allowed, readonly, 
            validation_function) in element_attributes_metadata:
            factory.add_element_attribute(name, help, type, value, range,
                    allowed, readonly, validation_function)
           
def create_factory_from_metadata(factory_id, info):
        help = info["help"]
        category = info["category"]
        display_name = info["display_name"]
        factory_type = info["factory_type"] if "factory_type" in info else None
        if factory_type == "addressable":
            family = info["family"]
            max_addresses = info["max_addresses"]
            factory = description.AddressableElementFactory(factory_id, 
                    display_name, family, max_addresses, help, category)
        elif factory_type == "routing":
            factory = description.RoutingTableElementFactory(factory_id, 
                    display_name, help, category)
        else:
            factory = description.ElementFactory(factory_id, display_name, help, category)
        if "connector_types" in info:
            add_connector_types(factory, info["connector_types"])
        if "traces" in info:
            add_traces(factory, info["traces"])
        if "attributes" in info:
            add_attributes(factory, info["attributes"])
        if "element_attributes" in info:
            add_element_attributes(factory, info["element_attributes"])
        return factory

def create_factories(version):
    factories = list()
    mod_name = "%s.metadata_v%s" % (__name__, version)
    if not mod_name in sys.modules:
        __import__(mod_name)
    metadata = sys.modules[mod_name].get_metadata()
    for factory_id, info in metadata.iteritems():
        factory = create_factory_from_metadata(factory_id, info)
        factories.append(factory)
    return factories

def create_provider(version):
    provider = description.FactoriesProvider()
    for factory in create_factories(version):
        provider.add_factory(factory)
    return provider

def create_description_instance(guid_generator, version, provider):
    return description.TestbedDescription(guid_generator, TESTBED_ID, version, 
        provider)

