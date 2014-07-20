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
        clsinit_copy, ResourceAction, reschedule_delay, ResourceFactory

import os
import datetime
import random
import psutil
import time

from optparse import OptionParser

usage = ("usage: %prog -n <node_count> -a <app_count> -t <thread_count> "
        "-r <run>")

parser = OptionParser(usage = usage)
parser.add_option("-n", "--node-count", dest="node_count", 
        help="Number of simulated nodes in the experiment", type="int")
parser.add_option("-a", "--app-count", dest="app_count", 
        help="Number of simulated applications in the experiment", type="int")
parser.add_option("-t", "--thread-count", dest="thread_count", 
        help="Number of threads processing experiment events", type="int")
parser.add_option("-r", "--run", dest="run", 
        help="Run numbber", type="int")

(options, args) = parser.parse_args()

node_count = options.node_count
app_count = options.app_count
thread_count = options.thread_count
run = options.run
clean_run = (run == 1)

cpu_count = psutil.NUM_CPUS
cpu_usage = []

vmem = psutil.virtual_memory()
mem_total = vmem.total
mem_usage = []

# Measure the CPU consumption before deployment
cpu_usage_before = sum(psutil.cpu_percent(interval=1, percpu=True))

# Measure the Memory usage before
vmem = psutil.virtual_memory()
mem_usage_before = vmem.percent


########## Declaration of dummy resources #####################################

platform = "dummy"
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

###############################################################################

# Set the number of threads. 
# NOTE: This must be done before instantiating the EC.
os.environ["NEPI_NTHREADS"] = str(thread_count)

# Create Experiment Controller:
exp_id = "%s_bench" % platform
ec = ExperimentController(exp_id)
        
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

# Deploy the experiment
zero_time = datetime.datetime.now()
ec.deploy()

cpu_usage1 = sum(psutil.cpu_percent(interval=1, percpu=True))
cpu_usage1 = cpu_usage1 - cpu_usage_before
cpu_usage.append(cpu_usage1)

vmem = psutil.virtual_memory()
mem_usage1 = vmem.percent - mem_usage_before
mem_usage.append(mem_usage1)

# Wait until nodes and apps are deployed
ec.wait_deployed(nodes + apps + ifaces)
# Time to deploy
ttd_time = datetime.datetime.now()

cpu_usage2 = sum(psutil.cpu_percent(interval=1, percpu=True))
cpu_usage2 = cpu_usage2 - cpu_usage_before
cpu_usage.append(cpu_usage2)

vmem = psutil.virtual_memory()
mem_usage2 = vmem.percent - mem_usage_before
mem_usage.append(mem_usage2)

# Wait until the apps are finished
ec.wait_finished(apps)
# Time to finish
ttr_time = datetime.datetime.now()

# Do the experiment controller shutdown
ec.shutdown()
# Time to release
ttrel_time = datetime.datetime.now()

# Get the failure level of the experiment (OK if no failure)
status = ec.failure_level
if status == 1:
    status = "OK"
elif status == 2:
    status = "RM_FAILURE"
else:
    status = "EC_FAILURE"
        
# Get time deltas in miliseconds
s2us = 1000000.0 # conversion factor s to microseconds = 10^6
s2ms = 1000.0 # conversion factor s to microseconds = 10^3

ttd = ttd_time - zero_time
ttdms =  (ttd.microseconds + ((ttd.seconds + ttd.days * 24 * 3600) * s2us)) / s2ms

ttr = (ttr_time - ttd_time)
ttrms =  (ttr.microseconds + ((ttr.seconds + ttr.days * 24 * 3600) * s2us)) / s2ms

ttrel = (ttrel_time - ttr_time)
ttrelms =  (ttrel.microseconds + ((ttrel.seconds + ttrel.days * 24 * 3600) * s2us)) / s2ms

############### Persist results

filename = "%s_scalability" % platform
if not os.path.exists(filename):
    f = open(filename, "w")
    f.write("platform|time|cpu%|cpu_count|mem%|mem_total|run|node_count|app_count|thread_count|TTD(ms)|TTR(ms)|TTREL(ms)|status\n")
else:
    f = open(filename, "a")

timestmp = zero_time.strftime('%Y%m%d %H:%M:%S')
cpu_usage = sum(cpu_usage)/float(len(cpu_usage))
mem_usage = sum(mem_usage)/float(len(mem_usage))

f.write("%s|%s|%f|%d|%f|%d|%d|%d|%d|%d|%d|%d|%d|%s\n" % (
    timestmp,
    platform,
    cpu_usage,
    cpu_count,
    mem_usage,
    mem_total,
    run,
    node_count,
    app_count,
    thread_count,
    ttdms,
    ttrms,
    ttrelms,
    status
    ))

f.close()
