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
# Author: Lucia Guevgeozian <lucia.guevgeozian_odizzio@inria.fr>

from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceAction, ResourceState

import os

def create_node(ec, username, pl_user, pl_password, hostname=None, country=None,
                operatingSystem=None, minBandwidth=None, minCpu=None):

    node = ec.register_resource("PlanetlabNode")

    if username:
        ec.set(node, "username", username)
    if pl_user:
        ec.set(node, "pluser", pl_user)
    if pl_password:
        ec.set(node, "plpassword", pl_password)

    if hostname:
        ec.set(node, "hostname", hostname)
    if country:
        ec.set(node, "country", country)
    if operatingSystem:
        ec.set(node, "operatingSystem", operatingSystem)
    if minBandwidth:
        ec.set(node, "minBandwidth", minBandwidth)
    if minCpu:
        ec.set(node, "minCpu", minCpu)

    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    
    return node

def add_app(ec, command, node, sudo=None, video=None, depends=None, forward_x11=None, \
        env=None):
    app = ec.register_resource("LinuxApplication")
    if sudo is not None:
        ec.set(app, "sudo", sudo)
    if video is not None:
        ec.set(app, "sources", video)
    if depends is not None:
        ec.set(app, "depends", depends)
    if forward_x11 is not None:
        ec.set(app, "forwardX11", forward_x11)
    if env is not None:
        ec.set(app, "env", env)
    ec.set(app, "command", command)

    ec.register_connection(app, node)

    return app

exp_id = "ping_filters_exp"

# Create the entity Experiment Controller:
ec = ExperimentController(exp_id)

# Register the nodes resources:

# The username in this case is the slice name, the one to use for login in 
# via ssh into PlanetLab nodes. Replace with your own slice name.
username = "inria_sfatest"

# The pluser and plpassword are the ones used to login in the PlanetLab web 
# site. Replace with your own user and password account information.
pl_user = "lucia.guevgeozian_odizzio@inria.fr"
pl_password =  os.environ.get("PL_PASS")

# Choose the PlanetLab nodes for the experiment, in this example 5 nodes are
# used, and they are picked according to different criterias.

# First node will be the one defined by its hostname.
hostname = "planetlab2.utt.fr"
node1 = create_node(ec, username, pl_user, pl_password, hostname=hostname)

# Second node will be any node in France.
country = "France"
node2 = create_node(ec, username, pl_user, pl_password, country=country)

# Third node will be a node in France that has Fedora 14 installed.
operatingSystem = "f14"
node3 = create_node(ec, username, pl_user, pl_password, country=country,
                operatingSystem=operatingSystem)

# Forth node will have at least 50% of CPU available
minCpu=50
node4 = create_node(ec, username, pl_user, pl_password, minCpu=minCpu)

# Fifth node can be any node, constrains are not important.
node5 = create_node(ec, username, pl_user, pl_password)

# Register the applications to run in the nodes, in this case just ping to the 
# first node:
apps_per_node = dict()
apps = []
for node in [node2, node3, node4, node5]:
    command = "ping -c5 %s > ping%s.txt" % (hostname, node)
    app = add_app(ec, command, node)
    apps_per_node[node] = app
    apps.append(app)

# Register conditions

# The nodes that are completely identified by their hostnames have to be provisioned 
# before the rest of the nodes. This assures that no other resource will use the
# identified node even if the constraints matchs. 
# In this example node2, node3, node4 and node5, are deployed after node1 is 
# provisioned. node1 must be the node planetlab2.utt.fr, meanwhile node2, node3,
# node4 and node5 just need to fulfill certain constraints.
# Applications are always deployed after nodes, so no need to register conditions
# for the apps in this example.

ec.register_condition(node2, ResourceAction.DEPLOY, node1, ResourceState.PROVISIONED)
ec.register_condition(node3, ResourceAction.DEPLOY, node1, ResourceState.PROVISIONED)
ec.register_condition(node4, ResourceAction.DEPLOY, node1, ResourceState.PROVISIONED)
ec.register_condition(node5, ResourceAction.DEPLOY, node1, ResourceState.PROVISIONED)
    
# Deploy the experiment:
ec.deploy()

# Wait until the applications are finish to retrive the traces:
ec.wait_finished(apps)

traces = dict() 
for node, app in apps_per_node.iteritems():
    ping_string = "ping%s.txt" % node
    trace = ec.trace(app, ping_string)
    traces[node]= trace

# Choose a directory to store the traces locally, change to a convenient path for you:
directory = "examples/planetlab/"
for node, trace in traces.iteritems():
    trace_file = directory + "ping%s.txt" % node
    f = open(trace_file, "w")
    f.write(trace)
    f.close()

# Do the experiment controller shutdown:
ec.shutdown()

# END
