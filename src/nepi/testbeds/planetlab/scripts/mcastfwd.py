import sys

import signal
import socket
import struct
import optparse
import threading
import subprocess
import re
import time
import collections
import os
import traceback
import logging

import ipaddr2

usage = "usage: %prog [options] <enabled-addresses>"

parser = optparse.OptionParser(usage=usage)

parser.add_option(
    "-d", "--poll-delay", dest="poll_delay", metavar="SECONDS", type="float",
    default = 1.0,
    help = "Multicast subscription polling interval")
parser.add_option(
    "-D", "--refresh-delay", dest="refresh_delay", metavar="SECONDS", type="float",
    default = 30.0,
    help = "Full-refresh interval - time between full IGMP reports")
parser.add_option(
    "-p", "--fwd-path", dest="fwd_path", metavar="PATH", 
    default = "/var/run/mcastfwd",
    help = "Path of the unix socket in which the program will listen for packets")
parser.add_option(
    "-r", "--router-path", dest="mrt_path", metavar="PATH", 
    default = "/var/run/mcastrt",
    help = "Path of the unix socket in which the program will listen for routing changes")
parser.add_option(
    "-A", "--announce-only", dest="announce_only", action="store_true",
    default = False,
    help = "If given, only group membership announcements will be made. "
           "Useful for non-router non-member multicast nodes.")
parser.add_option(
    "-R", "--no-router", dest="no_router", action="store_true",
    default = False,
    help = "If given, only group membership announcements and forwarding to the default multicast egress will be made. "
           "Useful for non-router but member multicast nodes.")
parser.add_option(
    "-v", "--verbose", dest="verbose", action="store_true",
    default = False,
    help = "Log more verbosely")

(options, remaining_args) = parser.parse_args(sys.argv[1:])

logging.basicConfig(
    stream=sys.stderr, 
    level=logging.DEBUG if options.verbose else logging.WARNING)

ETH_P_ALL = 0x00000003
ETH_P_IP = 0x00000800
TUNSETIFF = 0x400454ca
IFF_NO_PI = 0x00001000
IFF_TAP = 0x00000002
IFF_TUN = 0x00000001
IFF_VNET_HDR = 0x00004000
TUN_PKT_STRIP = 0x00000001
IFHWADDRLEN = 0x00000006
IFNAMSIZ = 0x00000010
IFREQ_SZ = 0x00000028
FIONREAD = 0x0000541b

class IGMPThread(threading.Thread):
    def __init__(self, vif_addr, *p, **kw):
        super(IGMPThread, self).__init__(*p, **kw)
        
        vif_addr = vif_addr.strip()
        self.vif_addr = vif_addr
        self.igmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IGMP)
        self.igmp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
            socket.inet_aton(self.vif_addr) )
        self.igmp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self.igmp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self._stop = False
        self.setDaemon(True)
        
        # Find tun name
        proc = subprocess.Popen(['ip','addr','show'],
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            stdin = open('/dev/null','r+b') )
        tun_name = None
        heading = re.compile(r"\d+:\s*([-a-zA-Z0-9_]+):.*")
        addr = re.compile(r"\s*inet\s*(\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}).*")
        for line in proc.stdout:
            match = heading.match(line)
            if match:
                tun_name = match.group(1)
            else:
                match = addr.match(line)
                if match and match.group(1) == vif_addr:
                    self.tun_name = tun_name
                    break
        else:
            raise RuntimeError, "Could not find iterface for", vif_addr
    
    def run(self):
        devnull = open('/dev/null','r+b')
        maddr_re = re.compile(r"\s*inet\s*(\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3})\s*")
        cur_maddr = set()
        lastfullrefresh = time.time()
        while not self._stop:
            # Get current subscriptions @ vif
            proc = subprocess.Popen(['ip','maddr','show',self.tun_name],
                stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT,
                stdin = devnull)
            new_maddr = set()
            for line in proc.stdout:
                match = maddr_re.match(line)
                if match:
                    new_maddr.add(match.group(1))
            proc.wait()
            
            # Get current subscriptions @ eth0 (default on PL),
            # they should be considered "universal" suscriptions.
            proc = subprocess.Popen(['ip','maddr','show', 'eth0'],
                stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT,
                stdin = devnull)
            new_maddr = set()
            for line in proc.stdout:
                match = maddr_re.match(line)
                if match:
                    new_maddr.add(match.group(1))
            proc.wait()
            
            # Every now and then, send a full report
            now = time.time()
            report_new = new_maddr
            if (now - lastfullrefresh) <= options.refresh_delay:
                report_new = report_new - cur_maddr
            else:
                lastfullrefresh = now
            
            # Report subscriptions
            for grp in report_new:
                print >>sys.stderr, "JOINING", grp
                igmpp = ipaddr2.ipigmp(
                    self.vif_addr, grp, 1, 0x16, 0, grp, 
                    noipcksum=True)
                try:
                    self.igmp_socket.sendto(igmpp, 0, (grp,0))
                except:
                    traceback.print_exc(file=sys.stderr)

            # Notify group leave
            for grp in cur_maddr - new_maddr:
                print >>sys.stderr, "LEAVING", grp
                igmpp = ipaddr2.ipigmp(
                    self.vif_addr, '224.0.0.2', 1, 0x17, 0, grp, 
                    noipcksum=True)
                try:
                    self.igmp_socket.sendto(igmpp, 0, ('224.0.0.2',0))
                except:
                    traceback.print_exc(file=sys.stderr)

            cur_maddr = new_maddr
            
            time.sleep(options.poll_delay)
    
    def stop(self):
        self._stop = True
        self.join(1+5*options.poll_delay)


