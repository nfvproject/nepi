#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Julien Tribino <julien.tribino@inria.fr>


from nepi.execution.resource import ResourceFactory, clsinit_copy, ResourceManager, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController
from nepi.execution.attribute import Attribute, Flags 

from nepi.resources.omf.node import OMFNode
from nepi.resources.omf.application import OMFApplication

from nepi.util.timefuncs import *

import time
import unittest

class DummyEC(ExperimentController):
    pass

@clsinit_copy
class DummyOMFApplication(OMFApplication):
    _rtype = "DummyOMFApplication"

    @classmethod
    def _register_attributes(cls):
        test = Attribute("test", "Input of the application", default = 0, set_hook = cls.test_hook)
        cls._register_attribute(test)

    @classmethod
    def test_hook(cls, old_value, new_value):
        new_value *= 10
        print "Change the value of test from "+ str(old_value) +" to : " + str(new_value)
        return new_value


class OMFTestSet(unittest.TestCase):

    def test_set_hook(self):
        self.ec = DummyEC(exp_id = "30")

        ResourceFactory.register_type(DummyOMFApplication)

        self.node1 = self.ec.register_resource("OMFNode")
        self.ec.set(self.node1, 'hostname', 'omf.plexus.wlab17')
        self.ec.set(self.node1, 'xmppSlice', "nepi")
        self.ec.set(self.node1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.node1, 'xmppPort', "5222")
        self.ec.set(self.node1, 'xmppPassword', "1234")

        self.app1 = self.ec.register_resource("DummyOMFApplication")
        self.ec.set(self.app1, 'appid', 'Test#1')
        self.ec.set(self.app1, 'path', "/usr/bin/ping")
        self.ec.set(self.app1, 'args', "")
        self.ec.set(self.app1, 'env', "")
        self.ec.set(self.app1, 'xmppSlice', "nepi")
        self.ec.set(self.app1, 'xmppHost', "xmpp-plexus.onelab.eu")
        self.ec.set(self.app1, 'xmppPort', "5222")
        self.ec.set(self.app1, 'xmppPassword', "1234")

        self.ec.register_connection(self.app1, self.node1)

        self.ec.register_condition(self.app1, ResourceAction.STOP, self.app1, ResourceState.STARTED , "10s")

        self.ec.deploy()

        time.sleep(3)
        print "First try to change the STDIN"
        self.ec.set(self.app1, 'test', 3)

        self.assertEquals(self.ec.get(self.app1, 'test'), 30)

        time.sleep(3)
        print "Second try to change the STDIN"
        self.ec.set(self.app1, 'test', 101)
        self.assertEquals(self.ec.get(self.app1, 'test'), 1010)

        self.ec.wait_finished([self.app1])

        # Stop Experiment
        self.ec.shutdown()


if __name__ == '__main__':
    unittest.main()



