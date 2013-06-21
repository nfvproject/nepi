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
from nepi.execution.resource import ResourceState, ResourceAction, \
        populate_factory
from nepi.resources.linux.node import OSType

from optparse import OptionParser, SUPPRESS_HELP

import os
import time
import tempfile

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
    command = "sudo -S dbus-uuidgen --ensure ; ccncat %s | vlc - " % \
            content_name

    app = ec.register_resource("LinuxCCNApplication")
    ec.set(app, "depends", "vlc")
    ec.set(app, "forwardX11", True)
    ec.set(app, "command", command)
    ec.register_connection(app, ccnd)

    return app

if __name__ == '__main__':
    # Search for available RMs
    populate_factory()
    
    ec = ExperimentController(exp_id = "olahh")
    
    # hosts
    host1 = "planetlab2.u-strasbg.fr"
    host2 = "planet1.servers.ua.pt"
    host3 = "planetlab1.cs.uoi.gr"
    host4 = "planetlab1.aston.ac.uk"
    host5 = "itchy.comlab.bth.se"
    host6 = "roseval.pl.sophia.inria.fr"

    # users
    pluser = "inria_alina"
    user = "alina"

    content_name = "ccnx:/VIDEO"
    video = "/home/alina/repos/nepi/examples/big_buck_bunny_240p_mpeg4_lq.ts"
    """
    # describe nodes in the central ring
    ring_hosts = [host1, host2, host3, host4]
    ccnds = dict()

    for i in xrange(len(ring_hosts)):
        host = ring_hosts[i]
        node = add_node(ec, host, pluser)
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
    """  
    # border node 1
    bnode1 = add_node(ec, host5, pluser)
    ccndb1 = add_ccnd(ec, bnode1)
    ccnrb1 = add_ccnr(ec, ccndb1)
    co = add_content(ec, ccnrb1, content_name, video)

    # border node 2
    bnode2 = add_node(ec, host6, user)
    ccndb2 = add_ccnd(ec, bnode2)
    ccnrb2 = add_ccnr(ec, ccndb2)
    app = add_stream(ec, ccndb2, content_name)
 
    # connect border nodes
    #add_fib_entry(ec, ccndb1, host1)
    #add_fib_entry(ec, ccnds[host1], host5)

    #add_fib_entry(ec, ccndb2, host3)
    #add_fib_entry(ec, ccnds[host3], host6)
 
    add_fib_entry(ec, ccndb2, host5)
    add_fib_entry(ec, ccndb1, host6)
 
    # deploy all ResourceManagers
    ec.deploy()

    ec.wait_finished([app])
    
    """
    proc2 = subprocess.Popen(['vlc', 
        '--ffmpeg-threads=1',
        '--sub-filter', 'marq', 
        '--marq-marquee', 
        '(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org', 
        '--marq-position=8', 
        '--no-video-title-show', '-'], 
        stdin=proc1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    dirpath = tempfile.mkdtemp()
    """

    # shutdown the experiment controller
    ec.shutdown()

