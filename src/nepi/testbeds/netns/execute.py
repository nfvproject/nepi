#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.util.constants import TIME_NOW
import os

class TestbedController(testbed_impl.TestbedController):
    from nepi.util.tunchannel_impl import TunChannel

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
        super(TestbedController, self).do_setup()

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        # TODO: take on account schedule time for the task 
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name):
            return
        element = self._elements.get(guid)
        if element:
            setattr(element, name, value)

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name):
            return value
        element = self._elements.get(guid)
        try:
            return getattr(element, name)
        except KeyError, AttributeError:
            return value

    def action(self, time, guid, action):
        raise NotImplementedError

    def shutdown(self):
        for trace in self._traces.values():
            trace.close()
        for guid, element in self._elements.iteritems():
            if isinstance(element, self.TunChannel):
                element.Cleanup()
            else:
                factory_id = self._create[guid]
                if factory_id == "Node":
                    element.destroy()
        self._elements.clear()

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

