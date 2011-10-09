#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
import os
import os.path
import re
import sys
import shutil
import signal
import tempfile
import time
import struct
import socket
import operator
import ipaddr
import gzip
import random
import traceback
import math
import subprocess

sys.path.append(os.path.abspath("../../src"))

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP
from nepi.testbeds.planetlab import util as plutil
from optparse import OptionParser


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
    user = os.getlogin()
    
    port_base = 2000 + (os.getpid() % 1000) * 13
    
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        self.__class__.port_base = self.__class__.port_base + 100
        
        print "Using:"
        print "\tDISPLAY:", os.environ['DISPLAY']
        print "\tPLC:", self.plchost
        print "\tUsername:", self.pluser
        print "\tslice:", self.slicename

        api = plutil.getAPI(self.pluser, self.plpass, hostname=self.plchost)
        self.vnet = plutil.getVnet(api, self.slicename).split('/')[0].strip()

        print "\tvnet:", self.vnet

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
        
        plroot_dir = os.path.join(self.root_dir,"pl")
        if not os.path.exists(plroot_dir):
            os.makedirs(plroot_dir)

        exp_desc = ExperimentDescription()
        pl_provider = FactoriesProvider(testbed_id)
        pl_desc = exp_desc.add_testbed_description(pl_provider)
        pl_desc.set_attribute_value(DC.ROOT_DIRECTORY, plroot_dir )
        pl_desc.set_attribute_value("homeDirectory", self.root_dir)
        pl_desc.set_attribute_value("slice", slicename)
        pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
        pl_desc.set_attribute_value("authUser", pl_user)
        pl_desc.set_attribute_value("authPass", pl_pwd)
        pl_desc.set_attribute_value("plcHost", plchost)
        pl_desc.set_attribute_value("tapPortBase", self.port_base)
        pl_desc.set_attribute_value("p2pDeployment", not self.no_p2p_deploy)
        pl_desc.set_attribute_value("dedicatedSlice", True)
        pl_desc.set_attribute_value("plLogLevel", "INFO")
        
        return pl_desc, exp_desc
    
    def make_pl_tapnode(self, pl, ip, inet = None, label = None, hostname = None, routes = None, mcast = False, mcastrouter = False, types = None):
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
        if types is None:
            types = ["TapInterface"] * len(ips)
        tap1 = []
        tap1ip = []
        for i,(ip,devtype) in enumerate(zip(ips,types)):
            _tap1 = pl.create(devtype)
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
            if mcastrouter:
                fwd = pl.create("MulticastForwarder")
                fwd.enable_trace("stderr")
                fwd.connector("node").connect(node1.connector("apps"))
                mrt = pl.create("MulticastRouter")
                mrt.connector("fwd").connect(fwd.connector("router"))
                mrt.enable_trace("stderr")
            else:
                ann = pl.create("MulticastAnnouncer")
                ann.enable_trace("stderr")
                ann.connector("node").connect(node1.connector("apps"))
                
        return node1, iface1, tap1, tap1ip, inet
    
    def add_vlc_base(self, pl, node):
        app = pl.create("Application")
        app.set_attribute_value("rpmFusion", True)
        app.set_attribute_value("depends", "vlc")
        app.set_attribute_value("command", "sudo -S dbus-uuidgen --ensure ; vlc --version")
        app.enable_trace("stdout")
        app.enable_trace("stderr")
        node.connector("apps").connect(app.connector("node"))
        return app
    
    def add_vlc_restreamer(self, pl, node):
        hostname = node.get_attribute_value("hostname")
        app = self.add_vlc_base(pl, node)
        app.set_attribute_value("label","vlc_restreamer_%d" % (node.guid,))
        app.set_attribute_value("command",
            "sudo -S dbus-uuidgen --ensure ; "
            "while true ; do "
            "vlc -vvv -I dummy"
            " udp/ts://@239.255.12.42"
            " --sout '#std{access=http,mux=ts,dst=:8080}'"
            " ; sleep 5 ; done ")
        return app
    
    def add_vlc_dumper(self, pl, node, hostname=None, labelprefix = "vlc_dumper", precmd = "sleep 5 ; "):
        app = self.add_vlc_base(pl, node)
        mylabel = "%s_%d" % (labelprefix, node.guid,)
        if hostname is None:
            hostname = node.get_attribute_value("hostname")
        app.set_attribute_value("label",mylabel)
        app.set_attribute_value("command",
            precmd+
            "sudo -S dbus-uuidgen --ensure ; "
            "cat /dev/null > {#["+mylabel+"].trace[output].[name]#} ; "
            "while [[ $(stat -c '%s' {#["+mylabel+"].trace[output].[name]#}) == '0' ]] ; do "
            "vlc -vvv -I dummy"
            " http://"+hostname+":8080 vlc://quit"
            " --sout '#std{access=file,mux=ts,dst={#["+mylabel+"].trace[output].[name]#}}'"
            " ; sleep 5 ; done ")
        app.enable_trace("output")
        return app
    
    def add_vlc_source(self, pl, node, iflabels):
        app = self.add_vlc_base(pl, node)
        app.set_attribute_value("label","vlc_source_%d" % (node.guid,))
        app.set_attribute_value("sources", self.movie_source)
        app.set_attribute_value("command",
            "sudo -S dbus-uuidgen --ensure ; "
            "vlc -vvv -I dummy "
            +os.path.basename(self.movie_source)
            +" --sout '#duplicate{"
            +','.join([
                "dst=std{access=udp,dst=239.255.12.42,mux=ts,ttl=64,miface-addr={#[%s].addr[0].[Address]#}}" % (iflabel,)
                for iflabel in iflabels
            ])
            +"}'")
        return app
    
    def add_net_monitor(self, pl, node):
        app = pl.create("Application")
        app.set_attribute_value("label","network_monitor_%d" % (node.guid,))
        app.set_attribute_value("command", 
            r"""head -n 2 /proc/net/dev ; while true ; do cat /proc/net/dev | sed -r 's/.*/'"$(date -R)"': \0/' | grep eth0 ; sleep 1 ; done""")
        app.enable_trace("stdout")
        node.connector("apps").connect(app.connector("node"))
        return app
    
    def add_ip_address(self, iface, address, netprefix):
        ip = iface.add_address()
        ip.set_attribute_value("Address", address)
        ip.set_attribute_value("NetPrefix", netprefix)

    def add_route(self, node, destination, netprefix, nexthop):
        route = node.add_route()
        route.set_attribute_value("Destination", destination)
        route.set_attribute_value("NetPrefix", netprefix)
        route.set_attribute_value("NextHop", nexthop)

    def make_ns_in_pl(self, pl, exp, node1, iface1, root):
        ns3_testbed_id = "ns3"
        
        # Add NS3 support in node1
        plnepi = pl.create("NepiDependency")
        plns3 = pl.create("NS3Dependency")
        plnepi.connector("node").connect(node1.connector("deps"))
        plns3.connector("node").connect(node1.connector("deps"))

        # Create NS3 testbed running in node1
        ns3_provider = FactoriesProvider(ns3_testbed_id)
        ns_desc = exp.add_testbed_description(ns3_provider)
        ns_desc.set_attribute_value("rootDirectory", root)
        ns_desc.set_attribute_value("SimulatorImplementationType", "ns3::RealtimeSimulatorImpl")
        ns_desc.set_attribute_value("ChecksumEnabled", True)
        ns_desc.set_attribute_value(DC.DEPLOYMENT_HOST, "{#[%s].addr[0].[Address]#}" % (
            iface1.get_attribute_value("label"),))
        ns_desc.set_attribute_value(DC.DEPLOYMENT_USER, 
            pl.get_attribute_value("slice"))
        ns_desc.set_attribute_value(DC.DEPLOYMENT_KEY, 
            pl.get_attribute_value("sliceSSHKey"))
        ns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        ns_desc.set_attribute_value(DC.DEPLOYMENT_COMMUNICATION, DC.ACCESS_SSH)
        ns_desc.set_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP,
            "{#[%s].[%s]#}" % (
                node1.get_attribute_value("label"),
                ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP,))
        ns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        
        return ns_desc
   
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

    def add_ns_fdnd(self, ns_desc, node):
        fdnd = ns_desc.create("ns3::FdNetDevice")
        node.connector("devs").connect(fdnd.connector("node"))
        #fdnd.enable_trace("FdPcapTrace")
        return fdnd

    def add_ns_node(self, ns_desc):
        node = ns_desc.create("ns3::Node")
        ipv4 = ns_desc.create("ns3::Ipv4L3Protocol")
        arp  = ns_desc.create("ns3::ArpL3Protocol")
        icmp = ns_desc.create("ns3::Icmpv4L4Protocol")
        udp = ns_desc.create("ns3::UdpL4Protocol")
        node.connector("protos").connect(ipv4.connector("node"))
        node.connector("protos").connect(arp.connector("node"))
        node.connector("protos").connect(icmp.connector("node"))
        node.connector("protos").connect(udp.connector("node"))
        return node

    def add_ns_wifi_dev(self, ns_desc, node, access_point = False):
        wifi = ns_desc.create("ns3::WifiNetDevice")
        node.connector("devs").connect(wifi.connector("node"))

        phy = ns_desc.create("ns3::YansWifiPhy")
        error = ns_desc.create("ns3::NistErrorRateModel")
        manager = ns_desc.create("ns3::ArfWifiManager")
        if access_point:
            mac = ns_desc.create("ns3::ApWifiMac")
        else:
            mac = ns_desc.create("ns3::StaWifiMac")

        phy.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
        mac.set_attribute_value("Standard", "WIFI_PHY_STANDARD_80211a")
        phy.connector("err").connect(error.connector("phy"))
        wifi.connector("phy").connect(phy.connector("dev"))
        wifi.connector("mac").connect(mac.connector("dev"))
        wifi.connector("manager").connect(manager.connector("dev"))

        #phy.enable_trace("YansWifiPhyPcapTrace")
        return wifi, phy

    def add_ns_constant_mobility(self, ns_desc, node, x, y, z):
        mobility = ns_desc.create("ns3::ConstantPositionMobilityModel") 
        position = "%d:%d:%d" % (x, y, z)
        mobility.set_attribute_value("Position", position)
        node.connector("mobility").connect(mobility.connector("node"))
        return mobility

    def add_ns_wifi_channel(self, ns_desc):
        channel = ns_desc.create("ns3::YansWifiChannel")
        delay = ns_desc.create("ns3::ConstantSpeedPropagationDelayModel")
        loss  = ns_desc.create("ns3::LogDistancePropagationLossModel")
        channel.connector("delay").connect(delay.connector("chan"))
        channel.connector("loss").connect(loss.connector("prev"))
        return channel

    def make_netns_testbed(self, exp_desc):
        netns_provider = FactoriesProvider("netns")
        netns_desc = exp_desc.add_testbed_description(netns_provider)
        netns_desc.set_attribute_value("homeDirectory", self.root_dir)
        netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        netns_root_dir = os.path.join(self.root_dir, "netns")
        os.mkdir(netns_root_dir)
        netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
        netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
        netns_desc.set_attribute_value(DC.USE_SUDO, True)
        return netns_desc

    def add_netns_node(self, netns_desc, forwardX = True, label = None):
        node = netns_desc.create("Node")
        node.set_attribute_value("forward_X11", forwardX)
        if label:
            node.set_attribute_value("label", label)
        return node
    
    def add_netns_app(self, netns_desc, command, node):
        app = netns_desc.create("Application")
        app.set_attribute_value("command", command)
        app.set_attribute_value("user", self.user)
        app.connector("node").connect(node.connector("apps"))
        return app

    def add_pl_netns_connection(self, 
            pl_tap, 
            netns_desc, netns_node, netns_addr, netns_prefix = 30,
            taplabel = None):
        pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        pl_tap.set_attribute_value("multicast", True) 
        #pl_tap.enable_trace("pcap")
        #pl_tap.enable_trace("packets")
        pl_tapip = pl_tap.addresses[0].get_attribute_value("Address")
        netns_tap = netns_desc.create("TunNodeInterface")
        netns_tap.set_attribute_value("up", True)
        netns_tap.set_attribute_value("mtu", 1448)
        self.add_ip_address(netns_tap, netns_addr, netns_prefix)
        if taplabel:
            netns_tap.set_attribute_value("label", taplabel)
        netns_node.connector("devs").connect(netns_tap.connector("node"))
        netns_tunchannel = netns_desc.create("TunChannel")
        netns_tunchannel.set_attribute_value("tun_cipher", "PLAIN") 
        netns_tunchannel.connector("->fd").connect(netns_tap.connector("fd->"))
        pl_tap.connector("tcp").connect(netns_tunchannel.connector("tcp"))
        
        pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        pl_tap.set_attribute_value("pointopoint", netns_addr)

    def add_pl_ns_connection(self, pl_desc, pl_node, pl_addr,
            ns, ns_node, ns_addr, prefix = 30,
            fd = False, ptp = False):
        pl_tap = pl_desc.create("TapInterface")
        if fd:
            pl_tap.set_attribute_value("tun_cipher", "PLAIN") 
        self.add_ip_address(pl_tap, pl_addr, prefix)
        pl_node.connector("devs").connect(pl_tap.connector("node"))
        ns_fdnd = ns.create("ns3::FdNetDevice")
        ns_node.connector("devs").connect(ns_fdnd.connector("node"))
        self.add_ip_address(ns_fdnd, ns_addr, prefix)
        
        if fd:
            pl_tap.connector("fd->").connect(ns_fdnd.connector("->fd"))
        else:
            tunchannel = ns.create("ns3::Nepi::TunChannel")
            tunchannel.connector("fd->").connect(ns_fdnd.connector("->fd"))
            pl_tap.connector("udp").connect(tunchannel.connector("udp"))
        
        if ptp:
            pl_tap.set_attribute_value("pointopoint", ns_addr)

    def make_pl_overlay(self, numnodes):
        ns3_testbed_id = "ns3"
        
        pl, exp = self.make_experiment_desc()
        
        # We'll make a distribution spanning tree using prefix matching as a distance
        api = plutil.getAPI(self.pluser, self.plpass, hostname=self.plchost)
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
            print indent, '-', socket.inet_ntoa(struct.pack('!L',node.vif_addr)), '\t', node.country, node.city, node.site, '\t', node.hostname
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
        leaves = []

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
                
            # NS node, first leaf
            if not ns_chosen and not node.children:
                ns_chosen.append(True)
                label = "ns_root"
                
            ips = [ ipaddr.IPAddress(node.vif_addr+i) for i in xrange(1+len(node.children)) ]
            node1, iface1, tap1, tap1ip, _ = self.make_pl_tapnode(pl, ips, inet, 
                hostname = node.hostname,
                routes = routes,
                mcastrouter = bool(node.children),
                mcast = True,
                label = label,
                types = ( [ "TapInterface" ] * len(ips) if parent else [ "TunInterface" ] + [ "TapInterface" ] * (len(ips)-1) ) 
                )
            
            for tap, ctap in zip(tap1[1:], ctaps):
                tap.connector("udp").connect(ctap.connector("udp"))
            
            # Store leaves
            if not node.children:
                leaves.append((node, node1))
            
            self.add_net_monitor(pl, node1)
            self.add_vlc_dumper(pl, node1)
            self.add_vlc_restreamer(pl, node1)
            #if not parent:
            #    taplabels = [
            #        t.get_attribute_value("label")
            #        for t in tap1[1:]
            #    ]
            #    self.add_vlc_source(pl, node1, taplabels)
            
            return tap1[0]
        roottap = maketree(maketree, root)

        vnet_i = int(ipaddr.IPAddress(self.vnet))

        ## NS3 ##
        pl_ns_root = exp.get_element_by_label("ns_root")
        pl_ns_root_iface = exp.get_element_by_label("ns_rootiface")
        ns = self.make_ns_in_pl(pl, exp, pl_ns_root, pl_ns_root_iface, "ns3")
        wifi_chan = self.add_ns_wifi_channel(ns)

        # AP node
        ap_node = self.add_ns_node(ns)
        self.add_ns_constant_mobility(ns, ap_node, 0, 0, 0)
        ap_wifi, ap_phy = self.add_ns_wifi_dev(ns, ap_node, access_point = True)
        ap_phy.connector("chan").connect(wifi_chan.connector("phys"))

        # Net range free for WiFi
        wifi_net_prefix = 32-int(math.floor(math.log(256-nextip[0]&0xff) / math.log(2)))
        wifi_net = vnet_i | (256 - (1<<(32-wifi_net_prefix)))

        # connect AP to PL
        pl_addr = str(ipaddr.IPAddress(wifi_net | 1))
        ns_addr = str(ipaddr.IPAddress(wifi_net | 2))
        self.add_pl_ns_connection(
            pl, pl_ns_root, pl_addr, 
            ns, ap_node, ns_addr, 
            fd = True, ptp = True, prefix=30)

        
        # AP ip
        ap_addr = str(ipaddr.IPAddress(vnet_i | 254))
        ap_addr_prefix = 32-int(math.ceil(math.log(self.nsta+3) / math.log(2)))
        self.add_ip_address(ap_wifi, ap_addr, ap_addr_prefix)
        
        # route for PL->wifi
        self.add_route(pl_ns_root, 
            str(ipaddr.IPAddress(wifi_net)), wifi_net_prefix,
            ns_addr)
        
        print "NS-3 AP\t%s/%s <--> PL AP %s" % (ns_addr, 30, pl_addr)
        print " | (|) %s/%s" % (ap_addr, ap_addr_prefix)
        print " |"
        print " |                  R %s/%d --> %s" % (str(ipaddr.IPAddress(wifi_net)), wifi_net_prefix, ns_addr)
       
        nextpip = (vnet_i | 255) >> (32-ap_addr_prefix) << (32-ap_addr_prefix)
        nextdip = vnet_i | 253
        ap_net = nextpip - (1<<(32-ap_addr_prefix))
        r = 50
        # STA nodes
        for i in xrange(self.nsta):
            stai = self.add_ns_node(ns)
            angi = (360/self.nsta)*i
            xi = r*math.cos(angi)
            yi = r*math.sin(angi)
            self.add_ns_constant_mobility(ns, stai, xi, yi, 0)
            wifi, phy = self.add_ns_wifi_dev(ns, stai, access_point = False)
            phy.connector("chan").connect(wifi_chan.connector("phys"))
            
            wifi_addr = str(ipaddr.IPAddress(vnet_i | nextdip))
            nextdip -= 1

            nextpip -= 4
            while nextpip & 3:
                nextpip -= 1
            plns_net_i = nextpip
            plns_net = str(ipaddr.IPAddress(plns_net_i))
            pl_addr2 = str(ipaddr.IPAddress(plns_net_i | 1))
            ns_addr2 = str(ipaddr.IPAddress(plns_net_i | 2))

            # route from AP (after others)
            print " | R %s/%s -> %s" % ( plns_net,30,ns_addr2 )
            self.add_route(ap_node, plns_net, 30, wifi_addr)

            print " +---\t(|) %16s/%s" % (wifi_addr,ap_addr_prefix)
            print " |         %16s (ns3) <---> (pl) %16s/30" % (ns_addr2, pl_addr2)
            print " |\t       \t\t                 <--  R %s/24" % (self.vnet, )
            print " |\t       \t R %s/30 -> %s" % (plns_net, pl_addr2)
            print " |\t       \t R %s <-- %s/24" % (ap_addr, plns_net)

            self.add_ip_address(wifi, wifi_addr, ap_addr_prefix)
            self.add_route(stai, plns_net, 30, pl_addr2)
            self.add_route(stai, self.vnet, 24, ap_addr)
            
            pl_nodei, _, pl_ifacei, _, _ = self.make_pl_tapnode(pl, [], inet, 
                routes = [(self.vnet, 24, ns_addr2)],
                mcast = False,
                label = "ns_plnode_%d" % (i+1,)
                )
 
            self.add_pl_ns_connection(
                pl, pl_nodei, pl_addr2,
                ns, stai, ns_addr2,
                prefix = 30)
            
            self.add_vlc_dumper(pl, pl_nodei,
                hostname = pl_addr,
                labelprefix = "vlc_dumper_ns",
                precmd = "sleep 15 ; ")

            # Validate (post-fact to let the user see the diagram above)
            if nextpip < wifi_net:
                raise RuntimeError, "Not enough IPs for wifi section"
        
        # route back to PL (after others)
        print " | R %s/%s -> %s" % ( self.vnet,24,pl_addr )
        self.add_route(ap_node, self.vnet, 24, pl_addr)


        ## NETNS ##
        netns_addr = str(ipaddr.IPAddress(vnet_i | 1))

        root1 = exp.get_element_by_label("root")
        netns = self.make_netns_testbed(exp)
        netns_node = self.add_netns_node(netns)
        netns_term = self.add_netns_app(netns, "xterm", netns_node)
        if self.movie_source:
            cmd = (
                "vlc -I dummy "
                +os.path.abspath(self.movie_source)
                +" --sout '#std{access=udp{ttl=64,miface-addr="+netns_addr+"},dst=239.255.12.42,mux=ts}'"
            )
        else:
            cmd = self.movie_command % {
                "dst" : "std{access=udp{ttl=64,miface-addr="+netns_addr+"},dst=239.255.12.42,mux=ts}"
            }
        netns_vlc  = self.add_netns_app(netns, cmd, netns_node)
        
        # connection PL1/NETNS
        self.add_pl_netns_connection(
            roottap,
            netns, netns_node, netns_addr,
            24,
            taplabel="netns_source")
        self.add_route(netns_node, 
            "0.0.0.0", 0, 
            str(ipaddr.IPAddress(root.vif_addr)) )
        
        # pick random hostname to stream from
        interactive_source_host = random.sample(leaves,1)[0][0].hostname

        xml = exp.to_xml()
        test_dir = "./results"
        #sys.exit(1)

        try:
            controller = ExperimentController(xml, self.root_dir)
            controller.start()
            
            # launch vlc client to monitor activity
            time.sleep(5)
            proc = subprocess.Popen([
                "vlc", "-I", "dummy", "http://%s:8080" % (interactive_source_host,)])
            
            print >>sys.stderr, "Close xterm to shut down or Ctrl+C"
            try:
                while not controller.is_finished(netns_term.guid):
                    time.sleep(5)
            except KeyboardInterrupt:
                # ping netns
                try:
                    controller.traces_info()
                except:
                    pass
                try:
                    controller.traces_info()
                except:
                    pass
            
            # kill streamer
            os.kill(proc.pid, signal.SIGTERM)
            
            # download results
            traces_info = controller.traces_info()
            for progress, (testbed_guid, guids) in enumerate(traces_info.iteritems()):
                for subprogress, (guid, traces) in enumerate(guids.iteritems()):
                    for name, data in traces.iteritems():
                        path = data["filepath"]
                        elem = exp.get_element(guid)
                        if elem is not None:
                            label = elem.get_attribute_value("label")
                            if label is not None:
                                path = "%s-%s" % (label,path)
                        
                        if not path:
                            continue
                        
                        print >>sys.stderr, ("%.2f%% Downloading trace" % (progress + (subprogress * 1.0 / len(guids)) * 100.0 / len(traces_info))), path
                        
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
                traceback.print_exc()
            try:
                controller.shutdown()
            except:
                traceback.print_exc()


