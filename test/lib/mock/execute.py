#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl

class TestbedController(testbed_impl.TestbedController):
    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)

    def do_configure(self):
        pass

    def get_route(self, guid, index, attribute):
        try:
            return self.box_get_route(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None

    def get_address(self, guid, index, attribute='Address'):
        try:
            return self.box_get_address(guid, int(index), attribute)
        except KeyError, AttributeError:
            return None

    def action(self, time, guid, action):
        raise NotImplementedError

    def trace(self, guid, trace_id, attribute='value'):
        if attribute == 'value':
            return """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""
        elif attribute == 'path':
            return '<test>'
        else:
            return None

    def shutdown(self):
	    pass

