#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nepi.core.attributes import AttributesMap

class TestbedConfiguration(AttributesMap):
    pass

class TestbedInstance(object):
    def __init__(self, configuration):
        pass

    def create(self, guid, factory_id):
        """Instructs creation of element """
        raise NotImplementedError

    def create_set(self, guid, name, value):
        """Instructs setting an attribute on an element"""
        raise NotImplementedError

    def do_create(self):
        """After do_create all instructed elements are created and 
        attributes setted"""
        raise NotImplementedError

    def connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2): 
        raise NotImplementedError

    def do_connect(self):
        raise NotImplementedError

    def add_trace(self, guid, trace_id):
        raise NotImplementedError

    def add_adddress(self, guid, family, address, netprefix, broadcast): 
        raise NotImplementedError

    def add_route(self, guid, family, destination, netprefix, nexthop, 
            interface):
        raise NotImplementedError

    def do_configure(self):
        raise NotImplementedError

    def do_cross_connect(self):
        raise NotImplementedError

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError

    def start(self, time):
        raise NotImplementedError

    def action(self, time, guid, action):
        raise NotImplementedError

    def stop(self, time):
        raise NotImplementedError

    def status(self, guid):
        raise NotImplementedError

    def trace(self, guid, trace_id):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

