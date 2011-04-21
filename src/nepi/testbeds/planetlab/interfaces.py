#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import nepi.util.ipaddr2 as ipaddr2
import plcapi

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
        self.broadcast = True
        self._interface_id = None

        # These get initialized when the iface is connected to its node
        self.node = None

        # These get initialized when the iface is connected to the internet
        self.has_internet = False

    def add_address(self, address, netprefix, broadcast):
        raise RuntimeError, "Cannot add explicit addresses to public interface"
    
    def pick_iface(self, siblings):
        """
        Picks an interface using the PLCAPI to query information about the node.
        
        Needs an assigned node.
        
        Params:
            siblings: other NodeIface elements attached to the same node
        """
        
        if (self.node or self.node._node_id) is None:
            raise RuntimeError, "Cannot pick interface without an assigned node"
        
        avail = self._api.GetInterfaces(
            node_id=self.node._node_id, 
            is_primary=self.primary,
            fields=('interface_id','mac','netmask','ip') ))
        
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
                return
        else:
            raise RuntimeError, "Cannot configure interface: cannot find suitable interface in PlanetLab node"

    def validate(self):
        if not element.has_internet:
            raise RuntimeError, "All external interface devices must be connected to the Internet"
    

class TunIface(object):
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

        # These get initialized when the iface is connected to its node
        self.node = None

    def add_address(self, address, netprefix, broadcast):
        if (self.address or self.netprefix or self.netmask) is not None:
            raise RuntimeError, "Cannot add more than one address to TUN interfaces"
        if broadcast:
            raise ValueError, "TUN interfaces cannot broadcast in PlanetLab"
        
        self.address = address
        self.netprefix = netprefix
        self.netmask = ipaddr2.ipv4_dot2mask(netprefix)

    def validate(self):
        pass
    

# Yep, it does nothing - yet
class Internet(object):
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api


