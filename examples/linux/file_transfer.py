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
#         Alina Quereilhac <alina.quereilhac@inria.fr>
#
#
# Example of how to run this experiment (replace with your credentials):
#
# $ cd <path-to-nepi>
# $ PYTHONPATH=$PYTHONPATH:~/repos/nepi/src python examples/linux/file_transfer.py -u inria_nepi -i ~/.ssh/id_rsa_planetlab -a planetlab1.u-strasbg.fr -b planetlab1.utt.fr


from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceAction, ResourceState

from optparse import OptionParser, SUPPRESS_HELP
import os


# The pluser and plpassword are the ones used to login in the PlanetLab web 
# site. Replace with your own user and password account information.
pl_password =  os.environ.get("PL_PASS")
pl_user =  os.environ.get("PL_USER")
username =  os.environ.get("PL_SLICE")
ssh_key =  "/home/alina/.ssh/id_rsa_planetlab"

## Create the experiment controller
ec = ExperimentController(exp_id = "file_transfer")

## Register node 1
node1 = ec.register_resource("PlanetlabNode")
# Set the hostname of the first node to use for the experiment
ec.set(node1, "pluser", pl_user)
ec.set(node1, "plpassword", pl_password)
# username should be your SSH user 
ec.set(node1, "username", username)
# Absolute path to the SSH private key
ec.set(node1, "identity", ssh_key)
# Clean all files, results, etc, from previous experiments wit the same exp_id
ec.set(node1, "cleanExperiment", True)
# Kill all running processes in the node before running the experiment
ec.set(node1, "cleanProcesses", True)

## Register node 2 
node2 = ec.register_resource("PlanetlabNode")
# Set the hostname of the first node to use for the experiment
ec.set(node2, "pluser", pl_user)
ec.set(node2, "plpassword", pl_password)
# Set the hostname of the first node to use for the experiment
ec.set(node2, "hostname", hostname2)
# username should be your SSH user 
ec.set(node2, "username", username)
# Absolute path to the SSH private key
ec.set(node2, "identity", ssh_key)
# Clean all files, results, etc, from previous experiments wit the same exp_id
ec.set(node2, "cleanExperiment", True)
# Kill all running processes in the node before running the experiment
ec.set(node2, "cleanProcesses", True)

# Register server
video = "big_buck_bunny_240p_mpeg4_lq.ts"
local_path_to_video = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
            "..", video)

command = "cat ${SHARE}/%s | pv -fbt 2> bw.txt | nc %s 1234" % ( 
        video, hostname2 )

server = ec.register_resource("LinuxApplication")
ec.set(server, "depends", "pv nc tcpdump")
ec.set(server, "files", local_path_to_video)
ec.set(server, "command", command)
ec.register_connection(server, node1)

# Register client
command = ("sudo -S dbus-uuidgen --ensure; sleep 3; "
        "vlc -I dummy rtp://%s:5004/%s "
        "--sout '#std{access=file,mux=ts,dst=VIDEO}'") % \
                (hostname2, video)

# Note: is important to add the -d option in nc command to not attempt to read from the 
# stdin
# if not nc in the client side close the socket suddently if runned in background
command =  "nc -dl 1234 > %s" % video

client = ec.register_resource("LinuxApplication")
ec.set(client, "depends", "nc")
ec.set(client, "command", command)
ec.register_connection(client, node2)

# Register a tcpdump in the server node to monitor the file transfer 
command = "tcpdump -ni eth0 -w file_transfer.pcap -s0 port 1234 2>&1"

capture = ec.register_resource("LinuxApplication")
ec.set(capture, "depends", "tcpdump")
ec.set(capture, "command", command)
ec.set(capture, "sudo", True)
ec.register_connection(capture, node1)

# Register conditions 1. nodes ; 2. start tcpdump capture ; 3. client listen port 1234 ;
# 4. server start sending video
ec.register_condition(server, ResourceAction.START, client, ResourceState.STARTED) 
ec.register_condition(client, ResourceAction.START, capture, ResourceState.STARTED)

# Deploy
ec.deploy()

# Wait until the applications are finish to retrive the traces
ec.wait_finished([server, client])

# Retrieve traces from nc and tcpdump
bw = ec.trace(server, "bw.txt")
pcap = ec.trace(capture, "file_transfer.pcap")

# Choose a directory to store the traces, example f = open("/home/<user>/bw.txt", "w")
f = open("bw.txt", "w")
f.write(bw)
f.close()
f = open("video_transfer.pcap", "w")
f.write(pcap)
f.close()

ec.shutdown()

