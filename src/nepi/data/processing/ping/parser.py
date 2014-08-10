#!/usr/bin/env python

###############################################################################
#
#    CCNX benchmark
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
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>
#
###############################################################################

#
# This library contains functions to parse log files generated using ping. 
#

import collections
import re
import os

# RE to match line starting "traceroute to"
_rre = re.compile("\d+ bytes from ((?P<hostname>[^\s]+) )?\(?(?P<ip>[^\s]+)\)??: icmp_.eq=\d+ ttl=\d+ time=(?P<time>[^\s]+) ms")

def parse_file(filename):
    """
        filename: path to traceroute file

    """

    f = open(filename, "r")

    # Traceroute info
    target_ip = None
    target_hostname = None
   
    data = []

    for line in f:
        # match traceroute to ...
        m = re.match(_rre, line)
        if not m:
            continue

        target_ip = m.groupdict()["ip"]
        # FIX THIS: Make sure the regular expression does not inlcude 
        # the ')' in the ip group 
        target_ip = target_ip.replace(")","")
        target_hostname = m.groupdict()["hostname"]
        time = m.groupdict()["time"]
        data.append((target_ip, target_hostname, time))

    f.close()

    return data

def annotate_cn_node(graph, nid1, ips2nid, data):
    for (target_ip, target_hostname, time) in data:
        nid2 = ips2nid[target_ip]

        if "delays" not in graph.edge[nid1][nid2]:
            graph.edge[nid1][nid2]["delays"] = []

        time = float(time.replace("ms", "").replace(" ",""))

        graph.edge[nid1][nid2]["delays"].append(time)

def annotate_cn_graph(logs_dir, graph): 
    """ Add delay inormation to graph using data collected using
    ping.

    """
    ips2nid = dict()

    for nid in graph.nodes():
        ips = graph.node[nid]["ips"]
        for ip in ips:
            ips2nid[ip] = nid

    # Walk through the ping logs...
    for dirpath, dnames, fnames in os.walk(logs_dir):
        # continue if we are not at the leaf level (if there are subdirectories)
        if dnames: 
            continue
        
        # Each dirpath correspond to a different host
        nid = os.path.basename(dirpath)
    
        for fname in fnames:
            if fname.endswith(".ping"):
                filename = os.path.join(dirpath, fname)
                data = parse_file(filename)
                annotate_cn_node(graph, nid, ips2nid, data)

    # Take as weight the most frequent value
    for nid1, nid2 in graph.edges():
        delays = collections.Counter(graph.edge[nid1][nid2]["delays"])
        weight = delays.most_common(1)[0][0]
        del graph.edge[nid1][nid2]["delays"]
        graph.edge[nid1][nid2]["weight"] = weight

    return graph