class FWDThread(threading.Thread):
    def __init__(self, rt_cache, router_socket, vifs, *p, **kw):
        super(FWDThread, self).__init__(*p, **kw)
        
        self.in_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.in_socket.bind(options.fwd_path)
        
        self.pending = collections.deque()
        self.maxpending = 1000
        self.rt_cache = rt_cache
        self.router_socket = router_socket
        self.vifs = vifs
        
        # prepare forwarding sockets 
        self.fwd_sockets = {}
        for fwd_target in remaining_args:
            fwd_target = socket.inet_aton(fwd_target)
            fwd_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            fwd_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            fwd_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, fwd_target)
            fwd_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            self.fwd_sockets[fwd_target] = fwd_socket
        
        # we always forward to eth0
        # In PL, we cannot join the multicast routers in eth0,
        # that would bring a lot of trouble. But we can
        # listen there for subscriptions and forward interesting
        # packets, partially joining the mbone
        # TODO: IGMP messages from eth0 should be selectively
        #       replicated in all vifs to propagate external
        #       subscriptions. It is complex though.
        fwd_target = '\x00'*4
        fwd_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        fwd_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        fwd_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, fwd_target)
        fwd_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self.fwd_sockets[fwd_target] = fwd_socket
        
        self._stop = False
        self.setDaemon(True)
    
    def run(self):
        in_socket = self.in_socket
        rt_cache = self.rt_cache
        vifs = self.vifs
        router_socket = self.router_socket
        len_ = len
        ord_ = ord
        str_ = str
        pending = self.pending
        in_socket.settimeout(options.poll_delay)
        buffer_ = buffer
        enumerate_ = enumerate
        fwd_sockets = self.fwd_sockets
        npending = 0
        noent = (None,None)
        def_socket = fwd_sockets['\x00\x00\x00\x00']
        
        while not self._stop:
            # Get packet
            try:
                if pending and npending:
                    packet = pending.pop()
                    npending -= 1
                else:
                    packet = in_socket.recv(2000)
            except socket.timeout, e:
                if pending and not npending:
                    npending = len_(pending)
                continue
            if not packet or len_(packet) < 24:
                continue
            
            fullpacket = packet
            parent = packet[:4]
            packet = buffer_(packet,4)
            
            if packet[9] == '\x02':
                # IGMP packet? It's for mrouted
                if router_socket:
                    router_socket.send(packet)
            elif packet[9] == '\x00':
                # LOOPING packet, discard
                continue
            
            # To-Do: PIM asserts
            
            # Get route
            addrinfo = packet[12:20]
            fwd_targets, rparent = rt_cache.get(addrinfo, noent)
            
            if fwd_targets is not None and (rparent == '\x00\x00\x00\x00' or rparent == parent):
                # Forward to vifs
                ttl = ord_(packet[8])
                tgt_group = (socket.inet_ntoa(addrinfo[4:]),0)
                print >>sys.stderr, map(socket.inet_ntoa, (parent, addrinfo[:4], addrinfo[4:])), "-> ttl", ttl,
                nfwd_targets = len_(fwd_targets)
                for vifi, vif in vifs.iteritems():
                    if vifi < nfwd_targets:
                        ttl_thresh = ord_(fwd_targets[vifi])
                        if ttl_thresh > 0 and ttl > ttl_thresh:
                            if vif[4] in fwd_sockets:
                                try:
                                    print >>sys.stderr, socket.inet_ntoa(vif[4]),
                                    fwd_socket = fwd_sockets[vif[4]]
                                    fwd_socket.sendto(packet, 0, tgt_group)
                                except:
                                    pass
                
                # Forward to eth0
                try:
                    print >>sys.stderr, 'default',
                    def_socket.sendto(packet, 0, tgt_group)
                except:
                    pass
                
                print >>sys.stderr, "."
            elif router_socket:
                # Mark pending
                if len_(pending) < self.maxpending:
                    tgt_group = addrinfo[4:]
                    print >>sys.stderr, map(socket.inet_ntoa, (parent, addrinfo[:4], addrinfo[4:])), "-> ?"
                    
                    pending.append(fullpacket)
                    
                    # Notify mrouted by forwarding it with protocol 0
                    router_socket.send(''.join(
                        (packet[:9],'\x00',packet[10:]) ))
            else:
                # Forward to eth0
                ttl = ord_(packet[8])
                tgt_group = (socket.inet_ntoa(addrinfo[4:]),0)
                
                try:
                    print >>sys.stderr, map(socket.inet_ntoa, (parent, addrinfo[:4], addrinfo[4:])), "-> ttl", ttl, 'default'
                    def_socket.sendto(packet, 0, tgt_group)
                except:
                    pass
    
    def stop(self):
        self._stop = True
        self.join(1+5*options.poll_delay)


