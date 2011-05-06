#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import nepi.util.ipaddr2 as ipaddr2
import nepi.util.server as server
import plcapi
import subprocess
import os
import os.path
import random

import tunproto

class NodeIface(object):
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        
        # Attributes
        self.primary = True

        # These get initialized at configuration time
        self.address = None
        self.lladdr = None
        self.netprefix = None
        self.netmask = None
        self.broadcast = True
        self._interface_id = None

        # These get initialized when the iface is connected to its node
        self.node = None

        # These get initialized when the iface is connected to the internet
        self.has_internet = False

    def __str__(self):
        return "%s<ip:%s/%s up mac:%s>" % (
            self.__class__.__name__,
            self.address, self.netmask,
            self.lladdr,
        )

    def add_address(self, address, netprefix, broadcast):
        raise RuntimeError, "Cannot add explicit addresses to public interface"
    
    def pick_iface(self, siblings):
        """
        Picks an interface using the PLCAPI to query information about the node.
        
        Needs an assigned node.
        
        Params:
            siblings: other NodeIface elements attached to the same node
        """
        
        if self.node is None or self.node._node_id is None:
            raise RuntimeError, "Cannot pick interface without an assigned node"
        
        avail = self._api.GetInterfaces(
            node_id=self.node._node_id, 
            is_primary=self.primary,
            fields=('interface_id','mac','netmask','ip') )
        
        used = set([sibling._interface_id for sibling in siblings
                    if sibling._interface_id is not None])
        
        for candidate in avail:
            candidate_id = candidate['interface_id']
            if candidate_id not in used:
                # pick it!
                self._interface_id = candidate_id
                self.address = candidate['ip']
                self.lladdr = candidate['mac']
                self.netprefix = candidate['netmask']
                self.netmask = ipaddr2.ipv4_dot2mask(self.netprefix) if self.netprefix else None
                return
        else:
            raise RuntimeError, "Cannot configure interface: cannot find suitable interface in PlanetLab node"

    def validate(self):
        if not self.has_internet:
            raise RuntimeError, "All external interface devices must be connected to the Internet"
    

class _CrossIface(object):
    def __init__(self, proto, addr, port):
        self.tun_proto = proto
        self.tun_addr = addr
        self.tun_port = port

class TunIface(object):
    _PROTO_MAP = tunproto.TUN_PROTO_MAP
    _KIND = 'TUN'

    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        
        # Attributes
        self.address = None
        self.netprefix = None
        self.netmask = None
        
        self.up = None
        self.device_name = None
        self.mtu = None
        self.snat = False
        self.txqueuelen = None
        
        # Enabled traces
        self.capture = False

        # These get initialized when the iface is connected to its node
        self.node = None
        
        # These get initialized when the iface is configured
        self.external_iface = None
        
        # These get initialized when the iface is configured
        # They're part of the TUN standard attribute set
        self.tun_port = None
        self.tun_addr = None
        
        # These get initialized when the iface is connected to its peer
        self.peer_iface = None
        self.peer_proto = None
        self.peer_proto_impl = None

        # same as peer proto, but for execute-time standard attribute lookups
        self.tun_proto = None 
        
        
        # Generate an initial random cryptographic key to use for tunnelling
        # Upon connection, both endpoints will agree on a common one based on
        # this one.
        self.tun_key = ( ''.join(map(chr, [ 
                    r.getrandbits(8) 
                    for i in xrange(32) 
                    for r in (random.SystemRandom(),) ])
                ).encode("base64").strip() )        
        

    def __str__(self):
        return "%s<ip:%s/%s %s%s>" % (
            self.__class__.__name__,
            self.address, self.netprefix,
            " up" if self.up else " down",
            " snat" if self.snat else "",
        )

    def add_address(self, address, netprefix, broadcast):
        if (self.address or self.netprefix or self.netmask) is not None:
            raise RuntimeError, "Cannot add more than one address to %s interfaces" % (self._KIND,)
        if broadcast:
            raise ValueError, "%s interfaces cannot broadcast in PlanetLab" % (self._KIND,)
        
        self.address = address
        self.netprefix = netprefix
        self.netmask = ipaddr2.ipv4_mask2dot(netprefix)
    
    def validate(self):
        if not self.node:
            raise RuntimeError, "Unconnected %s iface - missing node" % (self._KIND,)
        if self.peer_iface and self.peer_proto not in self._PROTO_MAP:
            raise RuntimeError, "Unsupported tunnelling protocol: %s" % (self.peer_proto,)
        if not self.address or not self.netprefix or not self.netmask:
            raise RuntimeError, "Misconfigured %s iface - missing address" % (self._KIND,)
    
    def _impl_instance(self, home_path, listening):
        impl = self._PROTO_MAP[self.peer_proto](
            self, self.peer_iface, home_path, self.tun_key, listening)
        impl.port = self.tun_port
        return impl
    
    def prepare(self, home_path, listening):
        if not self.peer_iface and (self.peer_proto and (listening or (self.peer_addr and self.peer_port))):
            # Ad-hoc peer_iface
            self.peer_iface = _CrossIface(
                self.peer_proto,
                self.peer_addr,
                self.peer_port)
        if self.peer_iface:
            if not self.peer_proto_impl:
                self.peer_proto_impl = self._impl_instance(home_path, listening)
            self.peer_proto_impl.prepare()
    
    def setup(self):
        if self.peer_proto_impl:
            self.peer_proto_impl.setup()
    
    def cleanup(self):
        if self.peer_proto_impl:
            self.peer_proto_impl.shutdown()
            self.peer_proto_impl = None

    def sync_trace(self, local_dir, whichtrace):
        if self.peer_proto_impl:
            return self.peer_proto_impl.sync_trace(local_dir, whichtrace)
        else:
            return None

