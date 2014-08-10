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

content_name = "ccnx:/test/bunny.ts"

STOP_TIME = "5000s"

operating_system = "f14"

repofile = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "repoFile1.0.8.2")

def get_simulator(ec):
    simulator = ec.filter_resources("LinuxNS3Simulation")

    if not simulator:
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", "localhost")

        simu = ec.register_resource("LinuxNS3Simulation")
        ec.register_connection(simu, node)
        return simu

    return simulator[0]

def add_collector(ec, trace_name, subdir, newname = None):
    collector = ec.register_resource("Collector")
    ec.set(collector, "traceName", trace_name)
    ec.set(collector, "subDir", subdir)
    if newname:
        ec.set(collector, "rename", newname)

    return collector

def add_dce_host(ec, nid):
    simu = get_simulator(ec)
    
    host = ec.register_resource("ns3::Node")
    ec.set(host, "enableStack", True)
    ec.register_connection(host, simu)

    # Annotate the graph
    ec.netgraph.annotate_node(nid, "host", host)
    
def add_dce_ccnd(ec, nid):
    # Retrieve annotation from netgraph
    host = ec.netgraph.node_annotation(nid, "host")
    
    # Add dce ccnd to the dce node
    ccnd = ec.register_resource("ns3::LinuxDceCCND")
    ec.set (ccnd, "stackSize", 1<<20)
    ec.set (ccnd, "debug", 7)
    ec.set (ccnd, "capacity", 50000)
    ec.set (ccnd, "StartTime", "1s")
    ec.set (ccnd, "StopTime", STOP_TIME)
    ec.register_connection(ccnd, host)

    # Collector to retrieve ccnd log
    collector = add_collector(ec, "stderr", nid, "log")
    ec.register_connection(collector, ccnd)

    # Annotate the graph
    ec.netgraph.annotate_node(nid, "ccnd", ccnd)

def add_dce_ccnr(ec, nid):
    # Retrieve annotation from netgraph
    host = ec.netgraph.node_annotation(nid, "host")
    
    # Add a CCN content repository to the dce node
    ccnr = ec.register_resource("ns3::LinuxDceCCNR")
    ec.set (ccnr, "repoFile1", repofile) 
    ec.set (ccnr, "stackSize", 1<<20)
    ec.set (ccnr, "StartTime", "2s")
    ec.set (ccnr, "StopTime", STOP_TIME)
    ec.register_connection(ccnr, host)

def add_dce_ccncat(ec, nid):
    # Retrieve annotation from netgraph
    host = ec.netgraph.node_annotation(nid, "host")
   
    ccnpeek = ec.register_resource("ns3::LinuxDceCCNPeek")
    #ec.set (ccnpeek, "contentName", "ccnx:/chunk0")
    ec.set (ccnpeek, "contentName", content_name)
    ec.set (ccnpeek, "stackSize", 1<<20)
    ec.set (ccnpeek, "StartTime", "5s")
    ec.set (ccnpeek, "StopTime", STOP_TIME)
    ec.register_connection(ccnpeek, host)

    collector = add_collector(ec, "stdout", nid, "peek")
    ec.register_connection(collector, ccnpeek)

    # Add a ccncat application to the dce host
    ccncat = ec.register_resource("ns3::LinuxDceCCNCat")
    ec.set (ccncat, "contentName", content_name)
    ec.set (ccncat, "stackSize", 1<<20)
    ec.set (ccncat, "StartTime", "8s")
    ec.set (ccncat, "StopTime", STOP_TIME)
    ec.register_connection(ccncat, host)

def add_dce_fib_entry(ec, nid1, nid2):
    # Retrieve annotations from netgraph
    host1 = ec.netgraph.node_annotation(nid1, "host")
    net = ec.netgraph.edge_net_annotation(nid1, nid2)
    ip2 = net[nid2]

    # Add FIB entry between peer hosts
    ccndc = ec.register_resource("ns3::LinuxDceFIBEntry")
    ec.set (ccndc, "protocol", "udp") 
    ec.set (ccndc, "uri", "ccnx:/") 
    ec.set (ccndc, "host", ip2)
    ec.set (ccndc, "stackSize", 1<<20)
    ec.set (ccndc, "StartTime", "2s")
    ec.set (ccndc, "StopTime", STOP_TIME)
    ec.register_connection(ccndc, host1)

def add_dce_net_iface(ec, nid1, nid2):
    # Retrieve annotations from netgraph
    host = ec.netgraph.node_annotation(nid1, "host")
    net = ec.netgraph.edge_net_annotation(nid1, nid2)
    ip1 = net[nid1]
    prefix = net["prefix"]

    dev = ec.register_resource("ns3::PointToPointNetDevice")
    ec.set(dev, "ip", ip1)
    ec.set(dev, "prefix", prefix)
    ec.register_connection(host, dev)

    queue = ec.register_resource("ns3::DropTailQueue")
    ec.register_connection(dev, queue)

    return dev

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

def add_dce_edge(ec, nid1, nid2):
    ### Add network interfaces to hosts
    p2p1 = add_dce_net_iface(ec, nid1, nid2)
    p2p2 = add_dce_net_iface(ec, nid2, nid1)

    # Create point to poing link between interfaces
    chan = ec.register_resource("ns3::PointToPointChannel")
    ec.set(chan, "Delay", "0ms")

    ec.register_connection(chan, p2p1)
    ec.register_connection(chan, p2p2)

    #### Add routing between CCN nodes
    add_dce_fib_entry(ec, nid1, nid2)
    add_dce_fib_entry(ec, nid2, nid1)

def add_dce_node(ec, nid):
    ### Add CCN nodes (ec.netgraph holds the topology graph)
    add_dce_host(ec, nid)
    add_dce_ccnd(ec, nid)
        
    if nid == ec.netgraph.targets()[0]:
        add_dce_ccnr(ec, nid)

    if nid == ec.netgraph.sources()[0]:
        add_dce_ccncat(ec, nid)

if __name__ == '__main__':

    #### Create NEPI Experiment Description with LINEAR topology 
    ec = ExperimentController("dce_ccn", 
            topo_type = TopologyType.LINEAR, 
            node_count = 4,
            assign_st = True,
            assign_ips = True,
            add_node_callback = add_dce_node, 
            add_edge_callback = add_dce_edge)
    
    print "Results stored at", ec.exp_dir

    #### Retrieve the consumer to wait for ot to finish
    ccncat = ec.filter_resources("ns3::LinuxDceCCNCat")
   
    #### Run experiment until metric convergences
    rnr = ExperimentRunner()
    runs = rnr.run(ec, min_runs = 1, max_runs = 1, 
            compute_metric_callback = avg_interests,
            wait_guids = ccncat,
            wait_time = 0)

