#!/usr/bin/env python

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util.constants import ApplicationStatus as AS
import ipaddr
import math
from optparse import OptionParser, SUPPRESS_HELP
import os
import random
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
    # Kills all running processes before starting the experiment
    slice_desc.set_attribute_value("cleanProc", True)
    slice_desc.set_attribute_value("plLogLevel", "DEBUG")
    return slice_desc
 
def create_node(hostname, pl_inet, slice_desc):
    pl_node = slice_desc.create("Node")
    pl_node.set_attribute_value("hostname", hostname)
    pl_node.set_attribute_value("label", hostname)
    pl_iface = slice_desc.create("NodeInterface")
    #pl_iface.set_attribute_value("label", "iface_%s" % hostname)
    pl_iface.connector("inet").connect(pl_inet.connector("devs"))
    pl_node.connector("devs").connect(pl_iface.connector("node"))
    return pl_node

def create_tunnel(node, peer, pl_nodes, slice_desc, subnet):
    pl_node = pl_nodes[node]
    pl_peer = pl_nodes[peer]

    pl_tun = slice_desc.create("TunInterface")
    pl_tun.set_attribute_value("label", "tun_%s%s" % (node, peer))
    pl_node.connector("devs").connect(pl_tun.connector("node"))

    pl_tunpeer = slice_desc.create("TunInterface")
    pl_tunpeer.set_attribute_value("label", "tun_%s%s" % (peer, node))
    pl_peer.connector("devs").connect(pl_tunpeer.connector("node"))

    pl_tun.connector("udp").connect(pl_tunpeer.connector("udp"))
    
    iterhosts = subnet.iterhosts()
    addr = iterhosts.next()
    ip = pl_tun.add_address()
    ip.set_attribute_value("Address", addr.exploded)
    ip.set_attribute_value("NetPrefix", subnet.prefixlen)

    peeraddr = iterhosts.next()
    peerip = pl_tunpeer.add_address()
    peerip.set_attribute_value("Address", peeraddr.exploded)
    peerip.set_attribute_value("NetPrefix", subnet.prefixlen)

def create_ccnd(pl_node, slice_desc):
    pl_app = slice_desc.create("CCNxDaemon")
    # Add multicast ccn route
    #pl_app.set_attribute_value("ccnroutes", "udp 224.0.0.204 2869")
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_app.connector("node").connect(pl_node.connector("apps"))

def create_ccnsendchunks(pl_node, slice_desc):
    pl_app = slice_desc.create("Application")
    path_to_video = os.path.join(os.path.dirname(os.path.abspath(__file__)),
        "big_buck_bunny_240p_mpeg4_lq.ts")
    pl_app.set_attribute_value("stdin", path_to_video)
    pl_app.set_attribute_value("command", "ccnsendchunks ccnx:/VIDEO")
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_app.connector("node").connect(pl_node.connector("apps"))
    return pl_app

def exec_ccncatchunks(slicename, hostname):
    print "Starting Vlc streamming ..."
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
    for hostname in hostnames:
        pl_node = create_node(hostname, pl_inet, slice_desc)
        pl_nodes[hostname] = pl_node

    # Get the base network segment (slice vsys_vnet) to assign all the IP addresses
    # to the virtual interfaces
    base = ipaddr.IPNetwork(vsys_vnet)

    # Calculate the number of virtual networks required to connect all the nodes 
    # with all other nodes as the binomial coeficient C(n, 2), with n = #nodes
    n = len(hostnames)
    c = math.factorial(n) / (2 * math.factorial(n-2)) 

    # Validate that we can get 'c' /30 subnetworks
    if c > math.pow(2, (30 - base.prefixlen)):
        raise RuntimeError("Insufficient address segment %s for experiment", vsys_vnet)
            
    # Create the subnetwors iterator 
    iter_sub = base.iter_subnets(new_prefix=30)

    # Create tunnels between nodes
    for i, node in enumerate(hostnames):
        peers = hostnames[i+1:]
        for peer in peers:
            subnet = iter_sub.next()
            create_tunnel(node, peer, pl_nodes, slice_desc, subnet)

    # Create ccnd daemons in all nodes
    for pl_node in pl_nodes.values():
        create_ccnd(pl_node, slice_desc)

    # Create a ccnsendchunks in a randomly chosen node to publish some content
    hostname = random.choice(pl_nodes.keys())
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

    proc = None
    if not TERMINATE:
        hostnames = pl_nodes.keys()
        hostnames.remove(hostname)
        # Randomnly choose a different hostname, than the one executing 
        # ccnsendchunks, to execute ccncatchunks and retrieve the VIDEO
        hostname = random.choice(hostnames)
        proc = exec_ccncatchunks(slicename, hostname)

    while not TERMINATE and proc and proc.poll() is None:
        time.sleep(0.5)
    
    if proc:
        if proc.poll() < 1:
           err = proc.stderr.read()
           print "ERROR ", err
        else:   
           out = proc.stdout.read()
           print "OUTPUT ", out

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
                 #'planetlab2.di.unito.it',
                 #'merkur.planetlab.haw-hamburg.de',
                 #'planetlab1.cs.uit.no',
                 #'planetlab3.cs.st-andrews.ac.uk',
                 #'planetlab2.cs.uoi.gr',
                 #'planetlab3.xeno.cl.cam.ac.uk',
                 #'planet2.inf.tu-dresden.de',
                 #'planetlab2.csg.uzh.ch',
                 #'planetlab2.upm.ro',
                 #'planetlab-um00.di.uminho.pt',
                 #'planetlabpc2.upf.edu',
                 #'planet2.elte.hu',
                 'planetlab2.esprit-tn.com' ]

    usage = "usage: %prog -s <pl_slice> -H <pl_host> -k <ssh_key> -u <pl_user> -p <pl_password> -v <vsys_vnet> -N <host_names> "

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
    (options, args) = parser.parse_args()

    hostnames = map(string.strip, options.hostnames.split(",")) if options.hostnames else default_hostnames 
    vsys_vnet = options.vsys_vnet
    slicename = options.slicename
    pl_host = options.pl_host
    pl_user= options.pl_user
    pl_pwd = options.pl_pwd
    pl_ssh_key = options.pl_ssh_key

    """
    hostnames = ['nepi1.pl.sophia.inria.fr',
        'nepi2.pl.sophia.inria.fr',
        'nepi3.pl.sophia.inria.fr',
        'nepi5.pl.sophia.inria.fr']

    pl_host = "nepiplc.pl.sophia.inria.fr"
    vsys_vnet = "192.168.2.0/24"
    """

    run(hostnames, vsys_vnet, slicename, pl_host, pl_user, pl_pwd, pl_ssh_key, 
            port_base, root_dir)

