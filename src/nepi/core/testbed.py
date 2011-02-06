#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et:ai:sts=4
from nepi.core.attributes import AttributesMap

#TODO: DEF ERRORCODES
#TODO: DEF PROTOCOL

class Configuration(AttributesMap):
    pass

class Testbed(object):
    def __init__(self, configuration):
        pass

    def execute(self, instruction):
        #TODO:
        pass

    def execute_batch(self, batch):
        raise NotImplementedError

    def create(self, time, guid, factory_id, parameters):
        raise NotImplementedError

    def destroy(self, time, guid):
        raise NotImplementedError

    def connect(self, time, connection_guid, 
            object1_guid, object2_guid, connetor1_id, connector2_id): 
        raise NotImplementedError

    def disconnect(self, time, connection_guid): 
        raise NotImplementedError

    def set(self, time, guid, name, value):
        raise NotImplementedError

    def get(self, time, guid, name):
        raise NotImplementedError

    def start(self, time, guid):
        raise NotImplementedError

    def stop(self, time, guid):
        raise NotImplementedError

    def state(self, time, guid):
        raise NotImplementedError

    def trace_enable(self, time, guid, trace_id):
        raise NotImplementedError

    def trace_disable(self, time, guid, trace_id):
        raise NotImplementedError

    def get_trace(self, time, guid, trace_id):
        raise NotImplementedError

    def add_adddress(self, time, guid):
        #TODO
        raise NotImplementedError

    def add_route(self, time, guid):
        #TODO
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError
