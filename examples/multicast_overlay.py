#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
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
import math

sys.path.append("../../src")

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP
from nepi.testbeds.planetlab import util as plutil

class PlanetLabMulticastOverlay:
    testbed_id = "planetlab"
    slicename = "inria_nepi12"
    plchost = "www.planet-lab.eu"
    plkey = os.environ.get(
            "PL_SSH_KEY",
            "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
    pluser = os.environ.get("PL_USER")
    plpass = os.environ.get("PL_PASS")
    vnet = "192.168.2.0"
    
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
        netns = exp_desc.add_testbed_description(netns_provider)
        netns.set_attribute_value("homeDirectory", self.root_dir)
        netns.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        netns_root_dir = os.path.join(self.root_dir, "netns")
        os.mkdir(netns_root_dir)
        netns.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
        netns.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        netns.set_attribute_value(DC.USE_SUDO, True)

        return pl_desc, netns, exp_desc

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
        
            _tap1ip = self.add_ip_address(_tap1, ip, 32)
            
            node1.connector("devs").connect(_tap1.connector("node"))
            
            tap1.append(_tap1)
            tap1ip.append(_tap1ip)
            
        inet = inet or pl.create("Internet")
        node1.connector("devs").connect(iface1.connector("node"))
        iface1.connector("inet").connect(inet.connector("devs"))
        
        for destip, destprefix, nexthop in routes:
            r1 = self.add_route(node1, destip, destprefix, nexthop)
        
        if mcast:
            fwd = pl.create("MulticastForwarder")
            fwd.enable_trace("stderr")
            fwd.connector("node").connect(node1.connector("apps"))
            if mcastrouter:
                mrt = pl.create("MulticastRouter")
                mrt.connector("fwd").connect(fwd.connector("router"))
                mrt.enable_trace("stderr")
                
        return node1, iface1, tap1, tap1ip, inet

    def add_ip_address(self, iface, address, netprefix, broadcast = False):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)
        ip.set_attribute_value("NetPrefix", netprefix)
        ip.set_attribute_value("Broadcast", broadcast)
        return ip

    def add_route(self, node, destination, netprefix, nexthop):
        route = node.add_route()
        route.set_attribute_value("Destination", destination)
        route.set_attribute_value("NetPrefix", netprefix)
        route.set_attribute_value("NextHop", nexthop)
        return route

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
        app = netns.create("Application")
        app.set_attribute_value("user", self.user)
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
        ns = exp.add_testbed_description(ns3_provider)
        ns.set_attribute_value("rootDirectory", root)
        ns.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns.set_attribute_value("ChecksumEnabled", True)
        ns.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[%s].addr[0].[Address]#}" % (
            iface1.get_attribute_value("label"),))
        ns.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "{#[%s].[%s]#}" % (
                node1.get_attribute_value("label"),
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))
        ns.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        
        return ns
  
    def add_pl_ns_node(self, pl_desc, inet, label_prefix):
        node = pl_desc.create("Node")
        node.set_attribute_value("label", label_prefix)
        iface = pl_desc.create("NodeInterface")
        iface.set_attribute_value("label", label_prefix+"iface")
        iface.connector("inet").connect(inet.connector("devs"))
        node.connector("devs").connect(iface.connector("node"))
        forwarder = pl_desc.create("MulticastForwarder")
        forwarder.enable_trace("stderr")
        node.connector("apps").connect(forwarder.connector("node"))
        return node, iface

    def add_pl_ns_connection(self, pl_desc, pl_node, pl_addr,
            ns, ns_node, ns_addr):
        pl_tap = pl_desc.create("TapInterface")
        pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        self.add_ip_address(pl_tap, pl_addr, 31)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        ns_fdnd = ns.create("ns3::FdNetDevice")
        ns_node.connector("devs").connect(ns_fdnd.connector("node"))
        self.add_ip_address(ns_fdnd, ns_addr, 31)
        pl_tap.connector("fd->").connect(ns_fdnd.connector("->fd"))

    def add_pl_ns_tunchan_connection(self, pl_desc, pl_node, pl_addr,
            ns, ns_node, ns_addr):
        pl_tap = pl_desc.create("TunInterface")
        self.add_ip_address(pl_tap, pl_addr, 31)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        ns_fdnd = ns.create("ns3::FdNetDevice")
        ns_fdnd.enable_trace("FdPcapTrace")
        self.add_ip_address(ns_fdnd, ns_addr, 31)
        ns_node.connector("devs").connect(ns_fdnd.connector("node"))
        ns_tc = ns.create("ns3::Nepi::TunChannel")
        ns_tc.connector("fd->").connect(ns_fdnd.connector("->fd"))
        pl_tap.connector("tcp").connect(ns_tc.connector("tcp"))

    def make_netns_node(self, netns):
        node = netns.create("Node")
        node.set_attribute_value("forward_X11", True)
        command = "xterm" 
        app = netns.create("Application")
        app.set_attribute_value("command", command)
        app.set_attribute_value("user", self.user)
        app.connector("node").connect(node.connector("apps"))
        return node

    def make_pl_netns_connection(self, pl_desc, pl_node, netns,
            netns_node, netns_iface_label):
        base=struct.unpack('!L',socket.inet_aton(self.vnet))[0]
        netns_addr = socket.inet_ntoa(struct.pack('!L',(base | 1)))
        pl_addr = socket.inet_ntoa(struct.pack('!L',(base | 2)))
        pl_tap = pl_desc.create("TunInterface")
        pl_tap.set_attribute_value("multicast", True) 
        #pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        #pl_tap.enable_trace("pcap")
        #pl_tap.enable_trace("packets")
        self.add_ip_address(pl_tap, pl_addr, 31)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        
        netns_tap = netns.create("TunNodeInterface")
        netns_tap.set_attribute_value("label", netns_iface_label)
        netns_tap.set_attribute_value("up", True)
        netns_tap.set_attribute_value("mtu", 1448)
        self.add_ip_address(netns_tap, netns_addr, 31)
        self.add_route(netns_node, self.vnet, 24, pl_addr)
        netns_node.connector("devs").connect(netns_tap.connector("node"))

        netns_tunchannel = netns.create("TunChannel")
        #netns_tunchannel.set_attribute_value("tun_cipher", "PLAIN") 
        netns_tunchannel.connector("->fd").connect(netns_tap.connector("fd->"))
        pl_tap.connector("tcp").connect(netns_tunchannel.connector("tcp"))

    def add_ns_fdnd(self, ns, node):
        fdnd = ns.create("ns3::FdNetDevice")
        node.connector("devs").connect(fdnd.connector("node"))
        #fdnd.enable_trace("FdPcapTrace")
        return fdnd

    def add_ns_node(self, ns):
        node = ns.create("ns3::Node")
        ipv4 = ns.create("ns3::Ipv4L3Protocol")
        arp  = ns.create("ns3::ArpL3Protocol")
        icmp = ns.create("ns3::Icmpv4L4Protocol")
        udp = ns.create("ns3::UdpL4Protocol")
        node.connector("protos").connect(ipv4.connector("node"))
        node.connector("protos").connect(arp.connector("node"))
        node.connector("protos").connect(icmp.connector("node"))
        node.connector("protos").connect(udp.connector("node"))
        return node

    def add_ns_wifi_dev(self, ns, node, access_point = False):
        wifi = ns.create("ns3::WifiNetDevice")
        node.connector("devs").connect(wifi.connector("node"))

        phy = ns.create("ns3::YansWifiPhy")
        error = ns.create("ns3::NistErrorRateModel")
        manager = ns.create("ns3::ArfWifiManager")
        if access_point:
            mac = ns.create("ns3::ApWifiMac")
        else:
            mac = ns.create("ns3::StaWifiMac")

        phy.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
        mac.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
        phy.connector("err").connect(error.connector("phy"))
        wifi.connector("phy").connect(phy.connector("dev"))
        wifi.connector("mac").connect(mac.connector("dev"))
        wifi.connector("manager").connect(manager.connector("dev"))

        #phy.enable_trace("YansWifiPhyPcapTrace")
        return wifi, phy

    def add_ns_constant_mobility(self, ns, node, x, y, z):
        mobility = ns.create("ns3::ConstantPositionMobilityModel") 
        position = "%d:%d:%d" % (x, y, z)
        mobility.set_attribute_value("Position", position)
        node.connector("mobility").connect(mobility.connector("node"))
        return mobility

    def add_ns_wifi_channel(self, ns):
        channel = ns.create("ns3::YansWifiChannel")
        delay = ns.create("ns3::ConstantSpeedPropagationDelayModel")
        loss  = ns.create("ns3::LogDistancePropagationLossModel")
        channel.connector("delay").connect(delay.connector("chan"))
        channel.connector("loss").connect(loss.connector("prev"))
        return channel

    def make_ns_wifi(self, ns, pl, pl_ns_root, inet, numwifinodes, nextip): 
        base=struct.unpack('!L',socket.inet_aton(self.vnet))[0]
        error = False
        for i in xrange(2, 6):
            nr = int(math.pow(2, i))
            if nr <= (numwifinodes + 2):
                break
        else:
            error = True
        
        # how many IPs will we need?
        # 1 for the AP, 2 for each station and one for each extra PL node
        # BUT we need to also reserve IPs to sum up to a posible subnetwork
        # number of nodes: 2, 4, 8, 16, etc ...
        # And finally, we need 2 extra IPs for the PL-AP iface
       
        nrips = (1 + 2*numwifinodes + nr + 2)
        if nrips + nextip[0] > 255:
            error = True
        if error:
            raise RuntimeError("There are not enough IP addresses for the wireless network", )
        
        netprefix = 32 - i
        _nextwifiip = [254]
        def nextwifiip():
            ip = socket.inet_ntoa(struct.pack('!L',(base | _nextwifiip[0])))
            _nextwifiip[0] -= 1
            return ip

        _nextnstapip = [(254 - nr -1)]
        def nextnstapip():
            ip = socket.inet_ntoa(struct.pack('!L',(base | _nextnstapip[0])))
            _nextnstapip[0] -= 1
            return ip

        _nexttapip = [(254 - nr - 1 - numwifinodes)]
        def nexttapip():
            ip = socket.inet_ntoa(struct.pack('!L',(base | _nexttapip[0])))
            _nexttapip[0] -= 1
            return ip

        # WIFI network
        wifi_chan = self.add_ns_wifi_channel(ns)
        
        # AP node
        ap_node = self.add_ns_node(ns)
        self.add_ns_constant_mobility(ns, ap_node, 0, 0, 0)
        ap_wifi, ap_phy = self.add_ns_wifi_dev(ns, ap_node, access_point = True)
        ap_phy.connector("chan").connect(wifi_chan.connector("phys"))

        # connect AP to PL
        _nextplip = (254 - nrips)
        pl_ip = socket.inet_ntoa(struct.pack('!L',(base | _nextplip)))
        print "PL IP %s" % pl_ip
        _nextplip -= 1
        ns_ip = socket.inet_ntoa(struct.pack('!L',(base | _nextplip)))
        print "NS IP %s" % ns_ip
        self.add_pl_ns_connection(pl, pl_ns_root, pl_ip, ns, ap_node, ns_ip)

        # routes in and out ns
        self.add_route(ap_node, self.vnet, 24, pl_ip)
        net = 256 - nr
        ip = socket.inet_ntoa(struct.pack('!L',(base | net)))
        self.add_route(pl_ns_root, ip, netprefix, ns_ip)
        
        ap_ip = nextwifiip()
        print "AP IP %s" % ap_ip
        self.add_ip_address(ap_wifi, ap_ip, netprefix)
        
        r = 50
        # STA nodes
        for i in xrange(0, numwifinodes):
            stai = self.add_ns_node(ns)
            angi = (360/numwifinodes)*i
            xi = r*math.cos(angi)
            yi = r*math.sin(angi)
            self.add_ns_constant_mobility(ns, stai, xi, yi, 0)
            wifi, phy = self.add_ns_wifi_dev(ns, stai, access_point = False)
            phy.connector("chan").connect(wifi_chan.connector("phys"))
            
            wifi_ip = nextwifiip()
            print "WIFI IP %s" % wifi_ip
            self.add_ip_address(wifi, wifi_ip, netprefix)
            self.add_route(stai, self.vnet, 24, ap_ip)
            
            """
            pl_nodei, pl_ifacei = self.add_pl_ns_node(pl, inet, 
                    "node2%d_pl"%i)
           
            pl_addr = (self.base_addr%(net+1))
            ns3_addr = (self.base_addr%(net+2))
            self.add_pl_ns_tunchan_connection(pl_desc, pl_nodei, pl_addr,
                ns, stai, ns3_addr)
            self.add_route(pl_nodei, (self.base_addr%32), 27, ns3_addr)
            self.add_route(pl_nodei, (self.base_addr%0), 30, ns3_addr)
            self.add_route(pl_nodei, (self.base_addr%4), 30, ns3_addr)

            network = (self.base_addr%net)
            self.add_route(netns_node, network, 30, (self.base_addr%2))
            self.add_route(pl_node1, network, 30, (self.base_addr%6))
            self.add_route(ap_node, network, 30, wifi_addr)
            """

    def make_pl_overlay(self, numnodes, numwifinodes):
        print "make_pl_overlay ..."
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
                
        print "traverse..."
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
       
        ns_chosen = []

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
                if not ns_chosen and node.children:
                    ns_chosen.append(True)
                    label = "ns_root"
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
        
        print "maketree..."
        maketree(maketree, root)

        # create a netns node and connect it to the root pl node
        pl_root = exp.get_element_by_label("root")
        netns_source = self.make_netns_node(netns)
        iflabel = "source-iface"
        self.make_pl_netns_connection(pl, pl_root, netns, 
                netns_source, iflabel)
        self.add_vlc_source(netns, netns_source, iflabel)
 
        # add ns wireless network 
        pl_ns_root = exp.get_element_by_label("ns_root")
        pl_ns_root_iface = exp.get_element_by_label("ns_rootiface")
        ns = self.make_ns_in_pl(pl, exp, pl_ns_root, pl_ns_root_iface, "ns3")
        self.make_ns_wifi(ns, pl, pl_ns_root, inet, numwifinodes, nextip)

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
    parser.add_option("-u", "--user", dest="user", help="Valid linux system user (not root).", type="str", default=os.getlogin())
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
    exp.user = options.user
    try:
        exp.setUp()
        exp.make_pl_overlay(5, 2)
    finally:
        exp.tearDown()

