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

from optparse import OptionParser, SUPPRESS_HELP

import os
import time

def add_node(ec, host, user):
    node = ec.register_resource("LinuxNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    #ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    return node

def add_ccnd(ec, os_type, peers):
    if os_type == "f12":
        depends = ( " autoconf openssl-devel  expat-devel libpcap-devel "
                " ecryptfs-utils-devel libxml2-devel automake gawk " 
                " gcc gcc-c++ git pcre-devel ")
    elif os_type == "ubuntu":
        depends = ( " autoconf libssl-dev libexpat-dev libpcap-dev "
                " libecryptfs0 libxml2-utils automake gawk gcc g++ "
                " git-core pkg-config libpcre3-dev ")

    sources = "http://www.ccnx.org/releases/ccnx-0.7.1.tar.gz"

    build = (
        # Evaluate if ccnx binaries are already installed
        " ( "
            "  test -d ${EXP_HOME}/ccnx/bin"
        " ) || ( "
        # If not, untar and build
            " ( "
                " mkdir -p ${SOURCES}/ccnx && "
                " tar xf ${SOURCES}/ccnx-0.7.1.tar.gz --strip-components=1 -C ${SOURCES}/ccnx "
             " ) && "
                "cd ${SOURCES}/ccnx && "
                # Just execute and silence warnings...
                "(  ( ./configure && make )  2>&1 )"
         " )") 

    install = (
        # Evaluate if ccnx binaries are already installed
        " ( "
            "  test -d ${EXP_HOME}/ccnx/bin "
        " ) || ( "
            "  mkdir -p ${EXP_HOME}/ccnx/bin && "
            "  cp -r ${SOURCES}/ccnx ${EXP_HOME}"
        " )"
    )

    env = "PATH=$PATH:${EXP_HOME}/ccnx/bin"

    # BASH command -> ' ccndstart 2>&1 ; ccndc add ccnx:/ udp  host ;  ccnr 2>&1 '
    command = "ccndstart 2>&1 ; "
    peers = map(lambda peer: "ccndc add ccnx:/ udp  %s" % peer, peers)
    command += " ; ".join(peers) + " ; "
    command += " ccnr 2>&1 "

    app = ec.register_resource("LinuxApplication")
    ec.set(app, "depends", depends)
    ec.set(app, "sources", sources)
    ec.set(app, "install", install)
    ec.set(app, "build", build)
    ec.set(app, "env", env)
    ec.set(app, "command", command)

    return app

def add_publish(ec, movie):
    env = "PATH=$PATH:${EXP_HOME}/ccnx/bin"
    command = "ccnseqwriter -r ccnx:/VIDEO"

    app = ec.register_resource("LinuxApplication")
    ec.set(app, "stdin", movie)
    ec.set(app, "env", env)
    ec.set(app, "command", command)

    return app

def add_stream(ec):
    env = "PATH=$PATH:${EXP_HOME}/ccnx/bin"
    command = "sudo -S dbus-uuidgen --ensure ; ( ccncat ccnx:/VIDEO | vlc - ) 2>&1"

    app = ec.register_resource("LinuxApplication")
    ec.set(app, "depends", "vlc")
    ec.set(app, "forwardX11", True)
    ec.set(app, "env", env)
    ec.set(app, "command", command)

    return app

def get_options():
    slicename = os.environ.get("PL_SLICE")

    usage = "usage: %prog -s <pl-slice> -u <user-2> -m <movie> -l <exp-id>"

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--pl-slice", dest="pl_slice", 
            help="PlanetLab slicename", default=slicename, type="str")
    parser.add_option("-u", "--user-2", dest="user2", 
            help="User for non PlanetLab machine", type="str")
    parser.add_option("-m", "--movie", dest="movie", 
            help="Stream movie", type="str")
    parser.add_option("-l", "--exp-id", dest="exp_id", 
            help="Label to identify experiment", type="str")

    (options, args) = parser.parse_args()

    if not options.movie:
        parser.error("movie is a required argument")

    return (options.pl_slice, options.user2, options.movie, options.exp_id)

if __name__ == '__main__':
    ( pl_slice, user2, movie, exp_id ) = get_options()

    # Search for available RMs
    populate_factory()
    
    host1 = 'planetlab2.u-strasbg.fr'
    host2 = 'roseval.pl.sophia.inria.fr'

    ec = ExperimentController(exp_id = exp_id)

    node1 = add_node(ec, host1, pl_slice)
    
    peers = [host2]
    ccnd1 = add_ccnd(ec, "f12", peers)

    ec.register_connection(ccnd1, node1)

    pub = add_publish(ec, movie)
    ec.register_connection(pub, node1)

    # The movie can only be published after ccnd is running
    ec.register_condition(pub, ResourceAction.START, 
            ccnd1, ResourceState.STARTED)
    
    node2 = add_node(ec, host2, user2)
    peers = [host1]
    ccnd2 = add_ccnd(ec, "ubuntu", peers)
    ec.register_connection(ccnd2, node2)
     
    stream = add_stream(ec)
    ec.register_connection(stream, node2)

    # The stream can only be retrieved after ccnd is running
    ec.register_condition(stream, ResourceAction.START, 
            ccnd2, ResourceState.STARTED)

    # And also, the stream can only be retrieved after it was published
    ec.register_condition(stream, ResourceAction.START, 
            pub, ResourceState.STARTED)
 
    ec.deploy()

    apps = [ccnd1, pub, ccnd2, stream]
    ec.wait_finished(apps)

    ec.shutdown()

