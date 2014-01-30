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

# Create the EC
exp_id = "multihop_ssh"
ec = ExperimentController(exp_id)

# server
node1 = ec.register_resource("LinuxNode")
ec.set(node1, "hostname", "wlab19.")
ec.set(node1, "username", "root")
ec.set(node1, "gatewayUser", "etourdi")
ec.set(node1, "gateway", "etourdi.pl.sophia.inria.fr")
ec.set(node1, "cleanHome", True)
ec.set(node1, "cleanProcesses", True)

# client
node2 = ec.register_resource("LinuxNode")
ec.set(node2, "hostname", "wlab5.")
ec.set(node2, "username", "root")
ec.set(node2, "gatewayUser", "etourdi")
ec.set(node2, "gateway", "etourdi.pl.sophia.inria.fr")
ec.set(node2, "cleanHome", True)
ec.set(node2, "cleanProcesses", True)

app1 = ec.register_resource("LinuxApplication")
video= "../big_buck_bunny_240p_mpeg4_lq.ts"
ec.set(app1, "sources", video)
command = "cat ${SRC}/big_buck_bunny_240p_mpeg4_lq.ts| nc wlab5 1234" 
ec.set(app1, "command", command)
ec.register_connection(app1, node1)

app2 = ec.register_resource("LinuxApplication")
command = "nc -dl 1234 > big_buck_copied_movie.ts"
ec.set(app2, "command", command)
ec.register_connection(app2, node2)

# Register conditions
ec.register_condition(app1, ResourceAction.START, app2, ResourceState.STARTED)

# Deploy
ec.deploy()

ec.wait_finished([app1, app2])

ec.shutdown()

# End
