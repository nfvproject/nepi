#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
import os

class TestbedInstance(testbed_impl.TestbedInstance):
    def __init__(self, testbed_version):
        super(TestbedInstance, self).__init__(TESTBED_ID, testbed_version)
        self._home_directory = None
        self._traces = dict()

    @property
    def home_directory(self):
        return self._home_directory

    def do_setup(self):
        self._home_directory = self._attributes.\
            get_attribute_value("homeDirectory")

    def set(self, time, guid, name, value):
        super(TestbedInstance, self).set(time, guid, name, value)
        # TODO: take on account schedule time for the task 
        element = self._elements[guid]
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
        # TODO: fetch real data from planetlab
        try:
            return self.box_get_route(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None

    def get_address(self, guid, index, attribute='Address'):
        # TODO: fetch real data from planetlab
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


