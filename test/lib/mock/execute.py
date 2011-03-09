#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl

class TestbedInstance(testbed_impl.TestbedInstance):
    def __init__(self, testbed_version):
        super(TestbedInstance, self).__init__(TESTBED_ID, testbed_version)

    def do_setup(self):
        pass

    def do_configure(self):
        pass

    def set(self, time, guid, name, value):
        super(TestbedInstance, self).set(time, guid, name, value)

    def get(self, time, guid, name):
        return True 

    def action(self, time, guid, action):
        raise NotImplementedError

    def trace(self, guid, trace_id):
        return """PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
"""

    def shutdown(self):
	    pass

