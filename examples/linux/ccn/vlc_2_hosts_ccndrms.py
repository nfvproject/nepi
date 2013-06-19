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
    ec.register_connection(ccnd, node)
    return ccnd

def add_ccnr(ec, ccnd, node):
    ccnr = ec.register_resource("LinuxCCNR")
    ec.register_connection(ccnr, node)
    ec.register_connection(ccnr, ccnd)

    return ccnr

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

    # Register a ResourceManagers (RMs)

    node1 = add_node(ec, host1, user1)
    ccnd1 = add_ccnd(ec, node1)
    ccnr1 = add_ccnr(ec, ccnd1, node1)

    node2 = add_node(ec, host2, user2)
    ccnd2 = add_ccnd(ec, node2)
    ccnr2 = add_ccnr(ec, ccnd2, node2)
 
    # Deploy all ResourceManagers
    ec.deploy()

    ec.wait_started([ccnd1, ccnr1, ccnd2, ccnr2])

    # Shutdown the experiment controller
    ec.shutdown()