class TapIface(TunIface):
    _PROTO_MAP = tunproto.TAP_PROTO_MAP
    _KIND = 'TAP'

# Yep, it does nothing - yet
class Internet(object):
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api

class NetPipe(object):
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api

        # Attributes
        self.mode = None
        self.addrList = None
        self.portList = None
        
        self.plrIn = None
        self.bwIn = None
        self.delayIn = None

        self.plrOut = None
        self.bwOut = None
        self.delayOut = None
        
        # These get initialized when the pipe is connected to its node
        self.node = None
        self.configured = False
    
    def validate(self):
        if not self.mode:
            raise RuntimeError, "Undefined NetPipe mode"
        if not self.portList:
            raise RuntimeError, "Undefined NetPipe port list - must always define the scope"
        if not (self.plrIn or self.bwIn or self.delayIn):
            raise RuntimeError, "Undefined NetPipe inbound characteristics"
        if not (self.plrOut or self.bwOut or self.delayOut):
            raise RuntimeError, "Undefined NetPipe outbound characteristics"
        if not self.node:
            raise RuntimeError, "Unconnected NetPipe"
    
    def _add_pipedef(self, bw, plr, delay, options):
        if delay:
            options.extend(("delay","%dms" % (delay,)))
        if bw:
            options.extend(("bw","%.8fMbit/s" % (bw,)))
        if plr:
            options.extend(("plr","%.8f" % (plr,)))
    
    def _get_ruledef(self):
        scope = "%s%s%s" % (
            self.portList,
            "@" if self.addrList else "",
            self.addrList or "",
        )
        
        options = []
        if self.bwIn or self.plrIn or self.delayIn:
            options.append("IN")
            self._add_pipedef(self.bwIn, self.plrIn, self.delayIn, options)
        if self.bwOut or self.plrOut or self.delayOut:
            options.append("OUT")
            self._add_pipedef(self.bwOut, self.plrOut, self.delayOut, options)
        options = ' '.join(options)
        
        return (scope,options)

    def configure(self):
        # set up rule
        scope, options = self._get_ruledef()
        command = "sudo -S netconfig config %s %s %s" % (self.mode, scope, options)
        
        (out,err),proc = server.popen_ssh_command(
            command,
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
            )
    
        if proc.wait():
            raise RuntimeError, "Failed instal build sources: %s %s" % (out,err,)
        
        # we have to clean up afterwards
        self.configured = True
    
    def refresh(self):
        if self.configured:
            # refresh rule
            scope, options = self._get_ruledef()
            command = "sudo -S netconfig refresh %s %s %s" % (self.mode, scope, options)
            
            (out,err),proc = server.popen_ssh_command(
                command,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed instal build sources: %s %s" % (out,err,)
    
    def cleanup(self):
        if self.configured:
            # remove rule
            scope, options = self._get_ruledef()
            command = "sudo -S netconfig delete %s %s" % (self.mode, scope)
            
            (out,err),proc = server.popen_ssh_command(
                command,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed instal build sources: %s %s" % (out,err,)
            
            self.configured = False
    
    def sync_trace(self, local_dir, whichtrace):
        if whichtrace != 'netpipeStats':
            raise ValueError, "Unsupported trace %s" % (whichtrace,)
        
        local_path = os.path.join(local_dir, "netpipe_stats_%s" % (self.mode,))
        
        # create parent local folders
        proc = subprocess.Popen(
            ["mkdir", "-p", os.path.dirname(local_path)],
            stdout = open("/dev/null","w"),
            stdin = open("/dev/null","r"))

        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        (out,err),proc = server.popen_ssh_command(
            "echo 'Rules:' ; sudo -S netconfig show rules ; echo 'Pipes:' ; sudo -S netconfig show pipes",
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        # dump results to file
        f = open(local_path, "wb")
        f.write(err or "")
        f.write(out or "")
        f.close()
        
        return local_path
    