class RouterThread(threading.Thread):
    def __init__(self, rt_cache, router_socket, vifs, *p, **kw):
        super(RouterThread, self).__init__(*p, **kw)
        
        self.rt_cache = rt_cache
        self.vifs = vifs
        self.router_socket = router_socket

        self._stop = False
        self.setDaemon(True)
    
    def run(self):
        rt_cache = self.rt_cache
        vifs = self.vifs
        addr_vifs = {}
        router_socket = self.router_socket
        router_socket.settimeout(options.poll_delay)
        len_ = len
        buffer_ = buffer
        
        buf = ""
        
        MRT_BASE	= 200
        MRT_ADD_VIF	= MRT_BASE+2	# Add a virtual interface		
        MRT_DEL_VIF	= MRT_BASE+3	# Delete a virtual interface		
        MRT_ADD_MFC	= MRT_BASE+4	# Add a multicast forwarding entry	
        MRT_DEL_MFC = MRT_BASE+5	# Delete a multicast forwarding entry	
        
        def cmdhdr(cmd, unpack=struct.unpack, buffer=buffer):
            op,dlen = unpack('II', buffer(cmd,0,8))
            cmd = buffer(cmd,8)
            return op,dlen,cmd
        def vifctl(data, unpack=struct.unpack):
            #vifi, flags,threshold,rate_limit,lcl_addr,rmt_addr = unpack('HBBI4s4s', data)
            return unpack('HBBI4s4s', data)
        def mfcctl(data, unpack=struct.unpack):
            #origin,mcastgrp,parent,ttls,pkt_cnt,byte_cnt,wrong_if,expire = unpack('4s4sH10sIIIi', data)
            return unpack('4s4sH32sIIIi', data)
        
        
        def add_vif(cmd):
            vifi = vifctl(cmd)
            vifs[vifi[0]] = vifi
            addr_vifs[vifi[4]] = vifi[0]
            print >>sys.stderr, "Added VIF", vifi
        def del_vif(cmd):
            vifi = vifctl(cmd)
            vifi = vifs[vifi[0]]
            del addr_vifs[vifi[4]]
            del vifs[vifi[0]]
            print >>sys.stderr, "Removed VIF", vifi
        def add_mfc(cmd):
            origin,mcastgrp,parent,ttls,pkt_cnt,byte_cnt,wrong_if,expire = mfcctl(data)
            if parent in vifs:
                parent_addr = vifs[parent][4]
            else:
                parent_addr = '\x00\x00\x00\x00'
            addrinfo = origin + mcastgrp
            rt_cache[addrinfo] = (ttls, parent_addr)
            print >>sys.stderr, "Added RT", '-'.join(map(socket.inet_ntoa,(parent_addr,origin,mcastgrp))), map(ord,ttls)
        def del_mfc(cmd):
            origin,mcastgrp,parent,ttls,pkt_cnt,byte_cnt,wrong_if,expire = mfcctl(data)
            if parent in vifs:
                parent_addr = vifs[parent][4]
            else:
                parent_addr = '\x00\x00\x00\x00'
            addrinfo = origin + mcastgrp
            del rt_cache[addrinfo]
            print >>sys.stderr, "Removed RT", '-'.join(map(socket.inet_ntoa,(parent_addr,origin,mcastgrp)))
        
        commands = {
            MRT_ADD_VIF : add_vif,
            MRT_DEL_VIF : del_vif,
            MRT_ADD_MFC : add_mfc,
            MRT_DEL_MFC : del_mfc,
        }

        while not self._stop:
            if len_(buf) < 8 or len_(buf) < (cmdhdr(buf)[1]+8):
                # Get cmd
                try:
                    cmd = router_socket.recv(2000)
                except socket.timeout, e:
                    continue
                if not cmd:
                    print >>sys.stderr, "PLRT CONNECTION BROKEN"
                    TERMINATE.append(None)
                    break
            
            if buf:
                buf += cmd
                cmd = buf
            
            if len_(cmd) < 8:
                continue
            
            op,dlen,data = cmdhdr(cmd)
            if len_(data) < dlen:
                continue
            
            buf = buffer_(data, dlen)
            data = buffer_(data, 0, dlen)
            
            print >>sys.stderr, "COMMAND", op, "DATA", dlen
            
            if op in commands:
                try:
                    commands[op](data)
                except:
                    traceback.print_exc(file=sys.stderr)
            else:
                print >>sys.stderr, "IGNORING UNKNOWN COMMAND", op
    
    def stop(self):
        self._stop = True
        self.join(1+5*options.poll_delay)



igmp_threads = []
for vif_addr in remaining_args:
    igmp_threads.append(IGMPThread(vif_addr))

rt_cache = {}
vifs = {}

TERMINATE = []
TERMINATE = []
def _finalize(sig,frame):
    global TERMINATE
    TERMINATE.append(None)
signal.signal(signal.SIGTERM, _finalize)


try:
    if not options.announce_only and not options.no_router:
        router_socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        router_socket.bind(options.mrt_path)
        router_socket.listen(0)
        router_remote_socket, router_remote_addr = router_socket.accept()
        router_thread = RouterThread(rt_cache, router_remote_socket, vifs)
    else:
        router_remote_socket = None
        router_thread = None

    if not options.announce_only:
        fwd_thread = FWDThread(rt_cache, router_remote_socket, vifs)

    for thread in igmp_threads:
        thread.start()
    
    if not options.announce_only:
        fwd_thread.start()
    if not options.no_router and not options.announce_only:
        router_thread.start()

    while not TERMINATE:
        time.sleep(30)
finally:
    if os.path.exists(options.mrt_path):
        try:
            os.remove(options.mrt_path)
        except:
            pass
    if os.path.exists(options.fwd_path):
        try:
            os.remove(options.fwd_path)    
        except:
            pass


