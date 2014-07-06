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
exp_id = "sfa_test"
ec = ExperimentController(exp_id)

#username = os.environ.get('SFA_SLICE')
username = 'inria_lguevgeo'
sfauser = os.environ.get('SFA_USER')
sfaPrivateKey = os.environ.get('SFA_PK')

# server
node1 = ec.register_resource("PlanetlabSfaNode")
ec.set(node1, "hostname", 'planetlab3.xeno.cl.cam.ac.uk')
ec.set(node1, "username", username)
ec.set(node1, "sfauser", sfauser)
ec.set(node1, "sfaPrivateKey", sfaPrivateKey)
ec.set(node1, "cleanHome", True)
ec.set(node1, "cleanProcesses", True)

node2 = ec.register_resource("PlanetlabSfaNode")
ec.set(node2, "username", username)
ec.set(node2, "sfauser", sfauser)
ec.set(node2, "sfaPrivateKey", sfaPrivateKey)
ec.set(node2, "cleanHome", True)
ec.set(node2, "cleanProcesses", True)

node3 = ec.register_resource("PlanetlabSfaNode")
ec.set(node3, "username", username)
ec.set(node3, "sfauser", sfauser)
ec.set(node3, "sfaPrivateKey", sfaPrivateKey)

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

ec.register_condition(node2, ResourceAction.DEPLOY, node1, ResourceState.PROVISIONED)
ec.register_condition(node3, ResourceAction.DEPLOY, node1, ResourceState.PROVISIONED)

# Deploy
ec.deploy()

ec.wait_finished([app1, app2, app3])

ec.shutdown()

# End
