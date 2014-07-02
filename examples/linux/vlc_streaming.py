#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2014 INRIA
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
#
# Instructions to run this example:
#
# 1. First edit the script file where required (See ASSING messages)
#
# 2. Then, run the script:
#
# $ cd <path-to-nepi>
# $ PYTHONPATH=$PYTHONPATH:~/repos/nepi/src python examples/linux/vlc_streaming.py -u inria_nepi -i ~/.ssh/id_rsa_planetlab -a planetlab1.u-strasbg.fr -b planetlab1.utt.fr | vlc -


from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceState, ResourceAction 

from optparse import OptionParser, SUPPRESS_HELP
import os


usage = ("usage: %prog -a <hostanme1> -b <hostname2> -u <username> -i <ssh-key>")

parser = OptionParser(usage = usage)
parser.add_option("-a", "--hostname1", dest="hostname1", 
        help="Remote host 1", type="str")
parser.add_option("-b", "--hostname2", dest="hostname2", 
        help="Remote host 2", type="str")
parser.add_option("-u", "--username", dest="username", 
        help="Username to SSH to remote host", type="str")
parser.add_option("-i", "--ssh-key", dest="ssh_key", 
        help="Path to private SSH key to be used for connection", 
        type="str")
(options, args) = parser.parse_args()

hostname1 = options.hostname1
hostname2 = options.hostname2
username = options.username
ssh_key = options.ssh_key

## Create the experiment controller
ec = ExperimentController(exp_id = "demo_CCN")

## Register node 1
node1 = ec.register_resource("LinuxNode")
# Set the hostname of the first node to use for the experiment
ec.set(node1, "hostname", hostname1)
# username should be your SSH user 
ec.set(node1, "username", username)
# Absolute path to the SSH private key
ec.set(node1, "identity", ssh_key)
# Clean all files, results, etc, from previous experiments wit the same exp_id
ec.set(node1, "cleanExperiment", True)
# Kill all running processes in the node before running the experiment
ec.set(node1, "cleanProcesses", True)

## Register node 2 
node2 = ec.register_resource("LinuxNode")
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

# Register VLC server
video = "big_buck_bunny_240p_mpeg4_lq.ts"
local_path_to_video = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
            "..", video)

command = ("sudo -S dbus-uuidgen --ensure; sleep 3;"
          "vlc -I dummy -vvv ${SHARE}/%s " 
          "--sout '#rtp{dst=%s,port=5004,mux=ts}' vlc://quit") % \
                  (video, hostname2)

server = ec.register_resource("LinuxApplication")
ec.set(server, "depends", "vlc")
ec.set(server, "files", local_path_to_video)
ec.set(server, "command", command)
ec.register_connection(server, node1)

command = ("sudo -S dbus-uuidgen --ensure; sleep 3; "
        "vlc -I dummy rtp://%s:5004/%s "
        "--sout '#std{access=file,mux=ts,dst=VIDEO}'") % \
                (hostname2, video)

client = ec.register_resource("LinuxApplication")
ec.set(client, "depends", "vlc")
ec.set(client, "command", command)
ec.register_connection(client, node2)

# The stream can only be retrieved after ccnd is running
ec.register_condition(server, ResourceAction.START, 
        client, ResourceState.STARTED)

## Deploy all resources
ec.deploy()

# Wait until the ccncat is finished
ec.wait_finished([server])

print ec.trace(client, "VIDEO")

ec.shutdown()


