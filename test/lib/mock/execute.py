# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import testbed_impl

class TestbedController(testbed_impl.TestbedController):
    def __init__(self):
        super(TestbedController, self).__init__(TESTBED_ID, TESTBED_VERSION)

    def do_configure(self):
        pass

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

