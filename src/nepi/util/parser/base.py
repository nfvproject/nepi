#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

class ExperimentParser(object):
    def to_data(self, experiment_description):
        data = dict()
        for testbed_description in experiment_description.testbed_descriptions:
            guid = testbed_description.guid
            data[guid] = self.testbed_to_data(testbed_description)
            for box in testbed_description.boxes:
                data[box.guid] = self.box_to_data(guid, box)
        return data

    def testbed_to_data(self, testbed_description):
        elem = dict()
        elem["testbed_id"] = testbed_description.provider.testbed_id
        elem["testbed_version"] = testbed_description.provider.testbed_version
        return elem 

    def box_to_data(self, testbed_guid, box):
        elem = dict()
        elem["testbed_guid"] = testbed_guid
        elem["factory_id"] = box.factory_id
        fattrs = self.factory_attributes_to_data(box.factory_attributes)
        if fattrs:
            elem["factory_attributes"] = fattrs
        attrs = self.attributes_to_data(box.attributes)
        if attrs:
            elem["attributes"] = attrs
        traces = self.traces_to_data(box.traces)
        if traces:
            elem["traces"] = traces
        connections = self.connections_to_data(box.connectors)
        if connections:
            elem["connections"] = connections
        addresses = self.addresses_to_data(box.addresses)
        if addresses:
            elem["addresses"] = addresses
        routes = self.routes_to_data(box.routes)
        if routes:
            elem["routes"] = routes
        return elem

    def factory_attributes_to_data(self, attributes):
        fattrs = dict()
        for attribute in attributes:
            if attribute.modified:
                fattrs[attribute.name] = attribute.value
        return fattrs if len(fattrs) > 0 else None

    def attributes_to_data(self, attributes):
        attrs = dict()
        for attribute in attributes:
            if attribute.modified:
                attrs[attribute.name] = attribute.value
        return attrs if len(attrs) > 0 else None

    def traces_to_data(self, traces):
        trcs = list()
        for trace in traces:
            if trace.enabled:
                trcs.append(trace.name)
        return trcs if len(trcs) > 0 else None

    def connections_to_data(self, connectors):
        cnctrs = dict()
        for connector in connectors:
            cnxs = dict()
            for other_connector in connector.connections:
                guid = other_connector.box.guid
                cnxs[guid] = other_connector.connector_type.name
            if len(cnxs) > 0:
                cnctrs[connector.connector_type.name] = cnxs
        return cnctrs if len(cnctrs) > 0 else None

    def addresses_to_data(self, addresses):
        addrs = list()
        for address in addresses:
            addr = dict()
            for attribute in address.attributes:
                if attribute.modified:
                    addr[attribute.name] = attribute.value
            addrs.append(addr)
        return addrs if len(addrs) > 0 else None

    def routes_to_data(self, routes):
        rts = list()
        for route in routes:
            rt = dict()
            for attribute in route.attibutes:
                if attribute.modified:
                    rt[attribute.name] = attribute.value
            rts.append(rt)
        return rts if len(rts) > 0 else None

    def from_data(self, experiment_description, data):
        connections_data = dict()
        for guid, elem_data in data.iteritems():
            if "testbed_id" in elem_data:
                self.testbed_from_data(experiment_description, elem_data)
            else:
                self.box_from_data(experiment_description, elem_data)
                if "connections" in elem_data:
                    connections_data[guid] = elem_data["connections"]
        # Connections need all boxes to be created
        self.connections_from_data(experiment_description, connections_data)
        return experiment_description

    def testbed_from_data(self, experiment_description, data):
        testbed_id = data["testbed_id"]
        testbed_version = data["testbed_version"]
        mod_name = 'nepi.testbeds.%s' % testbed_id
        if not mod_name in sys.modules:
            __import__(mod_name)
        testbed_mod = sys.modules[mod_name]
        provider = testbed_mod.TestbedFactoriesProvider(testbed_version)
        experiment_description.add_testbed_description(provider)

    def box_from_data(self, experiment_description, data):
        testbed_guid = data["testbed_guid"]
        testbed_description = experiment_description.testbed_description(
                testbed_guid)
        factory_id = data["factory_id"]
        if "factory_attributes" in data:
            self.factory_attributes_from_data(factory_id, testbed_description, 
                    data["factory_attributes"])
        box = testbed_description.create(factory_id)
        if "attributes" in data:
            self.attributes_from_data(box, data["attributes"])
        if "traces" in data:
            self.traces_from_data(box, data["traces"])
        if "addresses" in data:
            self.addresses_from_data(box, data["addresses"])
        if "routes" in data:
            self.routes_from_data(box, experiment_description, data["routes"])

    def factory_attributes_from_data(self, factory_id, testbed_description, 
            data):
        factory = testbed_description.provider.factory(factory_id)
        for name, value in data.iteritems():
            factory.set_attribute_value(name, value)

    def attributes_from_data(self, box, data):
        for name, value in data.iteritems():
            box.set_attribute_value(name, value)

    def traces_from_data(self, box, data):
        for name in data:
            box.trace(name).enable()

    def connections_from_data(self, experiment_description, data):
        for guid, connector_data in data.iteritems():
            box = experiment_description.box(guid)
            for connector_type_name, connections in connector_data.iteritems():
                for guid, other_connector_type_name in connections.iteritems():
                    other_box = experiment_description.box(guid)
                    connector = box.connector(connector_type_name)
                    other_connector = other_box.connector(
                            other_connector_type_name)
                    if not connector.is_connected(other_connector):
                        connector.connect(other_connector)

    def addresses_from_data(self, box, data):
        for address_attrs in data:
            addr = box.add_address()
            for name, value in address_attrs.iteritems():
                addr.set_attribute_value(name, value)

    def routes_from_data(self, box, experiment_description, data):
        for route_attrs in data:
            route = box.add_route()
            for name, value in route_attrs.iteritems():
                route.set_attribute_value(name, value)

