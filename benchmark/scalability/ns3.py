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

import os
import datetime
import ipaddr
import random
import psutil

from optparse import OptionParser

usage = ("usage: %prog -n <node_count> -a <app_count> -t <thread_count> "
        "-r <run> -H <remote_host> -u <remote_user> -i <ssh-key>")

parser = OptionParser(usage = usage)
parser.add_option("-n", "--node-count", dest="node_count", 
        help="Number of simulated nodes in the experiment", type="int")
parser.add_option("-a", "--app-count", dest="app_count", 
        help="Number of simulated applications in the experiment", type="int")
parser.add_option("-t", "--thread-count", dest="thread_count", 
        help="Number of threads processing experiment events", type="int")
parser.add_option("-r", "--run", dest="run", 
        help="Run numbber", type="int")

parser.add_option("-H", "--hostname", dest="hostname", 
        help="Remote host", type="str")
parser.add_option("-u", "--username", dest="username", 
        help="Username to SSH to remote host", type="str")
parser.add_option("-i", "--ssh-key", dest="ssh_key", 
        help="Path to private SSH key to be used for connection", 
        type="str")
(options, args) = parser.parse_args()

node_count = options.node_count
app_count = options.app_count
thread_count = options.thread_count
run = options.run
clean_run = (run == 1)

hostname = options.hostname
username = options.username
identity = options.ssh_key

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

platform = "ns3"

def add_linux_node(ec, hostname, username, ssh_key, clean_run):
    node = ec.register_resource("LinuxNode")
    ec.set(node, "hostname", hostname)

    if hostname not in ["localhost", "127.0.0.1"]:
        ec.set(node, "username", username)
        ec.set(node, "identity", identity)

    ec.set(node, "cleanHome", clean_run)
    ec.set(node, "cleanProcesses", True)

    return node

def add_node(ec, simu):
    node = ec.register_resource("ns3::Node")
    ec.set(node, "enableStack", True)
    ec.register_connection(node, simu)

    return node

def add_device(ec, node, ip, prefix):
    dev = ec.register_resource("ns3::CsmaNetDevice")
    ec.set(dev, "ip", ip)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(node, dev)
    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

def add_ping_app(ec, node, remote_ip):
    app = ec.register_resource("ns3::V4Ping")
    ec.set (app, "Remote", remote_ip)
    ec.set (app, "Interval", "1s")
    ec.set (app, "StartTime", "0s")
    ec.set (app, "StopTime", "20s")
    ec.register_connection(app, node)

    return app

# Set the number of threads. 
# NOTE: This must be done before instantiating the EC.
os.environ["NEPI_NTHREADS"] = str(thread_count)

# Create Experiment Controller:
exp_id = "%s_bench" % platform
ec = ExperimentController(exp_id)

# Add the physical node in which to run the simulation
lnode = add_linux_node(ec, hostname, username, identity, clean_run)

# Add a simulation resource
simu = ec.register_resource("LinuxNS3Simulation")
ec.set(simu, "enableDump", True)
ec.set(simu, "verbose", True)
ec.register_connection(simu, lnode)

# Add simulated nodes and applications
nodes = list()
apps = list()
devs = list()

ips = dict()

prefix = "16"
base_addr = "10.0.0.0/%s" % prefix
net = ipaddr.IPv4Network(base_addr)
host_itr = net.iterhosts()

for i in xrange(node_count):
    node = add_node(ec, simu)
    nodes.append(node)
    
    ip = host_itr.next()
    dev = add_device(ec, node, ip, prefix)
    devs.append(dev)

    ips[node] = ip

for nid in nodes:
    for j in xrange(app_count):
        # If there is only one node, ping itself. If there are more
        # choose one randomly.
        remote_ip = ips[nid]
        
        if len(nodes) > 1:
            choices = ips.values()
            choices.remove(remote_ip)
            remote_ip = random.choice(choices)

        app = add_ping_app(ec, node, remote_ip)
        apps.append(app)

chan = ec.register_resource("ns3::CsmaChannel")
ec.set(chan, "Delay", "0s")

for dev in devs:
    ec.register_connection(chan, dev)

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
ec.wait_deployed(nodes + apps + devs)
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

remote = "local" if hostname == "localhost" else "remote"
filename = "%s_scalability_%s.txt" % (platform, remote )
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
