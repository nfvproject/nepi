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
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

#
# CCN topology:
#
#                h2
#                0 
#  content   l1 / \ l2         ccncat
#  b1          /l5 \           b2
#  0 ----- h1 0 --- 0 h3 ------ 0
#              \   / 
#            l4 \ / l3
#                0
#                h4
# Experiment:
# - t0 : b2 retrives video published in b1
# - t1 : l1 goes down
# - t2 : l2 goes down
# - t3 : l5 goes up
#

from nepi.execution.ec import ExperimentController, ECState 
from nepi.execution.resource import ResourceState, ResourceAction 
from nepi.execution.trace import TraceAttr

import subprocess
from optparse import OptionParser, SUPPRESS_HELP

import os
import time

def add_node(ec, host, user, ssh_key = None):
    node = ec.register_resource("LinuxNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    ec.set(node, "identity", ssh_key)
    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    return node

def add_ccnd(ec, node):
    ccnd = ec.register_resource("LinuxCCND")
    ec.set(ccnd, "debug", 7)
    ec.register_connection(ccnd, node)
    return ccnd

def add_ccnr(ec, ccnd):
    ccnr = ec.register_resource("LinuxCCNR")
    ec.register_connection(ccnr, ccnd)
    return ccnr

def add_fib_entry(ec, ccnd, peer_host):
    entry = ec.register_resource("LinuxFIBEntry")
    ec.set(entry, "host", peer_host)
    ec.register_connection(entry, ccnd)
    return entry

def add_content(ec, ccnr, content_name, content):
    co = ec.register_resource("LinuxCCNContent")
    ec.set(co, "contentName", content_name)
    ec.set(co, "content", content)
    ec.register_connection(co, ccnr)
    return co

def add_stream(ec, ccnd, content_name):
    # ccnx v7.2 issue 101007 
    command = "ccnpeek %(content_name)s; ccncat %(content_name)s" % {
            "content_name" : content_name}

    app = ec.register_resource("LinuxCCNApplication")
    ec.set(app, "command", command)
    ec.register_connection(app, ccnd)

    return app

def add_collector(ec, trace_name):
    collector = ec.register_resource("Collector")
    ec.set(collector, "traceName", trace_name)

    return collector

def get_options():
    pl_slice = os.environ.get("PL_SLICE")

    # We use a specific SSH private key for PL if the PL_SSHKEY is specified or the
    # id_rsa_planetlab exists 
    default_key = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])
    default_key = default_key if os.path.exists(default_key) else None
    pl_ssh_key = os.environ.get("PL_SSHKEY", default_key)

    usage = "usage: %prog -s <pl-user> -m <movie> -e <exp-id> -i <ssh_key> -r <results>"

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--pl-user", dest="pl_user", 
            help="PlanetLab slicename", default = pl_slice, type="str")
    parser.add_option("-m", "--movie", dest="movie", 
            help="Stream movie", type="str")
    parser.add_option("-e", "--exp-id", dest="exp_id", 
            help="Label to identify experiment", type="str")
    parser.add_option("-i", "--pl-ssh-key", dest="pl_ssh_key", 
            help="Path to private SSH key to be used for connection", 
            default = pl_ssh_key, type="str")
    parser.add_option("-r", "--results", dest="results", default = "/tmp",  
            help="Path to directory where to store results", type="str") 

    (options, args) = parser.parse_args()

    if not options.movie:
        parser.error("movie is a required argument")

    return (options.pl_user, options.movie, options.exp_id, options.pl_ssh_key,
            options.results)

