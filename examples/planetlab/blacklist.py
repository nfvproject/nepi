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

# Create the EC
exp_id = "test_blacklist"
ec = ExperimentController(exp_id)

pl_user = os.environ.get("PL_USER")
pl_password =  os.environ.get("PL_PASS")
#username = os.environ.get("PL_SLICE")
username = 'inria_sfatest'

# nodes
node1 = ec.register_resource("PlanetlabNode")
ec.set(node1, "username", username)
ec.set(node1, "pluser", pl_user)
ec.set(node1, "plpassword", pl_password)
ec.set(node1, "cleanHome", True)
ec.set(node1, "cleanProcesses", True)

node2 = ec.register_resource("PlanetlabNode")
ec.set(node2, "username", username)
ec.set(node2, "pluser", pl_user)
ec.set(node2, "plpassword", pl_password)
ec.set(node2, "cleanHome", True)
ec.set(node2, "cleanProcesses", True)

node3 = ec.register_resource("PlanetlabNode")
ec.set(node3, "username", username)
ec.set(node3, "pluser", pl_user)
ec.set(node3, "plpassword", pl_password)
ec.set(node3, "cleanHome", True)
ec.set(node3, "cleanProcesses", True)

# Set the global attribute 'persist_blacklist' 
# (that applies to all PlanetlabNodes) to persist the 
# use of the blacklist, meaning leaving out of the
# provisioning the nodes in that file, and adding the new blacklisted
# nodes to the file.
ec.set_global('PlanetlabNode', 'persist_blacklist', True)

# apps
app1 = ec.register_resource("LinuxApplication")
command = "ping -c5 google.com" 
ec.set(app1, "command", command)
ec.register_connection(app1, node1)

app2 = ec.register_resource("LinuxApplication")
command = "ping -c5 google.com" 
ec.set(app2, "command", command)
ec.register_connection(app2, node2)

app3 = ec.register_resource("LinuxApplication")
command = "ping -c5 google.com" 
ec.set(app3, "command", command)
ec.register_connection(app3, node3)

# Deploy
ec.deploy()

ec.wait_finished([app1, app2, app3])

ec.shutdown()

# The blacklisted nodes are saved in ~/.nepi/plblacklist.txt. 
# The next time the experiment is run these nodes will not be used.

# End
