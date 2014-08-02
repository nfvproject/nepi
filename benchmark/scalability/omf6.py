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

from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceManager, ResourceState, \
        clsinit_copy, ResourceAction, ResourceFactory

import os
import datetime
import random
import psutil
import subprocess
import time
import threading
import numpy

from optparse import OptionParser

usage = ("usage: %prog -n <node_count> -a <app_count> -t <thread_count> "
        "-r <run> -d <delay> -o <opdelay>")

parser = OptionParser(usage = usage)
parser.add_option("-n", "--node-count", dest="node_count", 
        help="Number of simulated nodes in the experiment", type="int")
parser.add_option("-a", "--app-count", dest="app_count", 
        help="Number of simulated applications in the experiment", type="int")
parser.add_option("-t", "--thread-count", dest="thread_count", 
        help="Number of threads processing experiment events", type="int")
parser.add_option("-r", "--run", dest="run", 
        help="Run numbber", type="int")
parser.add_option("-d", "--delay", dest="delay", 
        help="Re-scheduling delay", type="float")

(options, args) = parser.parse_args()

node_count = options.node_count
app_count = options.app_count
thread_count = options.thread_count
run = options.run
clean_run = (run == 1)
delay = options.delay
reschedule_delay = "0s" # "%0.1fs" % delay

