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
from nepi.execution.runner import ExperimentRunner
from nepi.util.netgraph import NetGraph, TopologyType
import nepi.data.processing.ccn.parser as ccn_parser

import networkx
import socket
import os

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
        os.path.dirname(os.path.realpath(__file__)), "repoFile1.0.8.2")

def add_collector(ec, trace_name, subdir, newname = None):
    collector = ec.register_resource("Collector")
    ec.set(collector, "traceName", trace_name)
    ec.set(collector, "subDir", subdir)
    if newname:
        ec.set(collector, "rename", newname)

    return collector

def add_pl_host(ec, nid):
    hostname = PL_NODES[nid]

    # Add a planetlab host to the experiment description
    host = ec.register_resource("PlanetlabNode")
    ec.set(host, "hostname", hostname)
    ec.set(host, "username", pl_slice)
    ec.set(host, "identity", pl_ssh_key)
    #ec.set(host, "pluser", pl_user)
    #ec.set(host, "plpassword", pl_password)
    #ec.set(host, "country", country)
    #ec.set(host, "operatingSystem", operating_system)
    ec.set(host, "cleanExperiment", True)
    ec.set(host, "cleanProcesses", True)

    # Annotate the graph
    ec.netgraph.annotate_node(nid, "hostname", hostname)
    ec.netgraph.annotate_node(nid, "host", host)
    
    # Annotate the graph node with an ip address
    ip = socket.gethostbyname(hostname)
    ec.netgraph.annotate_node_ip(nid, ip)

def add_pl_ccnd(ec, nid):
    # Retrieve annotation from netgraph
    host = ec.netgraph.node_annotation(nid, "host")
    
    # Add a CCN daemon to the planetlab node
    ccnd = ec.register_resource("LinuxCCND")
    ec.set(ccnd, "debug", 7)
    ec.register_connection(ccnd, host)
    
    # Collector to retrieve ccnd log
    collector = add_collector(ec, "stderr", nid, "log")
    ec.register_connection(collector, ccnd)

    # Annotate the graph
    ec.netgraph.annotate_node(nid, "ccnd", ccnd)

def add_pl_ccnr(ec, nid):
    # Retrieve annotation from netgraph
    ccnd = ec.netgraph.node_annotation(nid, "ccnd")
    
    # Add a CCN content repository to the planetlab node
    ccnr = ec.register_resource("LinuxCCNR")

    ec.set(ccnr, "repoFile1", repofile)
    ec.register_connection(ccnr, ccnd)

def add_pl_ccncat(ec, nid):
    # Retrieve annotation from netgraph
    ccnd = ec.netgraph.node_annotation(nid, "ccnd")
    
    # Add a CCN cat application to the planetlab node
    ccncat = ec.register_resource("LinuxCCNCat")
    ec.set(ccncat, "pipeline", pipeline)
    ec.set(ccncat, "contentName", content_name)
    ec.register_connection(ccncat, ccnd)

def add_pl_fib_entry(ec, nid1, nid2):
    # Retrieve annotations from netgraph
    ccnd1 = ec.netgraph.node_annotation(nid1, "ccnd")
    hostname2 = ec.netgraph.node_annotation(nid2, "hostname")
    
    # Add a FIB entry between one planetlab node and its peer
    entry = ec.register_resource("LinuxFIBEntry")
    ec.set(entry, "host", hostname2)
    ec.register_connection(entry, ccnd1)

    # Collector to retrieve peering ping output (to measure neighbors delay)
    ec.enable_trace(entry, "ping")
    collector = add_collector(ec, "ping", nid1)
    ec.register_connection(collector, entry)

    return entry

def avg_interests(ec, run):
    ## Process logs
    logs_dir = ec.run_dir

    (graph,
        content_names,
        interest_expiry_count,
        interest_dupnonce_count,
        interest_count,
        content_count) = ccn_parser.process_content_history_logs(
                logs_dir, 
                ec.netgraph.topology)

    shortest_path = networkx.shortest_path(graph, 
            source = ec.netgraph.sources()[0], 
            target = ec.netgraph.targets()[0])

    ### Compute metric: Avg number of Interests seen per content name
    ###                 normalized by the number of nodes in the shortest path
    content_name_count = len(content_names.values())
    nodes_in_shortest_path = len(shortest_path) - 1
    metric = interest_count / (float(content_name_count) * float(nodes_in_shortest_path))

    # TODO: DUMP RESULTS TO FILE
    # TODO: DUMP GRAPH DELAYS!
    f = open("/tmp/metric", "w+")
    f.write("%.2f\n" % metric)
    f.close()
    print " METRIC", metric

    return metric

def add_pl_edge(ec, nid1, nid2):
    #### Add connections between CCN nodes
    add_pl_fib_entry(ec, nid1, nid2)
    add_pl_fib_entry(ec, nid2, nid1)

def add_pl_node(ec, nid):
    ### Add CCN nodes (ec.netgraph holds the topology graph)
    add_pl_host(ec, nid)
    add_pl_ccnd(ec, nid)
        
    if nid == ec.netgraph.targets()[0]:
        add_pl_ccnr(ec, nid)

    if nid == ec.netgraph.sources()[0]:
        add_pl_ccncat(ec, nid)

if __name__ == '__main__':

    #### Create NEPI Experiment Description with LINEAR topology 
    ec = ExperimentController("pl_ccn", 
            topo_type = TopologyType.LINEAR, 
            node_count = 4, 
            #assign_ips = True,
            assign_st = True,
            add_node_callback = add_pl_node, 
            add_edge_callback = add_pl_edge)
    
    print "Results stored at", ec.exp_dir

    #### Retrieve the content producing resource to wait for ot to finish
    ccncat = ec.filter_resources("LinuxCCNCat")
   
    #### Run experiment until metric convergences
    rnr = ExperimentRunner()
    runs = rnr.run(ec, min_runs = 10, max_runs = 300, 
            compute_metric_callback = avg_interests,
            wait_guids = ccncat,
            wait_time = 0)

