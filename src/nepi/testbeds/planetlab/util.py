#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import testbed_impl
from nepi.core.metadata import Parallel
from nepi.util.constants import TIME_NOW
from nepi.util.graphtools import mst
from nepi.util import ipaddr2
from nepi.util import environ
from nepi.util.parallel import ParallelRun
import sys
import os
import os.path
import time
import resourcealloc
import collections
import operator
import functools
import socket
import struct
import tempfile
import subprocess
import random
import shutil
import logging
import metadata
import weakref

def getAPI(user, pass_):
    import plcapi
    return plcapi.PLCAPI(username=user, password=pass_)

def filterBlacklist(candidates):
    blpath = environ.homepath('plblacklist')
    
    try:
        bl = open(blpath, "r")
    except:
        return candidates
        
    try:
        blacklist = set(
            map(int,
                map(str.strip, bl.readlines())
            )
        )
        return [ x for x in candidates if x not in blacklist ]
    finally:
        bl.close()

def getNodes(api, num, **constraints):
    # Now do the backtracking search for a suitable solution
    # First with existing slice nodes
    reqs = []
    nodes = []
    
    import node as Node
        
    for i in xrange(num):
        node = Node.Node(api)
        node.min_num_external_interface = 1
        nodes.append(node)
    
    node = nodes[0]
    candidates = filterBlacklist(node.find_candidates())
    reqs = [candidates] * num

    def pickbest(fullset, nreq, node=nodes[0]):
        if len(fullset) > nreq:
            fullset = zip(node.rate_nodes(fullset),fullset)
            fullset.sort(reverse=True)
            del fullset[nreq:]
            return set(map(operator.itemgetter(1),fullset))
        else:
            return fullset
    
    solution = resourcealloc.alloc(reqs, sample=pickbest)
    
    # Do assign nodes
    runner = ParallelRun(maxthreads=4)
    for node, node_id in zip(nodes, solution):
        runner.put(node.assign_node_id, node_id)
    runner.join()
    
    return nodes

def getSpanningTree(nodes, root = None, maxbranching = 2, hostgetter = operator.attrgetter('hostname')):
    if not root:
        # Pick root (deterministically)
        root = min(nodes, key=hostgetter)
    
    # Obtain all IPs in numeric format
    # (which means faster distance computations)
    for node in nodes:
        node._ip = socket.gethostbyname(hostgetter(node))
        node._ip_n = struct.unpack('!L', socket.inet_aton(node._ip))[0]
    
    # Compute plan
    # NOTE: the plan is an iterator
    plan = mst.mst(
        nodes,
        lambda a,b : ipaddr2.ipdistn(a._ip_n, b._ip_n),
        root = root,
        maxbranching = maxbranching)

    return plan

