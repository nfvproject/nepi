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
# This library contains functions to parse (CCNx) ccnd logs.
#
# Results from experiments must be stored in a directory
# named with the experiment run id.
# ccnd logs are stored in .log files in a subdirectory per node.
# The following diagram exemplifies the experiment result directory
# structure (nidi is the unique identifier assigned to node i):
#
#    run_id
#               \   nid1
#                        \ nid2.log
#               \   nid2
#                        \ nid1.log
#               \   nid3
#                        \ nid3.log
#

import collections
import functools
import networkx
import os
import pickle
import tempfile

from nepi.util.timefuncs import compute_delay_ms
from nepi.util.statfuncs import compute_mean
import nepi.data.processing.ping.parser as ping_parser

def is_control(content_name):
    return content_name.startswith("ccnx:/%C1") or \
            content_name.startswith("ccnx:/ccnx") or \
            content_name.startswith("ccnx:/...")


def parse_file(filename):
    """ Parses message information from ccnd log files

        filename: path to ccndlog file

    """

    faces = dict()
    sep = " "

    f = open(filename, "r")

    data = []

    for line in f:
        cols =  line.strip().split(sep)

        # CCN_PEEK
        # MESSAGE interest_from
        # 1374181938.808523 ccnd[9245]: debug.4352 interest_from 6 ccnx:/test/bunny.ts (23 bytes,sim=0CDCC1D7)
        #
        # MESSAGE interest_to
        # 1374181938.812750 ccnd[9245]: debug.3502 interest_to 5 ccnx:/test/bunny.ts (39 bytes,i=2844,sim=0CDCC1D7)
        #
        # MESSAGE CONTENT FROM
        # 1374181938.868682 ccnd[9245]: debug.4643 content_from 5 ccnx:/test/bunny.ts/%FD%05%1E%85%8FVw/%00/%9E%3D%01%D9%3Cn%95%2BvZ%8
        #
        # MESSAGE CONTENT_TO
        # 1374181938.868772 ccnd[9245]: debug.1619 content_to 6 ccnx:/test/bunny.ts/%FD%05%1E%85%8FVw/%00/%9E%3D%01%D9%3Cn%95%2BvZ%8
        #
        # 1375596708.222304 ccnd[9758]: debug.3692 interest_expiry ccnx:/test/bunny.ts/%FD%05%1E%86%B1GS/%00%0A%F7 (44 bytes,c=0:1,i=2819,sim=49FA8048)

        # External face creation
        # 1374181452.965961 ccnd[9245]: accepted datagram client id=5 (flags=0x40012) 204.85.191.10 port 9695

        if line.find("accepted datagram client") > -1:
            face_id = (cols[5]).replace("id=",'')
            ip = cols[7] 
            port = cols[9]
            faces[face_id] = (ip, port)
            continue

        # 1374181452.985296 ccnd[9245]: releasing face id 4 (slot 4)
        if line.find("releasing face id") > -1:
            face_id = cols[5]
            if face_id in faces:
                del faces[face_id]
            continue

        if len(cols) < 6:
            continue

        timestamp = cols[0]
        message_type = cols[3]

        if message_type not in ["interest_from", "interest_to", "content_from", 
                "content_to", "interest_dupnonce", "interest_expiry"]:
            continue

        face_id = cols[4] 
        content_name = cols[5]

        # Interest Nonce ? -> 412A74-0844-0008-50AA-F6EAD4
        nonce = ""
        if message_type in ["interest_from", "interest_to", "interest_dupnonce"]:
            last = cols[-1]
            if len(last.split("-")) == 5:
                nonce = last

        try:
            size = int((cols[6]).replace('(',''))
        except:
            print "interest_expiry without face id!", line
            continue

        # If no external IP address was identified for this face
        # asume it is a local face
        hostip = "localhost"

        if face_id in faces:
            hostip, port = faces[face_id]

        data.append((content_name, timestamp, message_type, hostip, face_id, 
            size, nonce, line))

    f.close()

    return data

def dump_content_history(content_history):
    f = tempfile.NamedTemporaryFile(delete=False)
    pickle.dump(content_history, f)
    f.close()
    return f.name

def load_content_history(fname):
    f = open(fname, "r")
    content_history = pickle.load(f)
    f.close()

    os.remove(fname)
    return content_history

def annotate_cn_node(graph, nid, ips2nid, data, content_history):
    for (content_name, timestamp, message_type, hostip, face_id, 
            size, nonce, line) in data:

        # Ignore local messages for the time being. 
        # They could later be used to calculate the processing times
        # of messages.
        if peer == "localhost":
            return

        # Ignore control messages for the time being
        if is_control(content_name):
            return

        if message_type == "interest_from" and \
                peer == "localhost":
            graph.node[nid]["ccn_consumer"] = True
        elif message_type == "content_from" and \
                peer == "localhost":
            graph.node[nid]["ccn_producer"] = True

        # remove digest
        if message_type in ["content_from", "content_to"]:
            content_name = "/".join(content_name.split("/")[:-1])
           
        if content_name not in content_history:
            content_history[content_name] = list()
      
        peernid = ips2nid[peer]
        add_edge(graph, nid, peernid)

        content_history[content_name].append((timestamp, message_type, nid, 
            peernid, nonce, size, line))

