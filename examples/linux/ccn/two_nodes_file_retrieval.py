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
# $ PYTHONPATH=$PYTHONPATHS:src python examples/linux/ccn/two_nodes_file_retrieval.py
#

from nepi.execution.ec import ExperimentController

import os

ssh_key = ####### <<< ASSING the absolute path to the private SSH key to login into the remote host >>>
ssh_user = ####### <<< ASSING the SSH username >>>

## Create the experiment controller
ec = ExperimentController(exp_id = "demo_CCN")

## Register node 1
node1 = ec.register_resource("LinuxNode")
# Set the hostname of the first node to use for the experiment
hostname1 = "peeramidion.irisa.fr" ##### <<< ASSIGN the hostname of a host you have SSSH access to >>>
ec.set(node1, "hostname", hostname1)
# username should be your SSH user 
ec.set(node1, "username", ssh_user)
# Absolute path to the SSH private key
ec.set(node1, "identity", ssh_key)
# Clean all files, results, etc, from previous experiments wit the same exp_id
ec.set(node1, "cleanExperiment", True)
# Kill all running processes in the node before running the experiment
ec.set(node1, "cleanProcesses", True)

## Register node 2 
node2 = ec.register_resource("LinuxNode")
# Set the hostname of the first node to use for the experiment
hostname2 = "planetlab2.upc.es" ##### <<< ASSIGN the hostname of a host you have SSSH access to >>>
ec.set(node2, "hostname", hostname2)
# username should be your SSH user 
ec.set(node2, "username", ssh_user)
# Absolute path to the SSH private key
ec.set(node2, "identity", ssh_key)
# Clean all files, results, etc, from previous experiments wit the same exp_id
ec.set(node2, "cleanExperiment", True)
# Kill all running processes in the node before running the experiment
ec.set(node2, "cleanProcesses", True)

## Register a CCN daemon in node 1
ccnd1 = ec.register_resource("LinuxCCND")
# Set ccnd log level to 7
ec.set(ccnd1, "debug", 7)
ec.register_connection(ccnd1, node1)

## Register a CCN daemon in node 2
ccnd2 = ec.register_resource("LinuxCCND")
# Set ccnd log level to 7
ec.set(ccnd2, "debug", 7)
ec.register_connection(ccnd2, node2)

## Register a repository in node 1
ccnr1 = ec.register_resource("LinuxCCNR")
ec.register_connection(ccnr1, ccnd1)

## Push the file into the repository
local_path_to_content = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
            "..", "..",
            "big_buck_bunny_240p_mpeg4_lq.ts")

# Register a FIB entry from node 1 to node 2
co = ec.register_resource("LinuxCCNContent")
ec.set(co, "contentName", "ccnx:/test/FILE1")
# NEPI will upload the specified file to the remote node and write it
# into the CCN repository
ec.set(co, "content", local_path_to_content)
ec.register_connection(co, ccnr1)

# Register a FIB entry from node 1 to node 2
entry1 = ec.register_resource("LinuxFIBEntry")
ec.set(entry1, "host", hostname2)
ec.register_connection(entry1, ccnd1)

# Register a FIB entry from node 2 to node 1
entry2 = ec.register_resource("LinuxFIBEntry")
ec.set(entry2, "host", hostname1)
ec.register_connection(entry2, ccnd2)

## Retrieve the file stored in node 1 from node 2
command = "ccncat ccnx:/test/FILE1"
app = ec.register_resource("LinuxCCNApplication")
ec.set(app, "command", command)
ec.register_connection(app, ccnd2)

# Register a collector to automatically collect the ccnd logs
# to a local directory
results_dir = "/tmp/demo_CCN_results"
col1 = ec.register_resource("Collector")
ec.set(col1, "traceName", "stderr")
ec.set(col1, "storeDir", results_dir)
ec.set(col1, "subDir", hostname1)
ec.register_connection(col1, ccnd1)

col2 = ec.register_resource("Collector")
ec.set(col2, "traceName", "stderr")
ec.set(col2, "storeDir", results_dir)
ec.set(col2, "subDir", hostname2)
ec.register_connection(col2, ccnd2)

## Deploy all resources
ec.deploy()

# Wait until the ccncat is finished
ec.wait_finished([app])

## CCND logs will be collected to the results_dir upon shutdown.
## We can aldo get the content of the logs now:
#print "LOG2", ec.trace(ccnd1, "stderr")
#print "LOG 1", ec.trace(ccnd2, "stderr")

ec.shutdown()
