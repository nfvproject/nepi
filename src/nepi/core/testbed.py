#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nepi.core.attributes import AttributesMap

class TestbedConfiguration(AttributesMap):
    pass

class TestbedInstance(object):
    def __init__(self, configuration):
        pass

    def create(self, guid, factory_id, parameters):
        raise NotImplementedError

    def do_create(self):
        raise NotImplementedError

    def connect(self, object1_guid, object2_guid, connect_code): 
        raise NotImplementedError

    def do_connect(self):
        raise NotImplementedError

    def enable_trace(self, guid, trace_id):
        raise NotImplementedError

    def add_adddress(self, guid):
        #TODO
        raise NotImplementedError

    def add_route(self, guid):
        #TODO
        raise NotImplementedError

    def do_configure(self):
        raise NotImplementedError

    def cross_connect(self, guid, connect_code, paremeters):
        raise NotImplementedError

    def do_cross_connect(self):
        raise NotImplementedError

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError

    def start(self, time):
        raise NotImplementedError

    def stop(self, time):
        raise NotImplementedError

    def status(self, guid):
        raise NotImplementedError

    def get_trace(self, time, guid, trace_id):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

