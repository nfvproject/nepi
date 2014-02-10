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

def add_node(ec, host, user):
    node = ec.register_resource("LinuxNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
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

exp_id = "transfer_file"

# Create the EC
ec = ExperimentController(exp_id)

# PlanetLab choosen nodes for the experiment, change for PlanetLab nodes in your slice or
# other linux nodes
server_name = "planetlab2.ionio.gr"
client_name = "planetlab2.fri.uni-lj.si"

slicename = "inria_sfatest"

# Location of the video in local machine
video= "../big_buck_bunny_240p_mpeg4_lq.ts"

# Packets needed for running the experiment
depends_server = "pv nc tcpdump"
depends_client = "nc"

# Add resource managers for the linux nodes
server = add_node(ec, server_name, slicename)
client = add_node(ec, client_name, slicename)

# Add resource managers for the linux applications
app_server =  add_app(ec, "cat ${SRC}/big_buck_bunny_240p_mpeg4_lq.ts | pv -fbt 2> \
     bw.txt | nc %s 1234" % client_name, server, video=video, depends=depends_server)

# Note: is important to add the -d option in nc command to not attempt to read from the 
# stdin
# if not nc in the client side close the socket suddently if runned in background
app_client =  add_app(ec, "nc -dl 1234 > big_buck_copied_movie.ts", client, \
    depends=depends_client)

capture = add_app(ec, "tcpdump -ni eth0 -w video_transfer.pcap -s0 port 1234 2>&1", \
    server, sudo=True)

# Register conditions 1. nodes ; 2. start tcpdump capture ; 3. client listen port 1234 ;
# 4. server start sending video
ec.register_condition(app_server, ResourceAction.START, app_client, ResourceState.STARTED) 
ec.register_condition(app_client, ResourceAction.START, capture, ResourceState.STARTED)

# Deploy
ec.deploy()

# Wait until the applications are finish to retrive the traces
ec.wait_finished([app_server, app_client])

bw = ec.trace(app_server, "bw.txt")
pcap = ec.trace(capture, "video_transfer.pcap")

# Choose a directory to store the traces, example f = open("/home/<user>/bw.txt", "w")
f = open("examples/linux/transfer/bw.txt", "w")
f.write(bw)
f.close()
f = open("examples/linux/transfer/video_transfer.pcap", "w")
f.write(pcap)
f.close()

ec.shutdown()

