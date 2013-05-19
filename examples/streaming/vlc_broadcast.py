#!/usr/bin/env python

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util.constants import ApplicationStatus as AS
from optparse import OptionParser, SUPPRESS_HELP
import os
import tempfile
import time
import uuid

"""
This experiment evaluates the consumption of computer resources when using
VLC for Internet broasdcasting using PlanetLab nodes as both server and clients. 
A root node (server) streams a broadcast in a loop, while the clients retrieve
the same video over and over until experiment run time is elapsed.

While the experiment is running cpu and memory usage, and the amount of bytes 
transmitted per stream are traced to files.

"""

# Trak SIGTERM, and set global termination flag instead of dying
import signal
TERMINATE = []
def _finalize(sig,frame):
    global TERMINATE
    TERMINATE.append(None)
signal.signal(signal.SIGTERM, _finalize)
signal.signal(signal.SIGINT, _finalize)

class MonitorInfo(object):
    TYPE_ROOT = "root"
    TYPE_LEAF = "leaf"

    def __init__(self, hostname, type):
        self.hostname = hostname
        self.type = type
        self.cpumem_monitor = None
        self.net_in_monitor = None
        self.net_out_monitor = None
        self.vlc = None

def create_slice(exp_desc, slicename, plc_host, pl_user, pl_pwd, 
        pl_ssh_key, root_dir):
    pl_provider = FactoriesProvider("planetlab")
    slice_desc = exp_desc.add_testbed_description(pl_provider)
    slice_desc.set_attribute_value("homeDirectory", root_dir)
    slice_desc.set_attribute_value("slice", slicename)
    slice_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
    slice_desc.set_attribute_value("authUser", pl_user)
    slice_desc.set_attribute_value("authPass", pl_pwd)
    slice_desc.set_attribute_value("plcHost", plc_host)
    # Kills all running processes before starting the experiment
    slice_desc.set_attribute_value("cleanProc", True)
    # NOTICE: Setting 'cleanHome' to 'True' will erase all previous
    # folders in the sliver Home directory, including result files!
    slice_desc.set_attribute_value("cleanHome", True)
    slice_desc.set_attribute_value("plLogLevel", "DEBUG")
    return slice_desc
 
def create_node(hostname, pl_inet, slice_desc):
    pl_node = slice_desc.create("Node")
    pl_node.set_attribute_value("hostname", hostname)
    pl_node.set_attribute_value("label", "%d" % pl_node.guid)
    pl_node.set_attribute_value("operatingSystem", "f12")
    pl_iface = slice_desc.create("NodeInterface")
    pl_iface.set_attribute_value("label", "iface_%d" % pl_node.guid)
    pl_iface.connector("inet").connect(pl_inet.connector("devs"))
    pl_node.connector("devs").connect(pl_iface.connector("node"))
    return pl_node, pl_iface

def create_vlc_server(movie, pl_node, slice_desc):
    mv = os.path.basename(movie)
    pl_app = slice_desc.create("Application")
    pl_app.set_attribute_value("rpmFusion", True)
    pl_app.set_attribute_value("depends", "vlc")
    pl_app.set_attribute_value("build", 
    #    "echo -e 'new TEST vod enabled\\nsetup TEST input %s' > ${SOURCES}/VOD.vlm" % mv)
       "echo -e 'new TEST broadcast enabled loop\\n"\
       "setup TEST input %s\\n"\
       "setup TEST output #rtp{mux=ts,sdp=rtsp://0.0.0.0:8554/TEST}\\n\\n"\
       "new test_sched schedule enabled\\n"\
       "setup test_sched append control TEST play' > ${SOURCES}/VOD.vlm" % mv)

    pl_app.set_attribute_value("sources", "%s" % movie)
    pl_app.set_attribute_value("command",
        "sudo -S dbus-uuidgen --ensure ; vlc -vvv -I dummy --vlm-conf VOD.vlm")
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_node.connector("apps").connect(pl_app.connector("node"))
    return pl_app

def create_vlc_client(root_node, pl_node, slice_desc):
    label = "%d_app" % pl_node.guid
    hostname = root_node.get_attribute_value("hostname")
    pl_app = slice_desc.create("Application")
    pl_app.set_attribute_value("label", label)
    pl_app.set_attribute_value("rpmFusion", True)
    pl_app.set_attribute_value("depends", "vlc")
    pl_app.set_attribute_value("command",
       "sudo -S dbus-uuidgen --ensure ; sleep 5;" \
       "vlc -I dummy rtsp://%s:8554/TEST --sout '#std{access=file,mux=ts,dst=/dev/null}'" % (hostname))
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_node.connector("apps").connect(pl_app.connector("node"))
    return pl_app

