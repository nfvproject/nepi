#!/usr/bin/env python

##
## Experiment topology:
## 
##  ccncatchunks                                ccnsendchunks
##       |                                            |
##       .->  node1 -- .. -- nodei -- .. -- nodeN   <-.
##    
##
##  - Nodes are connected through Intenet
##  - On each node runs a CCNx daemon
##  - Static entries are added to the CCNx FIB on each node to communicate them in series.
##    (Nodes only have FIB entries to at most two nodes)
##

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util.constants import ApplicationStatus as AS
import ipaddr
import math
from optparse import OptionParser, SUPPRESS_HELP
import os
import signal
import string
import subprocess
import tempfile
import time

# Trak SIGTERM, and set global termination flag instead of dying
TERMINATE = []
def _finalize(sig,frame):
    global TERMINATE
    TERMINATE.append(None)
signal.signal(signal.SIGTERM, _finalize)
signal.signal(signal.SIGINT, _finalize)

def create_slice_desc(slicename, plc_host, pl_user, pl_pwd, pl_ssh_key, 
        port_base, root_dir, exp_desc):
    pl_provider = FactoriesProvider("planetlab")
    slice_desc = exp_desc.add_testbed_description(pl_provider)
    slice_desc.set_attribute_value("homeDirectory", root_dir)
    slice_desc.set_attribute_value("slice", slicename)
    slice_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
    slice_desc.set_attribute_value("authUser", pl_user)
    slice_desc.set_attribute_value("authPass", pl_pwd)
    slice_desc.set_attribute_value("plcHost", plc_host)
    slice_desc.set_attribute_value("tapPortBase", port_base)
    slice_desc.set_attribute_value("p2pDeployment", True)
    # Kills all running processes before starting the experiment
    slice_desc.set_attribute_value("cleanProc", True)
    # NOTICE: Setting 'cleanHome' to 'True' will erase all previous
    # folders in the sliver Home directory, including result files!
    #slice_desc.set_attribute_value("cleanHome", True)
    slice_desc.set_attribute_value("plLogLevel", "DEBUG")
    return slice_desc
 
def create_node(hostname, pl_inet, slice_desc):
    pl_node = slice_desc.create("Node")
    pl_node.set_attribute_value("hostname", hostname)
    pl_node.set_attribute_value("label", hostname)
    pl_iface = slice_desc.create("NodeInterface")
    pl_iface.set_attribute_value("label", "iface_%s" % hostname)
    pl_iface.connector("inet").connect(pl_inet.connector("devs"))
    pl_node.connector("devs").connect(pl_iface.connector("node"))
    return pl_node

def create_ccnd(pl_node, routes, slice_desc):
    pl_app = slice_desc.create("CCNxDaemon")
    
    # We can specify a default ccnx version to be either ccnx-0.5.1 or ccnx-0.6.0
    #pl_app.set_attribute_value("ccnxversion", "ccnx-0.5.1")
    
    # We can also specify a custom local source and build and install directives
    path_to_source = os.path.join(os.path.dirname(os.path.abspath(__file__)),
        "ccnx-0.6.0rc3.tar.gz")
    pl_app.set_attribute_value("sources", path_to_source)
    pl_app.set_attribute_value("build", 
            "tar xzf ${SOURCES}/ccnx-0.6.0rc3.tar.gz && "
            "cd ./ccnx-0.6.0rc3 && "
            "./configure && make ")
    pl_app.set_attribute_value("install", "cp -r ./ccnx-0.6.0rc3/bin ${SOURCES}")
    # We use a wildcard to replace the public IP address of the node during runtime
    routes = "|".join(map(lambda route: "udp {#[iface_%s].addr[0].[Address]#}" % route, routes))
    
    # Add multicast ccn routes 
    pl_app.set_attribute_value("ccnroutes", routes)
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_app.connector("node").connect(pl_node.connector("apps"))

def create_ccnsendchunks(pl_node, slice_desc):
    pl_app = slice_desc.create("Application")
    path_to_video = os.path.join(os.path.dirname(os.path.abspath(__file__)),
        "../big_buck_bunny_240p_mpeg4_lq.ts")
    pl_app.set_attribute_value("stdin", path_to_video)
    pl_app.set_attribute_value("command", "ccnsendchunks ccnx:/VIDEO")
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_app.connector("node").connect(pl_node.connector("apps"))
    return pl_app

