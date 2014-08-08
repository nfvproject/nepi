#!/usr/bin/env python

###############################################################################
#
#    NEPI, a framework to manage network experiments
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
###############################################################################

from nepi.execution.ec import ExperimentController 
from nepi.execution.resource import ResourceState, ResourceAction
from nepi.util.netgraph import NetGraph, TopologyType

import os
import tempfile

from dminer import ccn

PL_NODES = dict({
    "0": "iraplab1.iralab.uni-karlsruhe.de",
    "1": "planetlab1.informatik.uni-goettingen.de",
    "2": "dfn-ple1.x-win.dfn.de",
    "3": "mars.planetlab.haw-hamburg.de",
    "4": "planetlab2.unineuchatel.ch", 
    "5": "planetlab-node3.it-sudparis.eu",
    "6": "planetlab2.extern.kuleuven.be",
    "7": "node2pl.planet-lab.telecom-lille1.eu",
    "8": "planetvs2.informatik.uni-stuttgart.de",
    "9": "planetlab1.informatik.uni-wuerzburg.de",
    "10": "planet1.l3s.uni-hannover.de",
    "11": "planetlab1.wiwi.hu-berlin.de",
    "12": "pl2.uni-rostock.de", 
    "13": "planetlab1.u-strasbg.fr",
    "14": "peeramidion.irisa.fr"
    })

pl_slice = os.environ.get("PL_SLICE")
pl_user = os.environ.get("PL_USER")
pl_password = os.environ.get("PL_PASS")
pl_ssh_key = os.environ.get("PL_SSHKEY")

content_name = "ccnx:/test/bunny.ts"

pipeline = 4 # Default value for ccncat

operating_system = "f14"

country = "germany"

repofile = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
            "..", "repoFile1.0.8.2")

def add_collector(ec, trace_name, store_dir, sub_dir, rename = None):
    collector = ec.register_resource("Collector")
    ec.set(collector, "traceName", trace_name)
    ec.set(collector, "storeDir", store_dir)
    ec.set(collector, "subDir", sub_dir)
    if rename:
        ec.set(collector, "rename", rename)

    return collector

def add_node(ec, n):
    hostname = PL_NODES[n]

    node = ec.register_resource("PlanetlabNode")
    ec.set(node, "hostname", hostname)
    ec.set(node, "username", username)
    ec.set(node, "identity", identity)
    ec.set(node, "pluser", pl_user)
    ec.set(node, "plpassword", pl_password)
    #ec.set(node, "country", country)
    #ec.set(node, "operatingSystem", operating_system)
    ec.set(node, "cleanExperiment", True)
    ec.set(node, "cleanProcesses", True)

    return node

def add_ccnd(ec, node, n):
    global PL_NODES

    ccnd = ec.register_resource("LinuxCCND")
    ec.set(ccnd, "debug", 7)
    ec.register_connection(ccnd, node)

    # collector for ccnd trace
    hostname = PL_NODES[n]
    collector = add_collector(ec, "stderr", hostname, "log")
    ec.register_connection(collector, ccnd)

    PL_NODES[n] = (hostname, node, ccnd)
    return ccnd

def add_ccnr(ec, ccnd):
    ccnr = ec.register_resource("LinuxCCNR")

    ec.set(ccnr, "repoFile1", repofile)
    ec.register_connection(ccnr, ccnd)

    return ccnr

def add_fib_entry(ec, n1, n2):
    (hostname1, node1, ccnd1) = PL_NODES[n1] 
    (hostname2, node2, ccnd2) = PL_NODES[n2]

    entry = ec.register_resource("LinuxFIBEntry")
    ec.set(entry, "host", peer_host)

    ec.register_connection(entry, ccnd1)

    ec.enable_trace(entry, "ping")
    collector = add_collector(ec, "ping", hostname2)
    ec.register_connection(collector, entry)

    return entry

def add_ccncat(ec, ccnd):
    ccncat = ec.register_resource("LinuxCCNCat")
    ec.set(ccncat, "pipeline", pipeline)
    ec.set(ccncat, "contentName", content_name)
    ec.register_connection(ccncat, ccnd)

    return ccncat

def compute_metric_callback(ec, run):
    ## Process logs and analyse data
    try:
        graph = ccn.parse_ccndlogs(graph = graph, 
                parse_ping_logs = True)
    except:
        print "Skipping: Error parsing ccnd logs", run_dir
        raise

    source = ccn.consumers(graph)[0]
    target = ccn.producers(graph)[0]

    # Process the data from the ccnd logs, but do not re compute
    # the link delay. 
    try:
        (content_names,
            interest_expiry_count,
            interest_dupnonce_count,
            interest_count,
            content_count) = ccn.process_ccn_data(graph, source)
    except:
        print "Skipping: Error processing ccn data", run_dir
        raise

    # Compute the shortest path
    shortest_path = ccn.shortest_path(graph, source, target)

    # Compute the load coefficient
    lcoeff = ccn.load_coefficient(graph, shortest_path, content_names)

    return lcoeff
             
if __name__ == '__main__':
    
    #### Generate a LADDER network topology 
    net_graph = NetGraph(topo_type = TopologyType.LADDER, 
            node_count = 6, 
            assign_st = True, 
            assign_ips = True)
   
    target = net_graph.targets()[0]
    source = net_graph.sources()[0]
    
    wait_guids = []

    #### Create NEPI Experiment Description (EC)
    ec = ExperimentController(exp_id)

    ### Add CCN nodes to the (EC)
    for n in graph.nodes():
        node = add_node(ec, n)
        ccnd = add_ccnd(ec, node, n)
        
        if n == target:
            ccnr = add_ccnr(ec, ccnd)

        ## Add content retrival application
        if n == source:
            ccncat = add_ccncat(ec, ccnd)
            wait_guids.append(ccncat)

    #### Add connections between CCN nodes
    for n1, n2 in graph.edges():
        add_fib_entry(ec, n1, n2)
        add_fib_entry(ec, n2, n1)

    #### Define the callback to compute experiment metric
    metric_callback = functools.partial(compute_metric_callback, ping)

    #### Run experiment until metric convergence
    rnr = ExperimentRunner()

    runs = rnr.run(ec, min_runs = 10, max_runs = 300 
            compute_metric_callback = metric_callback,
            wait_guids = wait_guids,
            wait_time = 0)

