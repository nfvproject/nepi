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
import time

def create_node(ec, username, pl_user, pl_password, critical=True, hostname=None, 
                country=None, operatingSystem=None, minBandwidth=None, minCpu=None):

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
    ec.set(node, "critical", critical)

    #ec.set(node, "cleanHome", True)
    #ec.set(node, "cleanProcesses", True)
    
    return node

exp_id = "scalability_exp"

# Create the entity Experiment Controller:
ec = ExperimentController(exp_id)

# Register the nodes resources:

# The username in this case is the slice name, the one to use for login in 
# via ssh into PlanetLab nodes. Replace with your own slice name.
username = os.environ.get("PL_SLICE")

# The pluser and plpassword are the ones used to login in the PlanetLab web 
# site. Replace with your own user and password account information.
pl_user = os.environ.get("PL_USER")
pl_password =  os.environ.get("PL_PASS")

# Choose the PlanetLab nodes for the experiment, in this example 5 nodes are
# used, and they are picked according to different criterias.

first_set_nodes = []
second_set_nodes = []
third_set_nodes = []

# First set of nodes will be defined by its hostname.
hostnames = ['planetlab2.utt.fr',
'planetlab-2.man.poznan.pl',
'planetlab-1.ing.unimo.it',
'gschembra3.diit.unict.it',
'planetlab2.ionio.gr',
'planetlab-1.imag.fr',
'node2pl.planet-lab.telecom-lille1.eu',
'planetlab1.xeno.cl.cam.ac.uk',
'planetlab3.hiit.fi',
'planetlab2.fri.uni-lj.si',
'planetlab1.informatik.uni-erlangen.de',
'node1pl.planet-lab.telecom-lille1.eu',
'planet2.servers.ua.pt',
'iraplab1.iralab.uni-karlsruhe.de',
'planetlab-node3.it-sudparis.eu',
'planet1.elte.hu',
'planet1.l3s.uni-hannover.de',
'planetlab1.fct.ualg.pt',
'host1.planetlab.informatik.tu-darmstadt.de',
'vicky.planetlab.ntua.gr',
'planetlab1.rutgers.edu']

for hostname in hostnames:
    node = create_node(ec, username, pl_user, pl_password, hostname=hostname,
            critical=False)
    first_set_nodes.append(node)

# Second set of nodes will be U.S.A. nodes.
country = "United States"
for i in range(15):
    node = create_node(ec, username, pl_user, pl_password, country=country,
            critical=False)
    second_set_nodes.append(node)

# Third set of nodes can be any node in Planetlab testbed.
for i in range(70):
    node = create_node(ec, username, pl_user, pl_password, critical=False)
    third_set_nodes.append(node)

# Register conditions

# The nodes that are completely identified by their hostnames have to be provisioned 
# before the rest of the nodes. This assures that no other resource will use the
# identified node even if the constraints matchs. 
# In this example the nodes from the first need to be provisioned before the ones in
# the second and third group. Using the same logic, is convenient that nodes from the
# second group are provisioned before nodes from the third group.

ec.register_condition(second_set_nodes, ResourceAction.DEPLOY, first_set_nodes, ResourceState.PROVISIONED)
ec.register_condition(third_set_nodes, ResourceAction.DEPLOY, second_set_nodes, ResourceState.PROVISIONED)
 
# Deploy the experiment:
ec.deploy()

# Wait until all nodes are provisioned:
ec.wait_deployed(first_set_nodes)
ec.wait_deployed(second_set_nodes)
ec.wait_deployed(third_set_nodes)

# Do the experiment controller shutdown:
ec.shutdown()

# END