def create_cpumem_monitor(pl_node, slice_desc):
    """ This function creates a monitoring application for the
    utilization of node resources by the vlc application.

    The format of the stdout trace file is the following:
    'timestamp cpu(%) mem(%) time'
    """
    label = "%d_cpumem" % pl_node.guid
    pl_app = slice_desc.create("Application")
    pl_app.set_attribute_value("label", label)
    pl_app.set_attribute_value("command", 
            "while true ; do echo $(date +%Y%m%d%H%M%S%z) " \
            " $(top -b -n 1 | grep 'vlc' | head -1 | sed 's/\s\s*/ /g' | sed 's/^\s//g' | cut -d' ' -f9,10,11)" \
            "; sleep 1 ; done")
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_node.connector("apps").connect(pl_app.connector("node"))
    return pl_app

def create_net_monitor(pl_node, slice_desc, pl_ifaces, pcap=False):
    """ This function creates a monitoring application for the
    amount of bytes transmitted/received by the vlc application.

    The format of the stdout trace file is the following:
    'total-Mbytes total-time'
    """
    label = "%d_net" % pl_node.guid
    hosts = " or ".join(map(lambda pl_iface: " ( host {#[%s].addr[0].[Address]#} ) " % 
        pl_iface.get_attribute_value("label"), pl_ifaces))
    pl_app = slice_desc.create("Application")
    pl_app.set_attribute_value("label", label)
    pl_app.set_attribute_value("rpmFusion", True)
    pl_app.set_attribute_value("sudo", True)
    pl_app.set_attribute_value("depends", "tcpdump pv")

    output = "/dev/null"
    if pcap:
        output = "{#[%s].trace[output].[name]#}" % label

    pl_app.set_attribute_value("command", 
            "tcpdump -l -i eth0 -s 0 -f '(%s)' -w - | pv -fbt >%s 2>>{#[%s].trace[stdout].[name]#}" %
            (hosts, output, label))

    if pcap:
        pl_app.enable_trace("output")
    
    pl_app.enable_trace("stdout")
    pl_app.enable_trace("stderr")
    pl_node.connector("apps").connect(pl_app.connector("node"))
    return pl_app

def store_results(controller, monitors, results_dir, exp_label):
    # create results directory for experiment
    root_path = os.path.join(results_dir, exp_label)

    print "STORING RESULTS in ", root_path

    try:
        os.makedirs(root_path)
    except OSError:
        pass

    # collect information on nodes
    hosts_info = ""

    for mon in monitors:
        hosts_info += "%s %s\n" % (mon.hostname, mon.type)

        # create a subdir per hostname
        node_path = os.path.join(root_path, mon.hostname)
        try:
            os.makedirs(node_path)
        except OSError:
            pass

        # store monitoring results
   
        cpumem_out = controller.trace(mon.cpumem_monitor.guid, "stdout")

        net_in = None
        if mon.net_in_monitor:
            net_in = controller.trace(mon.net_in_monitor.guid, "stdout")
        
        net_out = None
        if mon.net_out_monitor:
            net_out = controller.trace(mon.net_out_monitor.guid, "stdout")

        vlc_err = controller.trace(mon.vlc.guid, "stderr")
        vlc_out = controller.trace(mon.vlc.guid, "stdout")

        results = dict({
            "cpumem": cpumem_out, 
            "net_in": net_in, 
            "net_out": net_out, 
            "vlc_out": vlc_out,
            "vlc_err": vlc_err })

        for name, result in results.iteritems():
            if not result:
                continue

            fpath = os.path.join(node_path, name)
            f = open(fpath, "w")
            f.write(result)
            f.close()

    # store node info file
    fpath = os.path.join(root_path, "hosts")
    f = open(fpath, "w")
    f.write(hosts_info)
    f.close()