if __name__ == '__main__':
    content_name = "ccnx:/test/VIDEO"
    
    ( pl_user, movie, exp_id, pl_ssh_key, results_dir ) = get_options()

    ec = ExperimentController(exp_id = exp_id, local_dir = results_dir)

    # hosts in the US
    #host1 = "planetlab4.wail.wisc.edu"
    #host2 = "planetlab2.cs.columbia.edu"
    #host3 = "ricepl-2.cs.rice.edu"
    #host4 = "node1.planetlab.albany.edu"
    #host5 = "earth.cs.brown.edu"
    #host6 = "planetlab2.engr.uconn.edu"

    # hosts in EU
    host1 = "planetlab2.fct.ualg.pt"
    host2 = "planet2.unipr.it"
    host3 = "planetlab1.aston.ac.uk"
    host4 = "itchy.comlab.bth.se"
    host5 = "rochefort.infonet.fundp.ac.be"
    host6 = "planetlab1.u-strasbg.fr"

    # describe nodes in the central ring 
    ring_hosts = [host1, host2, host3, host4]
    ccnds = dict()

    for i in xrange(len(ring_hosts)):
        host = ring_hosts[i]
        node = add_node(ec, host, pl_user, pl_ssh_key)
        ccnd = add_ccnd(ec, node)
        ccnr = add_ccnr(ec, ccnd)
        ccnds[host] = ccnd
    
    ## Add ccn ring links
    # l1 : h1 - h2 , h2 - h1
    l1u = add_fib_entry(ec, ccnds[host1], host2)
    l1d = add_fib_entry(ec, ccnds[host2], host1)

    # l2 : h2 - h3 , h3 - h2
    l2u = add_fib_entry(ec, ccnds[host2], host3)
    l2d = add_fib_entry(ec, ccnds[host3], host2)

    # l3 : h3 - h4 , h4 - h3
    l3u = add_fib_entry(ec, ccnds[host3], host4)
    l3d = add_fib_entry(ec, ccnds[host4], host3)

    # l4 : h4 - h1 , h1 - h4
    l4u = add_fib_entry(ec, ccnds[host4], host1)
    l4d = add_fib_entry(ec, ccnds[host1], host4)

    # l5 : h1 - h3 , h3 - h1
    l5u = add_fib_entry(ec, ccnds[host1], host3)
    l5d = add_fib_entry(ec, ccnds[host3], host1)
    
    # border node 1
    bnode1 = add_node(ec, host5, pl_user, pl_ssh_key)
    ccndb1 = add_ccnd(ec, bnode1)
    ccnrb1 = add_ccnr(ec, ccndb1)
    ccnds[host5] = ccndb1
    co = add_content(ec, ccnrb1, content_name, movie)

    # border node 2
    bnode2 = add_node(ec, host6, pl_user, pl_ssh_key)
    ccndb2 = add_ccnd(ec, bnode2)
    ccnrb2 = add_ccnr(ec, ccndb2)
    ccnds[host6] = ccndb2
    app = add_stream(ec, ccndb2, content_name)
 
    # connect border nodes
    add_fib_entry(ec, ccndb1, host1)
    add_fib_entry(ec, ccnds[host1], host5)

    add_fib_entry(ec, ccndb2, host3)
    add_fib_entry(ec, ccnds[host3], host6)

    # Put down l5 10s after transfer started
    ec.register_condition(l5u, ResourceAction.STOP, 
            app, ResourceState.STARTED, time = "10s")
    ec.register_condition(l5d, ResourceAction.STOP, 
            app, ResourceState.STARTED, time = "10s")

    # Register a collector to automatically collect traces
    collector = add_collector(ec, "stderr")
    for ccnd in ccnds.values():
        ec.register_connection(collector, ccnd)

    # deploy all ResourceManagers
    ec.deploy()

    # Wait until ccncat has started retrieving the content
    ec.wait_started([app])

    rvideo_path = ec.trace(app, "stdout", attr = TraceAttr.PATH)
    command = 'tail -f %s' % rvideo_path

    # pulling the content of the video received
    # on b2, to stream it locally
    proc1 = subprocess.Popen(['ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-l', pl_user, host6,
        command],
        stdout = subprocess.PIPE, 
        stderr = subprocess.PIPE)
    
    proc2 = subprocess.Popen(['vlc', 
        '--ffmpeg-threads=1',
        '--sub-filter', 'marq', 
        '--marq-marquee', 
        '(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org', 
        '--marq-position=8', 
        '--no-video-title-show', '-'], 
        stdin=proc1.stdout, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE)

    (stdout, stderr) = proc2.communicate()

    # shutdown the experiment controller
    ec.shutdown()

