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
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceManager, ResourceState, \
        clsinit_copy, ResourceAction, ResourceFactory

import os
import tempfile
import time
import shutil
import unittest

reschedule_delay = "0.5s"
deploy_time = 0
run_time = 0

class Link(ResourceManager):
    _rtype = "dummy::Link"
    def do_deploy(self):
        time.sleep(deploy_time)
        super(Link, self).do_deploy()
        self.logger.debug(" -------- DEPLOYED ------- ")

class Interface(ResourceManager):
    _rtype = "dummy::Interface"

    def do_deploy(self):
        node = self.get_connected(Node.get_rtype())[0]
        link = self.get_connected(Link.get_rtype())[0]

        if node.state < ResourceState.READY or \
                link.state < ResourceState.READY:
            self.ec.schedule(reschedule_delay, self.deploy)
            self.logger.debug(" -------- RESCHEDULING ------- ")
        else:
            time.sleep(deploy_time)
            super(Interface, self).do_deploy()
            self.logger.debug(" -------- DEPLOYED ------- ")

class Node(ResourceManager):
    _rtype = "dummy::Node"

    def do_deploy(self):
        self.logger.debug(" -------- DO_DEPLOY ------- ")
        time.sleep(deploy_time)
        super(Node, self).do_deploy()
        self.logger.debug(" -------- DEPLOYED ------- ")

class Application(ResourceManager):
    _rtype = "dummy::Application"

    def do_deploy(self):
        node = self.get_connected(Node.get_rtype())[0]

        if node.state < ResourceState.READY: 
            self.ec.schedule(reschedule_delay, self.deploy)
            self.logger.debug(" -------- RESCHEDULING ------- ")
        else:
            time.sleep(deploy_time)
            super(Application, self).do_deploy()
            self.logger.debug(" -------- DEPLOYED ------- ")

    def do_start(self):
        super(Application, self).do_start()
        time.sleep(run_time)
        self.ec.schedule("0s", self.stop)

ResourceFactory.register_type(Application)
ResourceFactory.register_type(Node)
ResourceFactory.register_type(Interface)
ResourceFactory.register_type(Link)

class SerializeTestCase(unittest.TestCase):
    def test_serialize(self):
        node_count = 4
        app_count = 2

        dirpath = tempfile.mkdtemp()

        ec = ExperimentController(exp_id = "serialize-test")
       
        # Add simulated nodes and applications
        nodes = list()
        apps = list()
        ifaces = list()

        for i in xrange(node_count):
            node = ec.register_resource("dummy::Node")
            nodes.append(node)
            
            iface = ec.register_resource("dummy::Interface")
            ec.register_connection(node, iface)
            ifaces.append(iface)

            for i in xrange(app_count):
                app = ec.register_resource("dummy::Application")
                ec.register_connection(node, app)
                apps.append(app)

        link = ec.register_resource("dummy::Link")

        for iface in ifaces:
            ec.register_connection(link, iface)

        filepath = ec.save(dirpath)

        ec.deploy()

        # Wait until nodes and apps are deployed
        ec.wait_finished(apps)

        # Do the experiment controller shutdown
        ec.shutdown()

        # Load serialized experiment
        ec2 = ExperimentController.load(filepath)
        apps = ec2.get_resources_by_type("dummy::Application")
        ec2.deploy()
        ec2.wait_finished(apps)
        ec2.shutdown()
        
        self.assertEquals(len(ec.resources), len(ec2.resources))

        shutil.rmtree(dirpath)
                       
if __name__ == '__main__':
    unittest.main()