def annotate_cn_graph(logs_dir, graph, parse_ping_logs = False):
    """ Adds CCN content history for each node in the topology graph.

    """
    # Make a copy of the graph to ensure integrity
    graph = graph.copy()

    ips2nids = dict()

    for nid in graph.nodes():
        ips = graph.node[nid]["ips"]
        for ip in ips:
            ips2nids[ip] = nid

    # Now walk through the ccnd logs...
    for dirpath, dnames, fnames in os.walk(logs_dir):
        # continue if we are not at the leaf level (if there are subdirectories)
        if dnames: 
            continue
        
        # Each dirpath correspond to a different node
        nid = os.path.basename(dirpath)
    
        content_history = dict()

        for fname in fnames:
            if fname.endswith(".log"):
                filename = os.path.join(dirpath, fname)
                data = parse_file(filename)
                annotate_cn_node(graph, nid, ips2nids, data, content_history)

        # Avoid storing everything in memory, instead dump to a file
        # and reference the file
        fname = dump_content_history(content_history)
        graph.node[nid]["history"] = fname

    if parse_ping_logs:
        ping_parser.annotate_cn_graph(logs_dir, graph)

    return graph

def ccn_producers(graph):
    """ Returns the nodes that are content providers """
    return [nid for nid in graph.nodes() \
            if graph.node[nid].get("ccn_producer")]

def ccn_consumers(graph):
    """ Returns the nodes that are content consumers """
    return [nid for nid in graph.nodes() \
            if graph.node[nid].get("ccn_consumer")]

def process_content_history(graph):
    """ Compute CCN message counts and aggregates content historical 
    information in the content_names dictionary 
    
    """

    ## Assume single source
    source = ccn_consumers(graph)[0]

    interest_expiry_count = 0
    interest_dupnonce_count = 0
    interest_count = 0
    content_count = 0
    content_names = dict()

    # Collect information about exchanged messages by content name and
    # link delay info.
    for nid in graph.nodes():
        # Load the data collected from the node's ccnd log
        fname = graph.node[nid]["history"]
        history = load_content_history(fname)

        for content_name in history.keys():
            hist = history[content_name]

            for (timestamp, message_type, nid1, nid2, nonce, size, line) in hist:
                if message_type in ["content_from", "content_to"]:
                    # The first Interest sent will not have a version or chunk number.
                    # The first Content sent back in reply, will end in /=00 or /%00.
                    # Make sure to map the first Content to the first Interest.
                    if content_name.endswith("/=00"):
                        content_name = "/".join(content_name.split("/")[0:-2])

                # Add content name to dictionary
                if content_name not in content_names:
                    content_names[content_name] = dict()
                    content_names[content_name]["interest"] = dict()
                    content_names[content_name]["content"] = list()

                # Classify interests by replica
                if message_type in ["interest_from"] and \
                        nonce not in content_names[content_name]["interest"]:
                    content_names[content_name]["interest"][nonce] = list()
     
                # Add consumer history
                if nid == source:
                    if message_type in ["interest_to", "content_from"]:
                        # content name history as seen by the source
                        if "consumer_history" not in content_names[content_name]:
                            content_names[content_name]["consumer_history"] = list()

                        content_names[content_name]["consumer_history"].append(
                                (timestamp, message_type)) 

                # Add messages per content name and cumulate totals by message type
                if message_type == "interest_dupnonce":
                    interest_dupnonce_count += 1
                elif message_type == "interest_expiry":
                    interest_expiry_count += 1
                elif message_type == "interest_from":
                    interest_count += 1
                    # Append to interest history of the content name
                    content_names[content_name]["interest"][nonce].append(
                            (timestamp, nid2, nid1))
                elif message_type == "content_from":
                    content_count += 1
                    # Append to content history of the content name
                    content_names[content_name]["content"].append((timestamp, nid2, nid1))
                else:
                    continue
            del hist
        del history

    # Compute the time elapsed between the time an interest is sent
    # in the consumer node and when the content is received back
    for content_name in content_names.keys():
        # order content and interest messages by timestamp
        content_names[content_name]["content"] = sorted(
              content_names[content_name]["content"])
        
        for nonce, timestamps in content_names[content_name][
                    "interest"].iteritems():
              content_names[content_name]["interest"][nonce] = sorted(
                        timestamps)
      
        history = sorted(content_names[content_name]["consumer_history"])
        content_names[content_name]["consumer_history"] = history

        # compute the rtt time of the message
        rtt = None
        waiting_content = False 
        interest_timestamp = None
        content_timestamp = None
        
        for (timestamp, message_type) in history:
            if not waiting_content and message_type == "interest_to":
                waiting_content = True
                interest_timestamp = timestamp
                continue

            if waiting_content and message_type == "content_from":
                content_timestamp = timestamp
                break
    
        # If we can't determine who sent the interest, discard it
        rtt = -1
        if interest_timestamp and content_timestamp:
            rtt = compute_delay_ms(content_timestamp, interest_timestamp)

        content_names[content_name]["rtt"] = rtt
        content_names[content_name]["lapse"] = (interest_timestamp, content_timestamp)

    return (content_names,
        interest_expiry_count,
        interest_dupnonce_count,
        interest_count,
        content_count)

def process_content_history_logs(logs_dir, graph):
    """ Parse CCN logs and aggregate content history information in graph.
    Returns annotated graph and message countn and content names history.

    """
    ## Process logs and analyse data
    try:
        graph = annotate_cn_graph(logs_dir, graph, 
                parse_ping_logs = True)
    except:
        print "Skipping: Error parsing ccnd logs", logs_dir
        raise

    source = consumers(graph)[0]
    target = producers(graph)[0]

    # Process the data from the ccnd logs, but do not re compute
    # the link delay. 
    try:
        (graph,
        content_names,
        interest_expiry_count,
        interest_dupnonce_count,
        interest_count,
        content_count) = process_content_history(graph)
    except:
        print "Skipping: Error processing ccn data", logs_dir
        raise

    return (graph,
            content_names,
            interest_expiry_count,
            interest_dupnonce_count,
            interest_count,
            content_count) 