def get_options():
    slicename = os.environ.get("PL_SLICE")
    pl_host = os.environ.get("PL_HOST", "www.planet-lab.eu")
    pl_ssh_key = os.environ.get(
        "PL_SSH_KEY",
        "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
    pl_user = os.environ.get('PL_USER')
    pl_pwd = os.environ.get('PL_PASS')
    exp_label = "%s" % uuid.uuid4()

    usage = "usage: %prog -s <pl_slice> -H <pl_host> -k <ssh_key> -u <pl_user> \
            -p <pl_password> -m <movie> -r <results-dir> -l <experiment-label>"

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
    parser.add_option("-m", "--movie", dest="movie", 
            help="Stream movie", type="str")
    parser.add_option("-r", "--results", dest="results_dir", default = "/tmp", 
            help="Path to directory to store results", type="str")
    parser.add_option("-l", "--label", dest="exp_label", default = exp_label, 
            help="Label to identify experiment results", type="str")
    parser.add_option("-t", "--time", dest="time_to_run", default = 20, 
            help="Time to run the experiment in minutes", type="float")

    (options, args) = parser.parse_args()

    if not options.movie:
        parser.error("movie is a required argument")

    return (options.slicename, options.pl_host, options.pl_user, 
            options.pl_pwd, options.pl_ssh_key, options.movie,
            options.results_dir, options.exp_label, options.time_to_run)

if __name__ == '__main__':
    root_dir = tempfile.mkdtemp()
    (pl_slice, 
            pl_host, 
            pl_user, 
            pl_pwd, 
            pl_ssh_key, 
            movie, 
            results_dir,
            exp_label,
            time_to_run) = get_options()

    # list to store information on monitoring apps per node
    monitors = []
    
    # Create the experiment description object
    exp_desc = ExperimentDescription()

    # Create slice
    slice_desc = create_slice(exp_desc, pl_slice, pl_host, pl_user, pl_pwd,
        pl_ssh_key, root_dir)
   
    # Create the Internet box object
    pl_inet = slice_desc.create("Internet")

    # Create root node
    hostname = "ple6.ipv6.lip6.fr"
    (root_node, root_iface) = create_node(hostname, pl_inet, slice_desc)

    # Create monitor info object for root node
    root_mon = MonitorInfo(hostname, MonitorInfo.TYPE_ROOT)
    monitors.append(root_mon)

    # Add VLC service
    root_vlc = create_vlc_server(movie, root_node, slice_desc)
    
    # Add memory and cpu monitoring for root node
    root_mon.cpumem_monitor = create_cpumem_monitor(root_node, slice_desc)

    # Add reference to vlc app 
    root_mon.vlc = root_vlc

    # Create leaf nodes
    cli_apps = []
    cli_ifaces = []

    hostnames = [#"planetlab1.rd.tut.fi",
             "planetlab-2.research.netlab.hut.fi",
             "planetlab2.willab.fi",
             "planetlab3.hiit.fi",
             "planetlab4.hiit.fi",
             "planetlab1.willab.fi",
             "planetlab1.s3.kth.se",
             "itchy.comlab.bth.se",
             "planetlab-1.ida.liu.se",
             #"scratchy.comlab.bth.se",
             "planetlab2.s3.kth.se",
             "planetlab1.sics.se",
             "planetlab1.tlm.unavarra.es",
             #"planetlab2.uc3m.es",
             "planetlab2.upc.es",
             #"ait21.us.es",
             "planetlab3.upc.es",
             #"planetlab1.uc3m.es",
             "planetlab2.dit.upm.es",
             "planetlab1.upc.es",
             "planetlab2.um.es",
             "planet1.servers.ua.pt",
             "planetlab2.fct.ualg.pt",
             "planetlab-1.tagus.ist.utl.pt",
             "planetlab-2.tagus.ist.utl.pt",
             "planetlab-um00.di.uminho.pt",
             "planet2.servers.ua.pt",
             "planetlab1.mini.pw.edu.pl",
             "roti.mimuw.edu.pl",
             "planetlab1.ci.pwr.wroc.pl",
             "planetlab1.pjwstk.edu.pl",
             "ple2.tu.koszalin.pl",
             #"planetlab2.ci.pwr.wroc.pl",
             "planetlab2.cyfronet.pl",
             "plab2.ple.silweb.pl",
             "planetlab1.cyfronet.pl",
             "plab4.ple.silweb.pl",
             "ple2.dmcs.p.lodz.pl",
             "planetlab2.pjwstk.edu.pl",
             "ple1.dmcs.p.lodz.pl",
             "pandora.we.po.opole.pl",
             "gschembra3.diit.unict.it",
             #"onelab6.iet.unipi.it",
             #"planetlab1.science.unitn.it",
             "planetlab-1.ing.unimo.it",
             "gschembra4.diit.unict.it",
             "iraplab1.iralab.uni-karlsruhe.de",
             "planetlab-1.fokus.fraunhofer.de",
             "iraplab2.iralab.uni-karlsruhe.de",
             "planet2.zib.de",
             "pl2.uni-rostock.de",
             "onelab-1.fhi-fokus.de",
             "planet2.l3s.uni-hannover.de",
             "planetlab1.exp-math.uni-essen.de",
             "planetlab-2.fokus.fraunhofer.de",
             "planetlab02.tkn.tu-berlin.de",
             "planetlab1.informatik.uni-goettingen.de",
             "planetlab1.informatik.uni-erlangen.de",
             "planetlab2.exp-math.uni-essen.de",
             "planetlab2.lkn.ei.tum.de",
             "planetlab1.wiwi.hu-berlin.de",
             "planet1.l3s.uni-hannover.de",
             "planetlab1.informatik.uni-wuerzburg.de",
             "host3-plb.loria.fr",
             "inriarennes1.irisa.fr",
             "inriarennes2.irisa.fr",
             "peeramide.irisa.fr",
             #"pl1.bell-labs.fr",
             #"pl2.bell-labs.fr",
             "host4-plb.loria.fr",
             "planetlab-1.imag.fr",
             "planetlab-2.imag.fr",
             "ple2.ipv6.lip6.fr",
             "planetlab1.u-strasbg.fr",
             "kostis.di.uoa.gr",
             "planetlab1.ionio.gr",
             "planetlab2.ionio.gr",
             "planetlab2.cs.uoi.gr",
             "stella.planetlab.ntua.gr",
             "vicky.planetlab.ntua.gr",
             "planetlab1.cs.uoi.gr",
             "pl002.ece.upatras.gr",
             "planetlab04.cnds.unibe.ch",
             "lsirextpc01.epfl.ch",
             "planetlab2.csg.uzh.ch",
             "planetlab1.csg.uzh.ch",
             "planetlab-2.cs.unibas.ch",
             "planetlab-1.cs.unibas.ch",
             "planetlab4.cs.st-andrews.ac.uk",
             "planetlab-1.imperial.ac.uk",
             "planetlab3.xeno.cl.cam.ac.uk",
             "planetlab1.xeno.cl.cam.ac.uk",
             "planetlab2.xeno.cl.cam.ac.uk",
             "planetlab3.cs.st-andrews.ac.uk",
             "planetlab1.aston.ac.uk",
             "planetlab1.nrl.eecs.qmul.ac.uk",
             "chimay.infonet.fundp.ac.be",
             "orval.infonet.fundp.ac.be",
             "rochefort.infonet.fundp.ac.be",
             #"planck227ple.test.ibbt.be",
            ]


    for hostname in hostnames:
        pl_node, pl_iface = create_node(hostname, pl_inet, slice_desc)
        cli_ifaces.append(pl_iface)

        # Create monitor info object for root node
        node_mon = MonitorInfo(hostname, MonitorInfo.TYPE_LEAF)
        monitors.append(node_mon)
      
        # Add memory and cpu monitoring for all nodes
        node_mon.cpumem_monitor = create_cpumem_monitor(pl_node, slice_desc)

        # Add network monitoring for all nodes
        node_mon.net_out_monitor = create_net_monitor(pl_node, slice_desc, [root_iface])

        # Add VLC clients
        vlc = create_vlc_client(root_node, pl_node, slice_desc)
        cli_apps.append(vlc)

        # Add reference to vlc app 
        node_mon.vlc = vlc

    # Add network monitoring for root node
    #root_mon.net_monitor = create_net_monitor(root_node, slice_desc, cli_ifaces, pcap=True)
    root_mon.net_out_monitor = create_net_monitor(root_node, slice_desc, cli_ifaces)

    xml = exp_desc.to_xml()
   
    controller = ExperimentController(xml, root_dir)
    controller.start()

    start_time = time.time()
    duration = time_to_run * 60 # in seconds
    while not TERMINATE:
        time.sleep(1)
        if (time.time() - start_time) > duration: # elapsed time
            TERMINATE.append(None)

    controller.stop()
 
    # store results in results dir
    store_results(controller, monitors, results_dir, exp_label)
   
    controller.shutdown()