def get_nepi_revision():
    p = subprocess.Popen(["hg", "tip"], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()

    info = stdout.split("\n")
    changeset = info[0].split(":")[-1]

    return changeset

######### Resource consumption ################################################

cpu_count = psutil.NUM_CPUS
cpu_usage_deploy = []
cpu_usage_start = []

vmem = psutil.virtual_memory()
mem_total = vmem.total
mem_usage_deploy = []
mem_usage_start = []

stop_monitor_deploy = []
stop_monitor_start = []

def compute_estimator(samples):
    if len(samples) == 0:
        return 0,0,0

    x = numpy.array(samples)
    n = len(samples)
    std = x.std() 
    m = x.mean()

    return n, m, std

def monitor_resources(cpu_usage, mem_usage, stop):
    wait = 1

    while not stop:
        p = psutil.Process(os.getpid())
        cpu = p.get_cpu_percent(interval=1)
        cpu_usage.append(cpu)

        mem = p.get_memory_percent()
        mem_usage.append(mem)

        time.sleep(wait)

thread_monitor_deploy = threading.Thread(target=monitor_resources, 
        args=(cpu_usage_deploy, mem_usage_deploy, stop_monitor_deploy))

thread_monitor_start = threading.Thread(target=monitor_resources, 
        args=(cpu_usage_start, mem_usage_start, stop_monitor_start))

########## Declaration of resources #####################################

def create_node(ec, hostname):
    node = ec.register_resource("OMFNode")
    ec.set(node, 'hostname', hostname)
    ec.set(node, 'xmppServer', "xmpp.ilabt.iminds.be")
    ec.set(node, 'xmppUser', "nepi")
    ec.set(node, 'xmppPort', "5222")
    ec.set(node, 'xmppPassword', "1234")
    return node

def create_iface(ec, name, mode, hw_mode, essid, ip, node):
    iface = ec.register_resource("OMFWifiInterface")
    ec.set(iface, 'name', name)
    ec.set(iface, 'mode', mode)
    ec.set(iface, 'hw_mode', hw_mode)
    ec.set(iface, 'essid', essid)
    ec.set(iface, 'ip', ip)
    ec.register_connection(iface, node)
    return iface

def create_chan(ec, channel):
    chan = ec.register_resource("OMFChannel")
    ec.set(chan, 'channel', "6")
    return chan

def add_app(ec, command, node):
    app = ec.register_resource("OMFApplication")
    ec.set(app, "command", command)
    ec.register_connection(app, node)
    return app

############## Experiment design and execution ################################

platform = "omf6"

# Create the list of nodes and ips
hostnames = ['servernode', 'client1node',  'client2node', 'client3node', 'client4node', 'client5node' ]

host_suffix = ".nepivlcexperiment.nepi.wilab2.ilabt.iminds.be"
#host_suffix = ".nepiperformance.nepi.wilab2.ilabt.iminds.be"

# Set the number of threads. 
# NOTE: This must be done before instantiating the EC.
os.environ["NEPI_NTHREADS"] = str(thread_count)

# Create Experiment Controller:
exp_id = "%s_bench" % platform
ec = ExperimentController(exp_id)

# App to run on each node
command = "ping -c5 192.168.0.10"

# Add simulated nodes and applications
nodes = list()
apps = list()
ifaces = list()

channel = create_chan(ec,"6")

for i in xrange(node_count):
    #node = create_node(ec,"node" + str(i) + host_suffix)
    node = create_node(ec,hostnames[i] + host_suffix)
    nodes.append(node)

    iface = create_iface(ec, 'wlan0', 'adhoc', 'g', 'ping', "192.168.0.1" + str(i)+"/24", node)
    ec.register_connection(channel, iface)
    ifaces.append(iface)

    for j in xrange(app_count):
        app = add_app(ec, command, node)
        apps.append(app)
        ec.register_condition(apps, ResourceAction.STOP, apps, ResourceState.STARTED , "10s")


# Deploy the experiment
zero_time = datetime.datetime.now()

# Launch thread to monitor CPU and memory usage
thread_monitor_deploy.start()

# Deploy experiment
ec.deploy()

# Wait until nodes and apps are deployed
ec.wait_deployed(nodes + apps + ifaces + [channel])

# Time to deploy
ttd_time = datetime.datetime.now()

# Launch thread to monitor CPU and memory usage
thread_monitor_start.start()

# Stop deploy monitoring thread
stop_monitor_deploy.append(0)

# Wait until the apps are finished
ec.wait_finished(apps)

# Time to finish
ttr_time = datetime.datetime.now()

# Stop deploy monitoring thread
stop_monitor_start.append(0)

# Do the experiment controller shutdown
ec.shutdown()

# Time to release
ttrel_time = datetime.datetime.now()

##################### Format performance information ##########################

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

revision = get_nepi_revision()

filename = "%s_scalability_benchmark_rev_%s.data" % (platform, revision)

if not os.path.exists(filename):
    f = open(filename, "w")
    f.write("time|platform|cpu_count(%)|cpu_deploy(%)|cpu_start|"
    "mem_total(B)|mem_deploy(%)|mem_starts(%)|opdelay(s)|scheddelay(s)|run#|"
    "node_count|app_count|thread_count|TTD(ms)|TTR(ms)|TTREL(ms)|status\n")
else:
    f = open(filename, "a")

timestmp = zero_time.strftime('%Y%m%d %H:%M:%S')

n,m,std = compute_estimator(cpu_usage_deploy)
cpu_deploy = "%d,%0.2f,%0.2f" % (n,m,std)

n,m,std = compute_estimator(cpu_usage_start)
cpu_start = "%d,%0.2f,%0.2f" % (n,m,std)

n,m,std = compute_estimator(mem_usage_deploy)
mem_deploy = "%d,%0.2f,%0.2f" % (n,m,std)

n,m,std = compute_estimator(mem_usage_start)
mem_start = "%d,%0.2f,%0.2f" % (n,m,std)

rm_ttd_list = list()
rm_ttr_list = list()
rm_ttrel_list = list()

for guid in ec.resources:
    rm = ec.get_resource(guid)

    rm_d = rm.ready_time - zero_time
    d = (rm_d.microseconds + ((rm_d.seconds + rm_d.days * 24 * 3600) * s2us)) / s2ms
    rm_ttd_list.append(d)

    rm_r = rm.start_time - zero_time
    r = (rm_r.microseconds + ((rm_r.seconds + rm_r.days * 24 * 3600) * s2us)) / s2ms
    rm_ttr_list.append(r)

    rm_rel = rm.release_time - zero_time
    rel = (rm_rel.microseconds + ((rm_rel.seconds + rm_rel.days * 24 * 3600) * s2us)) / s2ms
    rm_ttrel_list.append(rel)

n,m,std = compute_estimator(rm_ttd_list)
rm_ttd = "%d,%0.2f,%0.2f" % (n,m,std)

n,m,std = compute_estimator(rm_ttr_list)
rm_ttr = "%d,%0.2f,%0.2f" % (n,m,std)

n,m,std = compute_estimator(rm_ttrel_list)
rm_ttrel = "%d,%0.2f,%0.2f" % (n,m,std)

f.write("%s|%s|%d|%s|%s|%d|%s|%s|%0.1f|%d|%d|%d|%d|%d|%d|%d|%s|%s|%s|%s|\n" % (
    timestmp,
    platform,
    cpu_count,
    cpu_deploy,
    cpu_start,
    mem_total,
    mem_deploy,
    mem_start,
    delay,
    run,
    node_count,
    app_count,
    thread_count,
    ttdms,
    ttrms,
    ttrelms,
    rm_ttd,
    rm_ttr,
    rm_ttrel,
    status
    ))

f.close()

