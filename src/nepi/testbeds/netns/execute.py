#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.util.constants import AF_INET, AF_INET6
import os

class TestbedInstance(testbed_impl.TestbedInstance):
    def __init__(self, testbed_version):
        super(TestbedInstance, self).__init__(TESTBED_ID, testbed_version)
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

    def do_configure(self):
        # TODO: add traces!
        # configure addressess
        for guid, addresses in self._add_address.iteritems():
            element = self._elements[guid]
            for address in addresses:
                (family, address, netprefix, broadcast) = address
                if family == AF_INET:
                    element.add_v4_address(address, netprefix)
        # configure routes
        for guid, routes in self._add_route.iteritems():
            element = self._elements[guid]
            for route in routes:
                (destination, netprefix, nexthop) = route
                element.add_route(prefix = destination, prefix_len = netprefix,
                        nexthop = nexthop)

    def set(self, time, guid, name, value):
        super(TestbedInstance, self).set(time, guid, name, value)
        # TODO: take on account schedule time for the task 
        element = self._elements[guid]
        if element:
            setattr(element, name, value)

    def get(self, time, guid, name):
        # TODO: take on account schedule time for the task
        element = self._elements[guid]
        return getattr(element, name)

    def action(self, time, guid, action):
        raise NotImplementedError

    def trace(self, guid, trace_id):
        fd = open("%s" % self.trace_filename(guid, trace_id), "r")
        content = fd.read()
        fd.close()
        return content

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

