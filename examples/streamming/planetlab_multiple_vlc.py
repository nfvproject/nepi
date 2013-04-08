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
        self.net_monitor = None
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
       "vlc -I dummy --repeat rtsp://%s:8554/TEST --sout '#std{access=file,mux=ts,dst=/dev/null}'" % (hostname))
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

def create_net_monitor(pl_node, slice_desc, pl_ifaces):
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
    pl_app.set_attribute_value("command", 
            "tcpdump -l -i eth0 -nNqttf '(%s)' -w - | pv -fbt >/dev/null 2>>{#[%s].trace[stdout].[name]#}" %
            (hosts, label))
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
        cpumem_stdout = controller.trace(mon.cpumem_monitor.guid, "stdout")
        net_stdout = controller.trace(mon.net_monitor.guid, "stdout")
        vlc_stderr = controller.trace(mon.vlc.guid, "stderr")

        results = dict({"cpumem": cpumem_stdout, "net": net_stdout, 
            "vlc_error": vlc_stderr})

        for name, stdout in results.iteritems():
            fpath = os.path.join(node_path, name)
            f = open(fpath, "w")
            f.write(stdout)
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
    parser.add_option("-t", "--time", dest="time_to_run", default = 1, 
            help="Time to run the experiment in hours", type="float")

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

    hostnames = ["planetlab1.rd.tut.fi", 
            "planetlab1.s3.kth.se", 
            "planetlab1.tlm.unavarra.es", 
            "planet1.servers.ua.pt", 
            "onelab3.warsaw.rd.tp.pl", 
            "gschembra3.diit.unict.it", 
            "iraplab1.iralab.uni-karlsruhe.de", 
            "host3-plb.loria.fr", 
            "kostis.di.uoa.gr", 
            "planetlab04.cnds.unibe.ch"]

    for hostname in hostnames:
        pl_node, pl_iface = create_node(hostname, pl_inet, slice_desc)
        cli_ifaces.append(pl_iface)

        # Create monitor info object for root node
        node_mon = MonitorInfo(hostname, MonitorInfo.TYPE_LEAF)
        monitors.append(node_mon)
      
        # Add memory and cpu monitoring for all nodes
        node_mon.cpumem_monitor = create_cpumem_monitor(pl_node, slice_desc)

        # Add network monitoring for all nodes
        node_mon.net_monitor = create_net_monitor(pl_node, slice_desc, [root_iface])

        # Add VLC clients
        vlc = create_vlc_client(root_node, pl_node, slice_desc)
        cli_apps.append(vlc)

        # Add reference to vlc app 
        node_mon.vlc = vlc

    # Add network monitoring for root node
    root_mon.net_monitor = create_net_monitor(root_node, slice_desc, cli_ifaces)

    xml = exp_desc.to_xml()
   
    controller = ExperimentController(xml, root_dir)
    controller.start()

    start_time = time.time()
    duration = time_to_run * 3600 # in seconds
    while not TERMINATE:
        time.sleep(1)
        if (time.time() - start_time) > duration: # elapsed time
            TERMINATE.append(None)

    controller.stop()
 
    # store results in results dir
    store_results(controller, monitors, results_dir, exp_label)
   
    controller.shutdown()

