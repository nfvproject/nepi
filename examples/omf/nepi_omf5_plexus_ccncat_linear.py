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
    
                 
                   
     content                ccncat        ccncat
     h1      h2      h3      h4            h5
     0 ----- 0 ----- 0 ------ 0 ------------0
               

      - Experiment:
        * t0 : h4 retrieves the content and we measure the time
        * t1 : h5 retrieve the content and should go faster than h4

"""

#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

from optparse import OptionParser, SUPPRESS_HELP

###  Define OMF Method to simplify definition of resources ###
def add_node(ec, hostname, xmppServer, xmppUser, xmppPort = "5222", xmppPassword = "1234"):
    node = ec.register_resource("OMFNode")
    ec.set(node, 'hostname', hostname)
    ec.set(node, 'xmppServer', xmppServer)
    ec.set(node, 'xmppUser', xmppUser)
    ec.set(node, 'xmppPort', xmppPort)
    ec.set(node, 'xmppPassword', xmppPassword)
    ec.set(node, 'version', "5")
    return node

def add_interface(ec, ip, xmppServer, xmppUser, essid = "ccn", name = "wlan0", mode = "adhoc",
                 typ = "g", xmppPort = "5222", xmppPassword = "1234"):
    iface = ec.register_resource("OMFWifiInterface")
    ec.set(iface, 'name', name)
    ec.set(iface, 'mode', mode)
    ec.set(iface, 'hw_mode', typ)
    ec.set(iface, 'essid', essid)
    ec.set(iface, 'ip', ip)
    ec.set(iface, 'version', "5")
    return iface

def add_channel(ec, channel, xmppServer, xmppUser, xmppPort = "5222", xmppPassword = "1234"):
    chan = ec.register_resource("OMFChannel")
    ec.set(chan, 'channel', channel)
    ec.set(chan, 'xmppServer', xmppServer)
    ec.set(chan, 'xmppUser', xmppUser)
    ec.set(chan, 'xmppPort', xmppPort)
    ec.set(chan, 'xmppPassword', xmppPassword)
    ec.set(chan, 'version', "5")
    return chan

def add_app(ec, host,  appid, command, env, xmppServer, xmppUser, 
                xmppPort = "5222", xmppPassword = "1234"):
    app = ec.register_resource("OMFApplication")
    ec.set(app, 'appid', appid)
    ec.set(app, 'command', command)
    ec.set(app, 'env', env)
    ec.set(app, 'version', "5")
    ec.register_connection(app, host)
    return app


###  Define a CCND application  ###
def add_ccnd(ec, host, peers, xmppServer, xmppUser, xmppPort = "5222", xmppPassword = "1234"):
    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root \
CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'

    # BASH command -> ' ccndstart ; ccndc add ccnx:/ udp host ; ccnr '
    command = "ccndc add ccnx:/ udp " + peers
    app = add_app(ec, host, "#ccnd", command, env, xmppServer, xmppUser,
                    xmppPort = xmppPort, xmppPassword = xmppPassword)
    return app

###  Define a CCN SeqWriter application ###
def add_publish(ec, host,  movie, xmppServer, xmppUser, xmppPort = "5222", xmppPassword = "1234"):
    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'

    # BASH command -> 'ccnseqwriter -r ccnx:/VIDEO < movie'
    command = "ccnseqwriter -r ccnx:/VIDEO"
    command += " < " + movie

    app = add_app(ec, host, "#ccn_write", command, env, xmppServer, xmppUser,
                  xmppPort = xmppPort, xmppPassword = xmppPassword)
    return app

###  Define a streaming application ###
def add_stream(ec, host, xmppServer, xmppUser, xmppPort = "5222", xmppPassword = "1234"):
    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'
    command = " ddbus-uuidgen --ensure ; ( /root/ccnx-0.7.2/bin/ccncat ccnx:/VIDEO | /root/vlc-1.1.13/cvlc - )  "
    app = add_app(ec, host, "#ccn_stream", command, env, xmppServer, xmppUser,
                  xmppPort = xmppPort, xmppPassword = xmppPassword)
    return app

###  Many options to easily addapt the script ####
def get_options():
    usage = "usage: %prog -c <channel> -s <xmpp_slice> -x <xmpp_host> -m <movie>"

    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--channel", dest="channel", 
            help="Channel of the communication", type="str")
    parser.add_option("-s", "--xmpp-slice", dest="xmpp_slice", 
            help="Name of the slice XMPP", type="str")
    parser.add_option("-x", "--xmpp-host", dest="xmpp_host",
            help="Name of the host XMPP", type="str")
    #parser.add_option("-e", "--exp-id", dest="exp_id", 
    #        help="Label to identify experiment", type="str")

    (options, args) = parser.parse_args()

    return (options.channel, options.xmpp_slice, 
            options.xmpp_host)

### Script itself ###
if __name__ == '__main__':
    (channel, xmpp_slice, xmpp_host) = get_options()

    env = 'PATH=$PATH:/root/ccnx-0.7.2/bin HOME=/root CCNR_DIRECTORY="/root" CCNR_STATUS_PORT="8080"'

# Create the EC
    ec = ExperimentController()

# Create the topology
    host1 = "omf.plexus.wlab5"
    host2 = "omf.plexus.wlab9"
    host3 = "omf.plexus.wlab10"
    host4 = "omf.plexus.wlab24"
    host5 = "omf.plexus.wlab29"  # b1

    ip1 = "10.0.0.5/24"
    ip2 = "10.0.0.9/24"
    ip3 = "10.0.0.10/24"
    ip4 = "10.0.0.24/24"
    ip5 = "10.0.0.29/24"

    all_hosts = [host1, host2, host3, host4, host5]
    all_ip = [ip1, ip2, ip3, ip4, ip5]

    ring_hosts = [host1, host2, host3, host4]
    nodes = dict()

    chann = add_channel(ec, channel, xmpp_slice, xmpp_host)
    for i in xrange(len(all_hosts)):
        node = add_node(ec,all_hosts[i], xmpp_slice, xmpp_host)
        iface = add_interface(ec, all_ip[i], xmpp_slice, xmpp_host)
        ec.register_connection(node, iface)
        ec.register_connection(iface, chann)
        nodes[all_hosts[i]] = node

#### CCN setup for the node
###    ccnds = dict()
###    ccnrs = dict()
###    for i in xrange(len(all_hosts)):
###        ccndstart = add_app(ec, nodes[all_hosts[i]],  "#ccndstart", "ccndstart &", 
###                              env, xmpp_slice, xmpp_host)
###        ccnr = add_app(ec, nodes[all_hosts[i]],  "#ccnr", "ccnr &", 
###                            env, xmpp_slice, xmpp_host)
###        ccnds[all_hosts[i]] = ccndstart
###        ccnrs[all_hosts[i]] = ccnr
###        ec.register_condition(ccnr, ResourceAction.START, ccndstart, ResourceState.STARTED, "1s")

#### CCNDC setup 
###    # l1 : h1 - h2 , h2 - h1
###    l1u = add_ccnd(ec, nodes[host1], ip2, xmpp_slice, xmpp_host)
###    l1d = add_ccnd(ec, nodes[host2], ip1, xmpp_slice, xmpp_host)

###    # l2 : h2 - h3 , h3 - h2
###    l2u = add_ccnd(ec, nodes[host2], ip3, xmpp_slice, xmpp_host)
###    l2d = add_ccnd(ec, nodes[host3], ip2, xmpp_slice, xmpp_host)

###    # l3 : h3 - h4 , h4 - h3
###    l3u = add_ccnd(ec, nodes[host3], ip4, xmpp_slice, xmpp_host)
###    l3d = add_ccnd(ec, nodes[host4], ip3, xmpp_slice, xmpp_host)

###    # l4 : h4 - h5 , h5 - h4
###    l4u = add_ccnd(ec, nodes[host4], ip5, xmpp_slice, xmpp_host)
###    l4d = add_ccnd(ec, nodes[host5], ip4, xmpp_slice, xmpp_host)

###    link = [l1u, l1d, l2u, l2d, l3u, l3d, l4u, l4d]

#### List of condition
###    for i in xrange(len(all_hosts)):
###         ec.register_condition(ccnrs[all_hosts[i]], ResourceAction.START, ccnds[all_hosts[i]], ResourceState.STARTED, "1s")
###         ec.register_condition(link, ResourceAction.START, ccnrs[all_hosts[i]], ResourceState.STARTED, "1s")


# Do the iperf
    iperfserv = dict()
    iperfclient = dict()
    for i in xrange(len(all_hosts)):
        perfserv = add_app(ec, nodes[all_hosts[i]],  "#perfserv", "iperf -s > /opt/iperfserv.txt", 
                              env, xmpp_slice, xmpp_host)
        iperfclient[all_hosts[i]] = []
        if i > 0:
            cmd = "iperf -c " + all_ip[i-1] + " > /opt/iperclient1.txt"
            perfclient1 = add_app(ec, nodes[all_hosts[i]],  "#perfclient1", cmd, 
                            env, xmpp_slice, xmpp_host)
            iperfclient[all_hosts[i]].append(perfclient1)

        if i < (len(all_hosts)-1):
            cmd = "iperf -c " + all_ip[i+1] + " > /opt/iperclient2.txt"
            perfclient2 = add_app(ec, nodes[all_hosts[i]],  "#perfclient2", cmd, 
                            env, xmpp_slice, xmpp_host)
            iperfclient[all_hosts[i]].append(perfclient2)

        iperfserv[all_hosts[i]] = perfserv

    for i in xrange(len(all_hosts)):
         #ec.register_condition(iperfserv[all_hosts[i]], ResourceAction.START, link, ResourceState.STARTED, "2s")
         for elt in iperfclient[all_hosts[i]]:
             ec.register_condition(elt, ResourceAction.START, iperfserv[all_hosts[i]], ResourceState.STARTED, "3s")


## Streaming Server
#    pub = add_publish(ec, nodes[host5], movie, xmpp_slice, xmpp_host)

## Streaming client
#    stream = add_stream(ec, nodes[host6], xmpp_slice, xmpp_host)

## Streaming conditions
#    ec.register_condition(pub, ResourceAction.START, link, ResourceState.STARTED, "2s")
#    ec.register_condition(stream, ResourceAction.START, link, ResourceState.STARTED, "2s")
#    ec.register_condition(stream, ResourceAction.START, pub, ResourceState.STARTED, "2s")



### Cleanning ###
# Cleaning when the experiment stop
##    ccndstops = []
##    for i in xrange(len(all_hosts)):
##        ccndstop = add_app(ec, nodes[all_hosts[i]], "#ccndstop", "ccndstop", env, xmpp_slice, xmpp_host)
##        ccndstops.append(ccndstop)
    perfkill = dict()
    for i in xrange(len(all_hosts)):
        kill = add_app(ec, nodes[all_hosts[i]], "#kill", "killall iperf", "", xmpp_slice, xmpp_host)
        perfkill[all_hosts[i]] = kill


# Condition to stop and clean the experiment
    apps = []
    for i in xrange(len(all_hosts)):
#        apps.append(ccnds[all_hosts[i]])
#        apps.append(ccnrs[all_hosts[i]])
        apps.append(iperfserv[all_hosts[i]])
        for elt in iperfclient[all_hosts[i]]:
            apps.append(elt)
#    apps += link
    #apps.append(pub)
    #apps.append(stream)

    ec.register_condition(apps, ResourceAction.STOP, apps, ResourceState.STARTED, "20s")

#    ec.register_condition(ccndstops + [killall], ResourceAction.START, apps, ResourceState.STOPPED, "1s")
#    ec.register_condition(ccndstops + [killall], ResourceAction.STOP, ccndstops, ResourceState.STARTED, "1s")

    killall = []
    for i in xrange(len(all_hosts)):
        killall.append(perfkill[all_hosts[i]])

    ec.register_condition(killall, ResourceAction.START, apps, ResourceState.STOPPED, "1s")
    ec.register_condition(killall, ResourceAction.STOP, killall, ResourceState.STARTED, "1s")

### Deploy and Wait ###
# Deploy all ResourceManagers
    ec.deploy()

# Wait until the applications are finished
    ec.wait_finished(killall)

# Shutdown the experiment controller
    ec.shutdown()