def exec_ccncatchunks(slicename, hostname):
    print "Getting video chunks from %s ..." % hostname
    login = "%s@%s" % (slicename, hostname)
    command = 'PATH=$PATH:$(ls | egrep nepi-ccnd- | head -1)/bin; ccncatchunks2 ccnx:/VIDEO'
    proc1 = subprocess.Popen(['ssh', login, command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = False)
    proc2 = subprocess.Popen(['vlc', '-'], stdin=proc1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc2

def create_ed(hostnames, vsys_vnet, slicename, plc_host, pl_user, pl_pwd, pl_ssh_key, 
        port_base, root_dir):

    # Create the experiment description object
    exp_desc = ExperimentDescription()

    # Create the slice description object
    slice_desc = create_slice_desc(slicename, plc_host, pl_user, pl_pwd, pl_ssh_key, 
        port_base, root_dir, exp_desc)
    
    # Create the Internet box object
    pl_inet = slice_desc.create("Internet")
    
    # Create the Node boxes
    pl_nodes = dict()
    ccn_routes = dict()
    prev_hostname = None
    for hostname in hostnames:
        pl_node = create_node(hostname, pl_inet, slice_desc)
        pl_nodes[hostname] = pl_node

        ccn_routes[hostname] = list()
        if prev_hostname:
            ccn_routes[hostname].append(prev_hostname)
            ccn_routes[prev_hostname].append(hostname)
        prev_hostname = hostname
     
    for hostname in hostnames:
        pl_node = pl_nodes[hostname] 
        routes = ccn_routes[hostname]
        create_ccnd(pl_node, routes, slice_desc)

    # Create a ccnsendchunks application box in the first node
    hostname = hostnames[0]
    pl_node = pl_nodes[hostname]
    pl_app = create_ccnsendchunks(pl_node, slice_desc)

    return exp_desc, pl_nodes, hostname, pl_app

def run(hostnames, vsys_vnet, slicename, plc_host, pl_user, pl_pwd, pl_ssh_key, 
        port_base, root_dir):

    exp_desc, pl_nodes, hostname, pl_app = create_ed(hostnames, vsys_vnet, 
            slicename, plc_host, pl_user, pl_pwd, pl_ssh_key, port_base, 
            root_dir)

    xml = exp_desc.to_xml()
    controller = ExperimentController(xml, root_dir)
    controller.start()
    
    while not TERMINATE and controller.status(pl_app.guid) == AS.STATUS_NOT_STARTED:
        time.sleep(0.5)

    proc1 = None
    if not TERMINATE:
        hostname = hostnames[-1]
        proc1 = exec_ccncatchunks(slicename, hostname)

    if not TERMINATE and proc1:
        time.sleep(60)

    proc2 = None
    if not TERMINATE:
        hostname = hostnames[-2]
        proc2 = exec_ccncatchunks(slicename, hostname)

    while not TERMINATE and proc1 and proc2 and proc2.poll() is None:
        time.sleep(0.5)
   
    if proc1:
        if proc1.poll() < 1:
           err = proc1.stderr.read()
           print "Stream 1 ERROR ", err
        else:   
           out = proc1.stdout.read()
           print "Stream 1 OUTPUT ", out

    if proc2:
        if proc2.poll() < 1:
           err = proc2.stderr.read()
           print "Stream 2 ERROR ", err
        else:   
           out = proc2.stdout.read()
           print "Stream 2 OUTPUT ", out

    controller.stop()
    controller.shutdown()

if __name__ == '__main__':
    root_dir = tempfile.mkdtemp()
    slicename = os.environ.get("PL_SLICE")
    pl_host = os.environ.get("PL_HOST", "www.planet-lab.eu")
    port_base = 2000 + (os.getpid() % 1000) * 13
    pl_ssh_key = os.environ.get(
        "PL_SSH_KEY",
        "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
    pl_user = os.environ.get('PL_USER')
    pl_pwd = os.environ.get('PL_PASS')
    pl_vsys_vnet = os.environ.get('PL_VSYS_NET')
    pl_hostnames = os.environ.get('PL_HOSTNAMES')
    default_hostnames = ['openlab02.pl.sophia.inria.fr',
                 'ple4.ipv6.lip6.fr',
                 'planetlab2.di.unito.it',
                 'merkur.planetlab.haw-hamburg.de',
                 'planetlab1.cs.uit.no',
                 'planetlab3.cs.st-andrews.ac.uk',
                 #'planetlab2.cs.uoi.gr',
                 'planetlab3.xeno.cl.cam.ac.uk',
                 'planet2.inf.tu-dresden.de',
                 'planetlab2.csg.uzh.ch',
                 'planetlab2.upm.ro',
                 'planetlab-um00.di.uminho.pt',
                 'planetlabpc2.upf.edu',
                 'planet2.elte.hu',
                 'planetlab2.esprit-tn.com' ]

    usage = "usage: %prog -s <pl_slice> -H <pl_host> -k <ssh_key> -u <pl_user> -p <pl_password> -v <vsys_vnet> -N <host_names> -c <node_count>"

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--slicename", dest="slicename", 
            help="PlanetLab slicename", default=slicename, type="str")
    parser.add_option("-H", "--pl-host", dest="pl_host", 
            help="PlanetLab site (e.g. www.planet-lab.eu)", 
            default=pl_host, type="str")
    parser.add_option("-k", "--ssh-key", dest="pl_ssh_key", 
            help="Path to private ssh key used for PlanetLab authentication", 
            default=pl_ssh_key, type="str")
    parser.add_option("-u", "--pl-user", dest="pl_user", 
            help="PlanetLab account user (i.e. Registration email address)", 
            default=pl_user, type="str")
    parser.add_option("-p", "--pl-pwd", dest="pl_pwd", 
            help="PlanetLab account password", default=pl_pwd, type="str")
    parser.add_option("-v", "--vsys-vnet", dest="vsys_vnet", 
            help="Value of the vsys_vnet tag addigned to your slice. (e.g. 192.168.3.0/16)", 
            default=pl_vsys_vnet, type="str")
    parser.add_option("-N", "--host-names", dest="hostnames", 
            help="Comma separated list of PlanetLab hostnames to use", 
            default=pl_hostnames, type="str")
    parser.add_option("-c", "--node-count", dest="node_count", 
            help="Number of nodes to use", 
            default=9, type="str")
    (options, args) = parser.parse_args()

    hostnames = map(string.strip, options.hostnames.split(",")) if options.hostnames else default_hostnames
    if options.node_count > 0 and options.node_count < len(hostnames):
       hostnames = hostnames[0:options.node_count]
    vsys_vnet = options.vsys_vnet
    slicename = options.slicename
    pl_host = options.pl_host
    pl_user= options.pl_user
    pl_pwd = options.pl_pwd
    pl_ssh_key = options.pl_ssh_key

    run(hostnames, vsys_vnet, slicename, pl_host, pl_user, pl_pwd, pl_ssh_key, 
            port_base, root_dir)

