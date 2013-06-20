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
# topology:
#
#           0
#         /   \
#  0 --- 0     0 --- 0
#         \   /
#           0
#
#

from nepi.execution.ec import ExperimentController, ECState 
from nepi.execution.resource import ResourceState, ResourceAction, \
        populate_factory
from nepi.resources.linux.node import OSType

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
    command = "sudo -S dbus-uuidgen --ensure ; ( ccncat %s | vlc - ) " % \
            content_name

    app = ec.register_resource("LinuxCCNDApplication")
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
    host1 = 'planetlab2.u-strasbg.fr'
    host2 = 'roseval.pl.sophia.inria.fr'

    # users
    user1 = "inria_alina"
    user2 = "alina"

    content_name = "ccnx:/VIDEO"
    video = "/home/alina/repos/nepi/examples/big_buck_bunny_240p_mpeg4_lq.ts"

    # Register a ResourceManagers (RMs)

    node1 = add_node(ec, host1, user1)
    ccnd1 = add_ccnd(ec, node1)
    ccnr1 = add_ccnr(ec, ccnd1)
    fibentry1 = add_fib_entry(ec, ccnd1, host2)
    co = add_content(ec, ccnr1, content_name, video)

    node2 = add_node(ec, host2, user2)
    ccnd2 = add_ccnd(ec, node2)
    ccnr2 = add_ccnr(ec, ccnd2)
    fibentry2 = add_fib_entry(ec, ccnd2, host1)
    app = add_stream(ec, ccnd2, content_name)
 
    # Deploy all ResourceManagers
    ec.deploy()

    ec.wait_finished([app])

    # Shutdown the experiment controller
    ec.shutdown()

