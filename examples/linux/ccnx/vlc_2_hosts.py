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

def add_node(ec, host, user, ssh_key = None):
    node = ec.register_resource("LinuxNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    ec.set(node, "identity", ssh_key)
    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    return node

def add_ccnd(ec, os_type, peers):
    if os_type == "f12":
        depends = ( " autoconf openssl-devel  expat-devel libpcap-devel "
                " ecryptfs-utils-devel libxml2-devel automake gawk " 
                " gcc gcc-c++ git pcre-devel make ")
    elif os_type == "ubuntu":
        depends = ( " autoconf libssl-dev libexpat-dev libpcap-dev "
                " libecryptfs0 libxml2-utils automake gawk gcc g++ "
                " git-core pkg-config libpcre3-dev make ")

    sources = "http://www.ccnx.org/releases/ccnx-0.7.1.tar.gz"

    build = (
        # Evaluate if ccnx binaries are already installed
        " ( "
            "  test -f ${EXP_HOME}/ccnx/bin/ccnd"
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
            "  test -f ${EXP_HOME}/ccnx/bin/ccnd"
        " ) || ( "
            "  mkdir -p ${EXP_HOME}/ccnx/bin && "
            "  cp -r ${SOURCES}/ccnx ${EXP_HOME}"
        " )"
    )

    env = "PATH=$PATH:${EXP_HOME}/ccnx/bin"

    # BASH command -> ' ccndstart ; ccndc add ccnx:/ udp  host ;  ccnr '
    command = "ccndstart ; "
    peers = map(lambda peer: "ccndc add ccnx:/ udp  %s" % peer, peers)
    command += " ; ".join(peers) + " ; "
    command += " ccnr "

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
    command = "sudo -S dbus-uuidgen --ensure ; ( ccncat ccnx:/VIDEO | vlc - ) "

    app = ec.register_resource("LinuxApplication")
    ec.set(app, "depends", "vlc")
    ec.set(app, "forwardX11", True)
    ec.set(app, "env", env)
    ec.set(app, "command", command)

    return app

def get_options():
    slicename = os.environ.get("PL_SLICE")

    # We use a specific SSH private key for PL if the PL_SSHKEY is specified or the
    # id_rsa_planetlab exists 
    default_key = "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'])
    default_key = default_key if os.path.exists(default_key) else None
    pl_ssh_key = os.environ.get("PL_SSHKEY", default_key)

    usage = "usage: %prog -s <pl-slice> -u <username> -m <movie> -l <exp-id> -i <ssh_key>"

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--pl-slice", dest="pl_slice", 
            help="PlanetLab slicename", default = slicename, type="str")
    parser.add_option("-u", "--username", dest="username", 
            help="User for extra host (non PlanetLab)", type="str")
    parser.add_option("-m", "--movie", dest="movie", 
            help="Stream movie", type="str")
    parser.add_option("-l", "--exp-id", dest="exp_id", 
            help="Label to identify experiment", type="str")
    parser.add_option("-i", "--pl-ssh-key", dest="pl_ssh_key", 
            help="Path to private SSH key to be used for connection", 
            default = pl_ssh_key, type="str")

    (options, args) = parser.parse_args()

    if not options.movie:
        parser.error("movie is a required argument")

    return (options.pl_slice, options.username, options.movie, options.exp_id, 
            options.pl_ssh_key)

if __name__ == '__main__':
    ( pl_slice, username, movie, exp_id, pl_ssh_key ) = get_options()

    # Search for available RMs
    populate_factory()
    
    # PlanetLab node
    host1 = 'planetlab2.u-strasbg.fr'
    
    # Another node 
    # IMPORTANT NOTE: you must replace this host for another one
    #       you have access to. You must set up your SSH keys so
    #       the host can be accessed through SSH without prompting
    #       for a password. The host must allow X forwarding using SSH.
    host2 = 'roseval.pl.sophia.inria.fr'

    # Create the ExperimentController instance
    ec = ExperimentController(exp_id = exp_id)

    # Register a ResourceManager (RM) for the PlanetLab node
    node1 = add_node(ec, host1, pl_slice, pl_ssh_key)
    
    peers = [host2]
    ccnd1 = add_ccnd(ec, "f12", peers)

    ec.register_connection(ccnd1, node1)

    pub = add_publish(ec, movie)
    ec.register_connection(pub, node1)

    # The movie can only be published after ccnd is running
    ec.register_condition(pub, ResourceAction.START, 
            ccnd1, ResourceState.STARTED)
    
    node2 = add_node(ec, host2, username)
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
 
    # Deploy all ResourceManagers
    ec.deploy()

    # Wait until the applications are finished
    apps = [ccnd1, pub, ccnd2, stream]
    ec.wait_finished(apps)

    # Shutdown the experiment controller
    ec.shutdown()