if __name__ == '__main__':
    usage = "usage: %prog -m movie -u user"
    parser = OptionParser(usage=usage)
    parser.add_option("-u", "--user", dest="user", help="Valid linux system user (not root).", type="str")
    parser.add_option("-U", "--pluser", dest="pluser", help="PlanetLab PLC username", type="str")
    parser.add_option("-m", "--movie", dest="movie", help="Path to movie file to play", type="str")
    parser.add_option("-n", "--nsta", dest="nsta", default=3, help="Number of wifi stations attached to the overlay", type="int")
    parser.add_option("-N", "--nodes", dest="nodes", default=5, help="Number of overlay nodes", type="int")
    parser.add_option("-s", "--slicename", dest="slicename", help="PlanetLab slice", type="str")
    parser.add_option("-H", "--plchost", dest="plchost", help="PlanetLab's PLC hostname", type="str")
    parser.add_option("-k", "--plkey", dest="plkey", help="Slice SSH key", type="str")
    parser.add_option("-P", "--no-p2p", dest="nop2p", help="Disable peer-to-peer deployment. Not recommended for first deployment.", 
        action="store_true", default=False)
    (options, args) = parser.parse_args()
    if options.user == 'root':
        parser.error("Missing or invalid 'user' option.")

    exp = PlanetLabMulticastOverlay()
    if not options.movie or options.movie.startswith("/dev/"):
        # use camera
        if not options.movie:
            options.movie = "/dev/video0"
        exp.movie_source = None
        exp.movie_command = (
            "vlc -I dummy -vvv --color "
            "v4l:///dev/video0:size=320x240:channel=0:adev=/dev/dsp:audio=0 "
            "--sout '#transcode{vcodec=mpeg4,acodec=aac,vb=100,ab=16,venc=ffmpeg{keyint=80,hq=rd},deinterlace}:"
            "%(dst)s'"
        )
    else:
        exp.movie_source = options.movie
    exp.no_p2p_deploy = options.nop2p
    exp.nsta = options.nsta
    if options.user:
        exp.user = options.user
    if options.plchost:
        exp.plchost = options.plchost
    if options.slicename:
        exp.slicename = options.slicename
    if options.plkey:
        exp.plkey = options.plkey
    if options.pluser:
        exp.pluser = options.pluser
    if not exp.plpass:
        exp.plpass = getpass.getpass("Password for %s: " % (exp.pluser,))
    
    # Fix some distro's environment to work well with netns
    if re.match(r"[^:]*:\d+$", os.environ['DISPLAY']):
        os.environ['DISPLAY'] += '.0'
    if not os.environ.get('XAUTHORITY'):
        os.environ['XAUTHORITY'] = os.path.join(os.environ['HOME'], '.Xauthority')
    
    try:
        exp.setUp()
        exp.make_pl_overlay(options.nodes)
    finally:
        exp.tearDown()

