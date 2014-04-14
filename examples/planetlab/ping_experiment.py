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

exp_id = "ping_exp"

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

# Define a Planetlab Node with no restriction, it can be any node
node = ec.register_resource('PlanetlabNode')
ec.set(node, "username", username)
ec.set(node, "pluser", pl_user)
ec.set(node, "plpassword", pl_password)
ec.set(node, "cleanHome", True)
ec.set(node, "cleanProcesses", True)

# Define a ping application
app = ec.register_resource('LinuxApplication')
ec.set(app, 'command', 'ping -c5 google.com > ping_google.txt')

# Connect the application to the node
ec.register_connection(node, app)
    
# Deploy the experiment:
ec.deploy()

# Wait until the application is finish to retrive the trace:
ec.wait_finished(app)

trace = ec.trace(app, 'ping_google.txt')

# Choose a directory to store the traces locally, change to a convenient path for you:
directory = "examples/planetlab/"
trace_file = directory + "ping_google.txt"
f = open(trace_file, "w")
f.write(trace)
f.close()

# Do the experiment controller shutdown:
ec.shutdown()

# END
