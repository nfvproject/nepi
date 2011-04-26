#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
import os

class TestbedController(testbed_impl.TestbedController):
    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)
        self._netns = None
        self._home_directory = None
        self._traces = dict()

    @property
    def home_directory(self):
        return self._home_directory

    @property
    def netns(self):
        return self._netns

    def do_setup(self):
        self._home_directory = self._attributes.\
            get_attribute_value("homeDirectory")
        self._netns = self._load_netns_module()

    def set(self, time, guid, name, value):
        super(TestbedController, self).set(time, guid, name, value)
        
        # TODO: take on account schedule time for the task 
        element = self._elements.get(guid)
        if element:
            setattr(element, name, value)

    def get(self, time, guid, name):
        # TODO: take on account schedule time for the task
        element = self._elements.get(guid)
        if element:
            try:
                if hasattr(element, name):
                    # Runtime attribute
                    return getattr(element, name)
                else:
                    # Try design-time attributes
                    return self.box_get(time, guid, name)
            except KeyError, AttributeError:
                return None

    def get_route(self, guid, index, attribute):
        # TODO: fetch real data from netns
        try:
            return self.box_get_route(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None

    def get_address(self, guid, index, attribute='Address'):
        # TODO: fetch real data from netns
        try:
            return self.box_get_address(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None


    def action(self, time, guid, action):
        raise NotImplementedError

    def shutdown(self):
        for trace in self._traces.values():
            trace.close()
        for element in self._elements.values():
            element.destroy()

    def trace_filename(self, guid, trace_id):
        # TODO: Need to be defined inside a home!!!! with and experiment id_code
        return os.path.join(self.home_directory, "%d_%s" % (guid, trace_id))

    def follow_trace(self, trace_id, trace):
        self._traces[trace_id] = trace

    def _load_netns_module(self):
        # TODO: Do something with the configuration!!!
        import sys
        __import__("netns")
        netns_mod = sys.modules["netns"]
        # enable debug
        enable_debug = self._attributes.get_attribute_value("enableDebug")
        if enable_debug:
            netns_mod.environ.set_log_level(netns_mod.environ.LOG_DEBUG)
        return netns_mod
