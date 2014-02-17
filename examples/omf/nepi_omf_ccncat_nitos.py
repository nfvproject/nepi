"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Author: Alina Quereilhac <alina.quereilhac@inria.fr>
            Julien Tribino <julien.tribino@inria.fr>

    Example :
      - Testbed : Nitos
      - Explanation :

      CCN topology:
                   
     content              ccncat
     b1                   b2
     0 ------------------ 0
   
      - Experiment:
        * t0 : b2 retrives video published in b1

"""

#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

from optparse import OptionParser, SUPPRESS_HELP

###  Define OMF Method to simplify definition of resources ###
def add_node(ec, hostname, xmppSlice, xmppHost, xmppPort = "5222", xmppPassword = "1234"):
    node = ec.register_resource("OMFNode")
    ec.set(node, 'hostname', hostname)
    ec.set(node, 'xmppSlice', xmppSlice)
    ec.set(node, 'xmppHost', xmppHost)
    ec.set(node, 'xmppPort', xmppPort)
    ec.set(node, 'xmppPassword', xmppPassword)
    return node

def add_interface(ec, ip, xmppSlice, xmppHost, essid = "ccn", alias = "w0", mode = "adhoc",
                 typ = "g", xmppPort = "5222", xmppPassword = "1234"):
    iface = ec.register_resource("OMFWifiInterface")
    ec.set(iface, 'alias', alias)
    ec.set(iface, 'mode', mode)
    ec.set(iface, 'type', typ)
    ec.set(iface, 'essid', essid)
    ec.set(iface, 'ip', ip)
    return iface

def add_channel(ec, channel, xmppSlice, xmppHost, xmppPort = "5222", xmppPassword = "1234"):
    chan = ec.register_resource("OMFChannel")
    ec.set(chan, 'channel', channel)
    ec.set(chan, 'xmppSlice', xmppSlice)
    ec.set(chan, 'xmppHost', xmppHost)
    ec.set(chan, 'xmppPort', xmppPort)
    ec.set(chan, 'xmppPassword', xmppPassword)
    return chan

def add_app(ec, appid, command, args, env, xmppSlice, xmppHost, 
                xmppPort = "5222", xmppPassword = "1234"):
    app = ec.register_resource("OMFApplication")
    ec.set(app, 'appid', appid)
    ec.set(app, 'path', command)
    ec.set(app, 'args', args)
    ec.set(app, 'env', env)
    return app


###  Define a CCND application  ###
def add_ccnd(ec, peers, xmppSlice, xmppHost, xmppPort = "5222", xmppPassword = "1234"):
    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root \
CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'

    # BASH command -> ' ccndstart ; ccndc add ccnx:/ udp host ; ccnr '
    peers = map(lambda peer: "ccndc add ccnx:/ udp  %s" % peer, peers)
    #command += " ; ".join(peers) + " && "
    command = peers[0]

    app = add_app(ec, "#ccnd", command, "", env, xmppSlice, xmppHost,
                     xmppPort = xmppPort, xmppPassword = xmppPassword)
    return app

###  Define a CCN SeqWriter application ###
def add_publish(ec, movie, xmppSlice, xmppHost, xmppPort = "5222", xmppPassword = "1234"):
    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'

    # BASH command -> 'ccnseqwriter -r ccnx:/VIDEO < movie'
    command = "ccnseqwriter -r ccnx:/VIDEO"
    command += " < " + movie

    app = add_app(ec, "#ccn_write", command, "", env, xmppSlice, xmppHost,
                  xmppPort = xmppPort, xmppPassword = xmppPassword)
    return app

###  Define a streaming application ###
def add_stream(ec, xmppSlice, xmppHost, xmppPort = "5222", xmppPassword = "1234"):
    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'
    command = " ddbus-uuidgen --ensure ; ( /root/ccnx-0.7.2/bin/ccncat ccnx:/VIDEO | /root/vlc-1.1.13/cvlc - )  "
    #command = "ccncat ccnx:/VIDEO | /root/vlc-1.1.13/cvlc - "
    app = add_app(ec, "#ccn_stream", command, "", env, xmppSlice, xmppHost,
                  xmppPort = xmppPort, xmppPassword = xmppPassword)
    return app

###  Many options to easily addapt the script ####
def get_options():
    usage = "usage: %prog -w <sender-node> -r <receiver-node> -s <slice> -m <movie>"

    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--sender-host", dest="sender_host", 
            help="Hostname of the sender Node", type="str")
    parser.add_option("-i", "--sender-ip", dest="sender_ip", 
            help="IP of the sender Node", type="str")
    parser.add_option("-r", "--receiver-host", dest="receiver_host", 
            help="Hostname of the receiver node", type="str")
    parser.add_option("-p", "--receiver-ip", dest="receiver_ip", 
            help="IP of the receiver node", type="str")
    parser.add_option("-c", "--channel", dest="channel", 
            help="Channel of the communication", type="str")
    parser.add_option("-s", "--xmpp-slice", dest="xmpp_slice", 
            help="Name of the slice XMPP", type="str")
    parser.add_option("-x", "--xmpp-host", dest="xmpp_host",
            help="Name of the host XMPP", type="str")
    parser.add_option("-m", "--movie", dest="movie", 
            help="Stream movie", type="str")

    (options, args) = parser.parse_args()

    if not options.movie:
        parser.error("movie is a required argument")

    return (options.sender_host, options.sender_ip, options.receiver_host, options.receiver_ip, options.channel, options.xmpp_slice, 
            options.xmpp_host ,options.movie)

### Script itself ###
if __name__ == '__main__':
    (sender, sender_ip, receiver, receiver_ip, channel, xmpp_slice, xmpp_host, movie) = get_options()

    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'

# Create the EC
    ec = ExperimentController()

# Create the topology
    node1 = add_node(ec,sender, xmpp_slice, xmpp_host)
    iface1 = add_interface(ec, sender_ip, xmpp_slice, xmpp_host)
    ec.register_connection(node1, iface1)

    node2 = add_node(ec, receiver, xmpp_slice, xmpp_host)
    iface2 = add_interface(ec, receiver_ip, xmpp_slice, xmpp_host)
    ec.register_connection(node2, iface2)

    chann = add_channel(ec, channel, xmpp_slice, xmpp_host)
    ec.register_connection(iface1, chann)
    ec.register_connection(iface2, chann)

# CCN setup for the sender
    ccndstart1 = add_app(ec, "#ccndstart", "ccndstart &", "", env,xmpp_slice, xmpp_host)
    ec.register_connection(ccndstart1, node1)

    peers = [receiver_ip]
    ccnd1 = add_ccnd(ec, peers, xmpp_slice, xmpp_host)
    ec.register_connection(ccnd1, node1)

    ccnr1 = add_app(ec, "#ccnr", "ccnr &", "", env, xmpp_slice, xmpp_host)
    ec.register_connection(ccnr1, node1)

    # Register content producer application (ccnseqwriter)
    pub = add_publish(ec, movie, xmpp_slice, xmpp_host)
    ec.register_connection(pub, node1)

    # The movie can only be published after ccnd is running
    ec.register_condition(ccnd1, ResourceAction.START, ccndstart1, ResourceState.STARTED, "1s")
    ec.register_condition(ccnr1, ResourceAction.START, ccnd1, ResourceState.STARTED, "1s")
    ec.register_condition(pub, ResourceAction.START, ccnr1, ResourceState.STARTED, "2s")
   
# CCN setup for the receiver
    ccndstart2 = add_app(ec, "#ccndstart", "ccndstart &", "", env,xmpp_slice, xmpp_host)
    ec.register_connection(ccndstart2, node2)

    peers = [sender_ip]
    ccnd2 = add_ccnd(ec, peers, xmpp_slice, xmpp_host)
    ec.register_connection(ccnd2, node2)

    ccnr2 = add_app(ec, "#ccnr", "ccnr &", "", env,xmpp_slice, xmpp_host)
    ec.register_connection(ccnr2, node2)
     
    # Register consumer application (ccncat)
    stream = add_stream(ec, xmpp_slice, xmpp_host)
    ec.register_connection(stream, node2)

    # The stream can only be retrieved after ccnd is running
    ec.register_condition(ccnd2, ResourceAction.START, ccndstart2, ResourceState.STARTED, "1s")
    ec.register_condition(ccnr2, ResourceAction.START, ccnd2, ResourceState.STARTED, "1s")
    ec.register_condition(stream, ResourceAction.START, ccnr2, ResourceState.STARTED, "2s")

# And also, the stream can only be retrieved after it was published
    ec.register_condition(stream, ResourceAction.START, pub, ResourceState.STARTED, "5s")


# Cleaning when the experiment stop
    ccndstop1 = add_app(ec, "#ccndstop", "ccndstop", "", env, xmpp_slice, xmpp_host)
    ec.register_connection(ccndstop1, node1)
    ccndstop2 = add_app(ec, "#ccndstop", "ccndstop", "", env, xmpp_slice, xmpp_host)
    ec.register_connection(ccndstop2, node2)
    ccndstops = [ccndstop1,ccndstop2]

    killall = add_app(ec, "#kill", "killall sh", "", "", xmpp_slice, xmpp_host)
    ec.register_connection(killall, node2)

    apps = [ccndstart1, ccnd1, ccnr1, pub, ccndstart2, ccnd2, ccnr2, stream]

    ec.register_condition(apps, ResourceAction.STOP, stream, ResourceState.STARTED, "20s")

    ec.register_condition(ccndstops, ResourceAction.START, apps, ResourceState.STOPPED, "1s")
    ec.register_condition(killall, ResourceAction.START, ccndstops, ResourceState.STARTED)
    ec.register_condition(ccndstops, ResourceAction.STOP, ccndstops, ResourceState.STARTED, "1s")
    ec.register_condition(killall, ResourceAction.STOP, ccndstops, ResourceState.STOPPED)

# Deploy all ResourceManagers
    ec.deploy()

# Wait until the applications are finished
    ec.wait_finished(ccndstops)

# Shutdown the experiment controller
    ec.shutdown()

