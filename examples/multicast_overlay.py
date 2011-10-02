#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP
from nepi.testbeds.planetlab import util as plutil
from optparse import OptionParser
import os
import sys
import shutil
import tempfile
import time
import struct
import socket
import operator
import ipaddr
import gzip
import random

class PlanetLabMulticastOverlay:
    testbed_id = "planetlab"
    slicename = "inria_nepi"
    plchost = "www.planet-lab.eu"
    plkey = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
    pluser = os.environ.get("PL_USER")
    plpass = os.environ.get("PL_PASS")
    vnet = "192.168.3.0"
    
    port_base = 2000 + (os.getpid() % 1000) * 13
    
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        self.__class__.port_base = self.__class__.port_base + 100

    def tearDown(self):
        try:
            shutil.rmtree(self.root_dir)
        except:
            # retry
            time.sleep(0.1)
            shutil.rmtree(self.root_dir)

    def make_experiment_desc(self):
        testbed_id = self.testbed_id
        slicename = self.slicename
        plchost = self.plchost
        pl_ssh_key = self.plkey
        pl_user = self.pluser
        pl_pwd = self.plpass

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id)
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", slicename)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        pl_desc.set_attribute_value("plcHost", plchost)
        pl_desc.set_attribute_value("tapPortBase", self.port_base)
        pl_desc.set_attribute_value("p2pDeployment", True)
        pl_desc.set_attribute_value("dedicatedSlice", True)
        pl_desc.set_attribute_value("plLogLevel", "INFO")
   
        netns_provider = FactoriesProvider("netns")
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self.root_dir)
        netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        netns_root_dir = os.path.join(self.root_dir, "netns")
        os.mkdir(netns_root_dir)
        netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
        netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        netns_desc.set_attribute_value(DC.USE_SUDO, True)

        return pl_desc, netns_desc, exp_desc
    

    def make_pl_tapnode(self, pl, ip, inet = None, label = None, hostname = None, routes = None, mcast = False, mcastrouter = False):
        if not isinstance(ip, list):
            ips = [ip]
        else:
            ips = ip
        node1 = pl.create("Node")
        if label: 
            node1.set_attribute_value("label", label)
        if hostname: 
            node1.set_attribute_value("hostname", hostname)
        iface1 = pl.create("NodeInterface")
        if label:
            iface1.set_attribute_value("label", label+"iface")
        tap1 = []
        tap1ip = []
        for i,ip in enumerate(ips):
            _tap1 = pl.create("TapInterface")
            _tap1.set_attribute_value("multicast", True)
            _tap1.enable_trace("pcap") # for error output
            if label:
                _tap1.set_attribute_value("label", label+"tap"+(str(i+1) if i else ""))
        
            _tap1ip = _tap1.add_address()
            _tap1ip.set_attribute_value("Address", ip)
            _tap1ip.set_attribute_value("NetPrefix", 32)
            _tap1ip.set_attribute_value("Broadcast", False)
        
            node1.connector("devs").connect(_tap1.connector("node"))
            
            tap1.append(_tap1)
            tap1ip.append(_tap1ip)
            
        inet = inet or pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        for destip, destprefix, nexthop in routes:
            r1 = node1.add_route()
            r1.set_attribute_value("Destination", destip)
            r1.set_attribute_value("NetPrefix", destprefix)
            r1.set_attribute_value("NextHop", nexthop)
        
        if mcast:
            fwd = pl.create("MulticastForwarder")
            fwd.enable_trace("stderr")
            fwd.connector("node").connect(node1.connector("apps"))
            if mcastrouter:
                mrt = pl.create("MulticastRouter")
                mrt.connector("fwd").connect(fwd.connector("router"))
                mrt.enable_trace("stderr")
                
        return node1, iface1, tap1, tap1ip, inet
    
    def add_vlc_base(self, pl, node):
        app = pl.create("Application")
        app.set_attribute_value("rpmFusion", True)
        app.set_attribute_value("depends", "vlc")
        app.set_attribute_value("command", "vlc --version")
        app.enable_trace("stdout")
        app.enable_trace("stderr")
        node.connector("apps").connect(app.connector("node"))
        return app
    
    def add_vlc_restreamer(self, pl, node):
        hostname = node.get_attribute_value("hostname")
        app = self.add_vlc_base(pl, node)
        app.set_attribute_value("label","vlc_restreamer_%d" % (node.guid,))
        app.set_attribute_value("command",
            "vlc -vvv -I dummy"
            " udp://@239.255.12.42"
            " --sout '#rtp{port=6060,sdp=rtsp://"+hostname+":8080/test.sdp}'")
        return app
    
    def add_vlc_dumper(self, pl, node):
        app = self.add_vlc_base(pl, node)
        app.set_attribute_value("label","vlc_dumper_%d" % (node.guid,))
        app.set_attribute_value("command",
            "vlc -vvv -I dummy"
            " udp://@239.255.12.42"
            " --sout output")
        app.enable_trace("output")
        return app
    
    def add_vlc_source(self, netns, node, iflabel):
        app = netns_desc.create("Application")
        app.set_attribute_value("user", os.getlogin())
        app.set_attribute_value("label","vlc_source_%d" % (node.guid,))
        app.set_attribute_value("command",
            "vlc -vvv -I dummy "
            +os.path.basename(self.movie_source)
            +"--miface-addr {#[%s].addr[0].[Address]#} " % (iflabel,)
            +"--sout '#udp{dst=239.255.12.42,ttl=64}'")
        app.connector("node").connect(node.connector("apps"))
        return app
    
    def add_net_monitor(self, pl, node):
        app = pl.create("Application")
        app.set_attribute_value("label","network_monitor_%d" % (node.guid,))
        app.set_attribute_value("command", 
            r"""head -n 2 /proc/net/dev ; while true ; do cat /proc/net/dev | sed -r 's/.*/'"$(date -R)"': \0/' | grep eth0 ; sleep 1 ; done""")
        app.enable_trace("stdout")
        node.connector("apps").connect(app.connector("node"))
        return app
    
    def make_ns_in_pl(self, pl, exp, node1, iface1, root):
        ns3_testbed_id = "ns3"
        
        # Add NS3 support in node1
        plnepi = pl.create("NepiDependency")
        plns3 = pl.create("NS3Dependency")
        plnepi.connector("node").connect(node1.connector("deps"))
        plns3.connector("node").connect(node1.connector("deps"))

        # Create NS3 testbed running in node1
        ns3_provider = FactoriesProvider(ns3_testbed_id)
        ns3_desc = exp.add_testbed_description(ns3_provider)
        ns3_desc.set_attribute_value("rootDirectory", root)
        ns3_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns3_desc.set_attribute_value("ChecksumEnabled", True)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[%s].addr[0].[Address]#}" % (
            iface1.get_attribute_value("label"),))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns3_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "{#[%s].[%s]#}" % (
                node1.get_attribute_value("label"),
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))
        ns3_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        
        return ns3_desc
    
    def make_netns_node(self, netns_desc):
        node = netns_desc.create("Node")
        node.set_attribute_value("forward_X11", True)
        return node

    def make_pl_netns_connection(self, pl_desc, pl_node, netns_desc,
            netns_node, netns_iface_label, vnet):
        base = struct.unpack('!L',socket.inet_aton(vnet))[0]
        netns_addr = socket.inet_ntoa(struct.pack('!L',(base | 1)))
        pl_addr = socket.inet_ntoa(struct.pack('!L',(base | 2)))

        pl_tap = pl_desc.create("TunInterface")
        pl_tap.set_attribute_value("multicast", True) 
        #pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        #pl_tap.enable_trace("pcap")
        #pl_tap.enable_trace("packets")
        addr = pl_tap.add_address()
        adrr.set_attribute_value("Address", pl_addr)
        addr.set_attribute_value("NetPrefix", 32)
        addr.set_attribute_value("Broadcast", False)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        
        netns_tap = netns_desc.create("TunNodeInterface")
        netns_tap.set_attribute_value("label", netns_iface_label)
        netns_tap.set_attribute_value("up", True)
        netns_tap.set_attribute_value("mtu", 1448)
        addr = netns_tap.add_address()
        adrr.set_attribute_value("Address", netns_addr)
        addr.set_attribute_value("NetPrefix", 32)
        addr.set_attribute_value("Broadcast", False)
        route = netns_node.add_route()
        route.set_attribute_value("Destination", vnet)
        r1.set_attribute_value("NetPrefix", 24)
        r1.set_attribute_value("NextHop", pl_addr)
        netns_node.connector("devs").connect(netns_tap.connector("node"))

        netns_tunchannel = netns_desc.create("TunChannel")
        #netns_tunchannel.set_attribute_value("tun_cipher", "PLAIN") 
        netns_tunchannel.connector("->fd").connect(netns_tap.connector("fd->"))
        pl_tap.connector("tcp").connect(netns_tunchannel.connector("tcp"))

    def make_pl_overlay(self, numnodes, num_wifi):
        ns3_testbed_id = "ns3"
        
        pl, netns, exp = self.make_experiment_desc()
        # We'll make a distribution spanning tree using prefix matching as a distance
        api = plutil.getAPI(self.pluser, self.plpass)
        nodes = plutil.getNodes(api, numnodes, operatingSystem = 'f12')
        root = min(nodes, key=operator.attrgetter('hostname'))
        links = list(plutil.getSpanningTree(nodes, root=root))
      
        for node in nodes:
            node.vif_ips = set()
            node.children = []
            node.childips = set()
        
        # Build an explicit tree
        for slave, master in links:
            master.children.append(slave)
        
        # We have to assign IPs and routes.
        # The IP will be assigned sequentially, depth-first.
        # This will result in rather compact routing rules
        nextip = [128-numnodes]
        def traverse(traverse, node, parent=None, base=struct.unpack('!L',socket.inet_aton(self.vnet))[0]):
            if nextip[0] >= 254:
                raise RuntimeError, "Too many IPs to assign!"
            
            node.vif_addr = base | (nextip[0])
            nips = 1+len(node.children) # one vif per child, plus one for the parent
            nextip[0] += nips
            
            for i in xrange(nips):
                node.vif_ips.add(node.vif_addr+i)

            if parent:
                parent.childips.update(node.vif_ips)

            for i,child in enumerate(node.children):
                traverse(traverse, child, node, base)
                
            if parent:
                parent.childips.update(node.childips)
                
        traverse(traverse, root)
        
        def printtree(printtree, node, indent=''):
            print indent, '-', socket.inet_ntoa(struct.pack('!L',node.vif_addr)), node.country, node.city, node.site
            for child in node.children:
                childips = map(ipaddr.IPAddress, child.childips)
                childnets = ipaddr.collapse_address_list(childips)
                cip = ipaddr.IPAddress(child.vif_addr)
                for cnet in childnets:
                    print indent, '|- R', cnet, '->', cip
                printtree(printtree, child, indent+' | ')
        printtree(printtree, root)

        inet = pl.create("Internet")
        
        def maketree(maketree, node, parent=None, parentIp=None):
            routes = []
            ctaps = []
            for i,child in enumerate(node.children):
                childips = map(ipaddr.IPAddress, child.childips)
                childnets = ipaddr.collapse_address_list(childips)
                cip = ipaddr.IPAddress(child.vif_addr)
                pip = ipaddr.IPAddress(node.vif_addr+1+i)
                for cnet in childnets:
                    routes.append((cnet.ip.exploded, cnet.prefixlen, cip.exploded))
                ctaps.append( maketree(maketree, child, node, pip) )
            if parentIp:
                routes.append((self.vnet,24,parentIp))
            
            if not parent:
                label = "root"
            else:
                label = None
            ips = [ ipaddr.IPAddress(node.vif_addr+i) for i in xrange(1+len(node.children)) ]
            node1, iface1, tap1, tap1ip, _ = self.make_pl_tapnode(pl, ips, inet, 
                hostname = node.hostname,
                routes = routes,
                mcastrouter = bool(node.children),
                mcast = True,
                label = label )
            
            for tap, ctap in zip(tap1[1:], ctaps):
                tap.connector("udp").connect(ctap.connector("udp"))
            
            self.add_net_monitor(pl, node1)
            self.add_vlc_restreamer(pl, node1)
            if random.random() < 0.1 and parent:
                self.add_vlc_dumper(pl, node1)
            
            return tap1[0]
        maketree(maketree, root)

        # create a netns node and connect it to the root pl node
        pl_root = exp_desc.get_element_by_label("root")
        netns_source = self.make_netns_node(netns)
        iflabel = "source-iface"
        self.make_pl_netns_connection(pl_desc, pl_root, netns_desc, 
                netns_source, iflabel, self.vnet)
        self.add_vlc_source(netns, netns_n, iflabel)
 
        xml = exp.to_xml()
        test_dir = "./results"

        try:
            controller = ExperimentController(xml, self.root_dir)
            controller.start()
            
            print >>sys.stderr, "Press CTRL-C to shut down"
            try:
                while True:
                    time.sleep(10)
            except KeyboardInterrupt:
                pass
            
            # download results
            for testbed_guid, guids in controller.traces_info().iteritems():
                for guid, traces in guids.iteritems():
                    for name, data in traces.iteritems():
                        path = data["filepath"]
                        
                        if not path:
                            continue
                        
                        print >>sys.stderr, "Downloading trace", path
                        
                        filepath = os.path.join(test_dir, path)
                        
                        try:
                            trace = controller.trace(guid, name)
                        except:
                            traceback.print_exc(file=sys.stderr)
                            continue
                        try:
                            if not os.path.exists(os.path.dirname(filepath)):
                                os.makedirs(os.path.dirname(filepath))
                        except:
                            traceback.print_exc(file=sys.stderr)
                        
                        try:
                            if len(trace) >= 2**20:
                                # Bigger than 1M, compress
                                tracefile = gzip.GzipFile(filepath+".gz", "wb")
                            else:
                                tracefile = open(filepath,"wb")
                            try:
                                tracefile.write(trace)
                            finally:
                                tracefile.close()
                        except:
                            traceback.print_exc(file=sys.stderr)
        finally:
            try:
                controller.stop()
            except:
                import traceback
                traceback.print_exc()
            try:
                controller.shutdown()
            except:
                import traceback
                traceback.print_exc()


if __name__ == '__main__':
    usage = "usage: %prog -n number_sta -m movie -u user"
    parser = OptionParser(usage=usage)
    parser.add_option("-u", "--user", dest="user", help="Valid linux system user (not root).", type="str")
    parser.add_option("-m", "--movie", dest="movie", help="Path to movie file to play", type="str")
    parser.add_option("-n", "--nsta", dest="nsta", help="Number of wifi stations", type="int")
    parser.add_option("-N", "--nodes", dest="nsta", help="Number of overlay nodes", type="int")
    parser.add_option("-a", "--base_addr", dest="base_addr", help="Base address segment for the experiment", type="str")
    parser.add_option("-s", "--slicename", dest="slicename", help="PlanetLab slice", type="str")
    (options, args) = parser.parse_args()
    if not options.movie:
        parser.error("Missing 'movie' option.")
    if options.user == 'root':
        parser.error("Missing or invalid 'user' option.")
    if options.nsta and options.nsta > 8:
        parser.error("Try a number of stations under 9.")

    exp = PlanetLabMulticastOverlay()
    exp.movie_source = options.movie
    try:
        exp.setUp()
        exp.make_pl_overlay(50, 8)
    finally:
        exp.tearDown()

