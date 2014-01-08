#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

import functools
import hashlib
import socket
import time
import threading
import xmlrpclib

def _retry(fn):
    def rv(*p, **kw):
        for x in xrange(5):
            try:
                return fn(*p, **kw)
            except (socket.error, IOError, OSError):
                time.sleep(x*5+5)
        else:
            return fn (*p, **kw)
    return rv

class PLCAPI(object):

    _expected_methods = set(
        ['AddNodeTag', 'AddConfFile', 'DeletePersonTag', 'AddNodeType',
         'DeleteBootState', 'SliceListNames', 'DeleteKey','SliceGetTicket', 
         'SliceUsersList', 'SliceUpdate', 'GetNodeGroups', 'SliceCreate', 
         'GetNetworkMethods', 'GetNodeFlavour', 'DeleteNode', 'BootNotifyOwners',
         'AddPersonKey', 'AddNode', 'UpdateNodeGroup', 'GetAddressTypes',
         'AddIlink', 'DeleteNetworkType', 'GetInitScripts', 'GenerateNodeConfFile',
         'AddSite', 'BindObjectToPeer', 'SliceListUserSlices', 'GetPeers',
         'AddPeer', 'DeletePeer', 'AddRole', 'DeleteRole', 'SetPersonPrimarySite',
         'AddSiteAddress', 'SliceDelete', 'NotifyPersons', 'GetKeyTypes',
         'GetConfFiles', 'GetIlinks', 'AddTagType', 'GetNodes', 'DeleteNodeTag',
         'DeleteSliceFromNodesWhitelist', 'UpdateAddress', 'ResetPassword', 
         'AddSliceToNodesWhitelist', 'AddRoleToTagType', 'AddLeases',
         'GetAddresses', 'AddInitScript', 'RebootNode', 'GetPCUTypes', 
         'RefreshPeer', 'GetBootMedium', 'UpdateKey', 'UpdatePCU', 'GetSession',
         'AddInterfaceTag', 'UpdatePCUType', 'GetInterfaces', 'SliceExtendedInfo',
         'SliceNodesList', 'DeleteRoleFromTagType', 'DeleteSlice', 'GetSites',
         'DeleteMessage', 'GetSliceFamily', 'GetPlcRelease', 'UpdateTagType',
         'AddSliceInstantiation', 'ResolveSlices', 'GetSlices',
         'DeleteRoleFromPerson', 'GetSessions', 'UpdatePeer', 'VerifyPerson',
         'GetPersonTags', 'DeleteKeyType', 'AddSlice', 'SliceUserAdd',
         'DeleteSession', 'GetMessages', 'DeletePCU', 'GetPeerData',
         'DeletePersonFromSite', 'DeleteTagType', 'GetPCUs', 'UpdateLeases',
         'AddMessage', 'DeletePCUProtocolType', 'DeleteInterfaceTag',
         'AddPersonToSite', 'GetSlivers', 'SliceNodesDel',
         'DeleteAddressTypeFromAddress', 'AddNodeGroup', 'GetSliceTags',
         'DeleteSite', 'GetSiteTags', 'UpdateMessage', 'DeleteSliceFromNodes',
         'SliceRenew', 'UpdatePCUProtocolType', 'DeleteSiteTag',
         'GetPCUProtocolTypes', 'GetEvents', 'GetSliceTicket', 'AddPersonTag',
         'BootGetNodeDetails', 'DeleteInterface', 'DeleteNodeGroup',
         'AddPCUProtocolType', 'BootCheckAuthentication', 'AddSiteTag',
         'AddAddressTypeToAddress', 'DeleteConfFile', 'DeleteInitScript',
         'DeletePerson', 'DeleteIlink', 'DeleteAddressType', 'AddBootState',
         'AuthCheck', 'NotifySupport', 'GetSliceInstantiations', 'AddPCUType',
         'AddPCU', 'AddSession', 'GetEventObjects', 'UpdateSiteTag', 
         'UpdateNodeTag', 'AddPerson', 'BlacklistKey', 'UpdateInitScript',
         'AddSliceToNodes', 'RebootNodeWithPCU', 'GetNodeTags', 'GetSliceKeys',
         'GetSliceSshKeys', 'AddNetworkMethod', 'SliceNodesAdd',
         'DeletePersonFromSlice', 'ReportRunlevel', 'GetNetworkTypes',
         'UpdateSite', 'DeleteConfFileFromNodeGroup', 'UpdateNode',
         'DeleteSliceInstantiation', 'DeleteSliceTag', 'BootUpdateNode',
         'UpdatePerson', 'UpdateConfFile', 'SliceUserDel', 'DeleteLeases',
         'AddConfFileToNodeGroup', 'UpdatePersonTag', 'DeleteConfFileFromNode',
         'AddPersonToSlice', 'UnBindObjectFromPeer', 'AddNodeToPCU',
         'GetLeaseGranularity', 'DeletePCUType', 'GetTagTypes', 'GetNodeTypes',
         'UpdateInterfaceTag', 'GetRoles', 'UpdateSlice', 'UpdateSliceTag',
         'AddSliceTag', 'AddNetworkType', 'AddInterface', 'AddAddressType',
         'AddRoleToPerson', 'DeleteNodeType', 'GetLeases', 'UpdateInterface',
         'SliceInfo', 'DeleteAddress', 'SliceTicketGet', 'GetPersons',
         'GetWhitelist', 'AddKeyType', 'UpdateAddressType', 'GetPeerName',
         'DeleteNetworkMethod', 'UpdateIlink', 'AddConfFileToNode', 'GetKeys',
         'DeleteNodeFromPCU', 'GetInterfaceTags', 'GetBootStates',
         'SetInterfaceSens', 'SetNodeLoadm', 'GetInterfaceRate', 'GetNodeLoadw',
         'SetInterfaceKey', 'GetNodeSlices', 'GetNodeLoadm', 'SetSliceVref',
         'GetInterfaceIwpriv', 'SetNodeLoadw', 'SetNodeSerial',
         'GetNodePlainBootstrapfs', 'SetNodeMEMw', 'GetNodeResponse',
         'SetInterfaceRate', 'SetSliceInitscript', 'SetNodeFcdistro',
         'GetNodeLoady', 'SetNodeArch', 'SetNodeKargs', 'SetNodeMEMm',
         'SetNodeBWy', 'SetNodeBWw', 'SetInterfaceSecurityMode', 'SetNodeBWm',
         'SetNodeASType', 'GetNodeKargs', 'GetPersonColumnconf',
         'GetNodeResponsem', 'GetNodeCPUy', 'GetNodeCramfs', 'SetNodeSlicesw',
         'SetPersonColumnconf', 'SetNodeSlicesy', 'GetNodeCPUw', 'GetNodeBWy', 
         'GetNodeCPUm', 'GetInterfaceDriver', 'GetNodeLoad', 'GetInterfaceMode',
         'GetNodeSerial', 'SetNodeSlicesm', 'SetNodeLoady', 'GetNodeReliabilityw',
         'SetSliceFcdistro', 'GetNodeReliabilityy', 'SetInterfaceEssid',
         'SetSliceInitscriptCode', 'GetNodeExtensions', 'GetSliceOmfControl',
         'SetNodeCity', 'SetInterfaceIfname', 'SetNodeHrn', 'SetNodeNoHangcheck', 
         'GetNodeNoHangcheck', 'GetSliceFcdistro', 'SetNodeCountry',
         'SetNodeKvariant', 'GetNodeKvariant', 'GetNodeMEMy', 'SetInterfaceIwpriv',
         'GetNodeMEMw', 'SetInterfaceBackdoor', 'GetInterfaceFreq',
         'SetInterfaceChannel', 'SetInterfaceNw', 'GetPersonShowconf',
         'GetSliceInitscriptCode', 'SetNodeMEM', 'GetInterfaceEssid', 'GetNodeMEMm',
         'SetInterfaceMode', 'SetInterfaceIwconfig', 'GetNodeSlicesm', 'GetNodeBWm',
         'SetNodePlainBootstrapfs', 'SetNodeRegion', 'SetNodeCPU', 'GetNodeSlicesw',
         'SetNodeBW', 'SetNodeSlices', 'SetNodeCramfs', 'GetNodeSlicesy',
         'GetInterfaceKey', 'GetSliceInitscript', 'SetNodeCPUm', 'SetSliceArch',
         'SetNodeLoad', 'SetNodeResponse', 'GetSliceSliverHMAC', 'GetNodeBWw',
         'GetNodeRegion', 'SetNodeMEMy', 'GetNodeASType', 'SetNodePldistro',
         'GetSliceArch', 'GetNodeCountry', 'SetSliceOmfControl', 'GetNodeHrn', 
         'GetNodeCity', 'SetInterfaceAlias', 'GetNodeBW', 'GetNodePldistro',
         'GetSlicePldistro', 'SetNodeASNumber', 'GetSliceHmac', 'SetSliceHmac',
         'GetNodeMEM', 'GetNodeASNumber', 'GetInterfaceAlias', 'GetSliceVref',
         'GetNodeArch', 'GetSliceSshKey', 'GetInterfaceKey4', 'GetInterfaceKey2',
         'GetInterfaceKey3', 'GetInterfaceKey1', 'GetInterfaceBackdoor',
         'GetInterfaceIfname', 'SetSliceSliverHMAC', 'SetNodeReliability',
         'GetNodeCPU', 'SetPersonShowconf', 'SetNodeExtensions', 'SetNodeCPUy', 
         'SetNodeCPUw', 'GetNodeResponsew', 'SetNodeResponsey', 'GetInterfaceSens',
         'SetNodeResponsew', 'GetNodeResponsey', 'GetNodeReliability',
         'GetNodeReliabilitym', 'SetNodeResponsem', 'SetInterfaceDriver',
         'GetInterfaceSecurityMode', 'SetNodeDeployment', 'SetNodeReliabilitym',
         'GetNodeFcdistro', 'SetInterfaceFreq', 'GetInterfaceNw',
         'SetNodeReliabilityy', 'SetNodeReliabilityw', 'GetInterfaceIwconfig',
         'SetSlicePldistro', 'SetSliceSshKey', 'GetNodeDeployment',
         'GetInterfaceChannel', 'SetInterfaceKey2', 'SetInterfaceKey3',
         'SetInterfaceKey1', 'SetInterfaceKey4'])
     
    _required_methods = set()

    def __init__(self, username = None, password = None, session_key = None, 
            proxy = None,
            hostname = "www.planet-lab.eu",
            urlpattern = "https://%(hostname)s:443/PLCAPI/",
            local_peer = "PLE"):

        self._blacklist = set()
        self._reserved = set()
        self._nodes_cache = None

        if session_key is not None:
            self.auth = dict(AuthMethod='session', session=session_key)
        elif username is not None and password is not None:
            self.auth = dict(AuthMethod='password', Username=username, AuthString=password)
        else:
            self.auth = dict(AuthMethod='anonymous')
        
        self._local_peer = local_peer
        self._url = urlpattern % {'hostname':hostname}

        if (proxy is not None):
            import urllib2
            class HTTPSProxyTransport(xmlrpclib.Transport):
                def __init__(self, proxy, use_datetime=0):
                    opener = urllib2.build_opener(urllib2.ProxyHandler({"https" : proxy}))
                    xmlrpclib.Transport.__init__(self, use_datetime)
                    self.opener = opener

                def request(self, host, handler, request_body, verbose=0):
                    req = urllib2.Request('https://%s%s' % (host, handler), request_body)
                    req.add_header('User-agent', self.user_agent)
                    self.verbose = verbose
                    return self.parse_response(self.opener.open(req))

            self._proxy_transport = lambda : HTTPSProxyTransport(proxy)
        else:
            self._proxy_transport = lambda : None
        
        self.threadlocal = threading.local()
    
    @property
    def api(self):
        # Cannot reuse same proxy in all threads, py2.7 is not threadsafe
        return xmlrpclib.ServerProxy(
            self._url ,
            transport = self._proxy_transport(),
            allow_none = True)
        
    @property
    def mcapi(self):
        try:
            return self.threadlocal.mc
        except AttributeError:
            return self.api
        
    def test(self):
        import warnings
        
        # validate XMLRPC server checking supported API calls
        methods = set(_retry(self.mcapi.system.listMethods)())
        if self._required_methods - methods:
            warnings.warn("Unsupported REQUIRED methods: %s" % (
                ", ".join(sorted(self._required_methods - methods)), ) )
            return False

        if self._expected_methods - methods:
            warnings.warn("Unsupported EXPECTED methods: %s" % (
                ", ".join(sorted(self._expected_methods - methods)), ) )
        
        try:
            # test authorization
            network_types = _retry(self.mcapi.GetNetworkTypes)(self.auth)
        except (xmlrpclib.ProtocolError, xmlrpclib.Fault),e:
            warnings.warn(str(e))
        
        return True
    
    @property
    def network_types(self):
        try:
            return self._network_types
        except AttributeError:
            self._network_types = _retry(self.mcapi.GetNetworkTypes)(self.auth)
            return self._network_types
    
    @property
    def peer_map(self):
        try:
            return self._peer_map
        except AttributeError:
            peers = _retry(self.mcapi.GetPeers)(self.auth, {}, ['shortname','peername','peer_id'])
            
            self._peer_map = dict(
                (peer['shortname'], peer['peer_id'])
                for peer in peers
            )

            self._peer_map.update(
                (peer['peername'], peer['peer_id'])
                for peer in peers
            )

            self._peer_map.update(
                (peer['peer_id'], peer['shortname'])
                for peer in peers
            )

            self._peer_map[None] = self._local_peer
            return self._peer_map

    def get_node_flavour(self, node):
        """
        Returns detailed information on a given node's flavour,
        i.e. its base installation.

        This depends on the global PLC settings in the PLC_FLAVOUR area,
        optionnally overridden by any of the following tags if set on that node:
        'arch', 'pldistro', 'fcdistro', 'deployment', 'extensions'
        
        Params:
        
            * node : int or string
                - int, Node identifier
                - string, Fully qualified hostname
        
        Returns:

            struct
                * extensions : array of string, extensions to add to the base install
                * fcdistro : string, the fcdistro this node should be based upon
                * nodefamily : string, the nodefamily this node should be based upon
                * plain : boolean, use plain bootstrapfs image if set (for tests)  
        """
        if not isinstance(node, (str, int, long)):
            raise ValueError, "Node must be either a non-unicode string or an int"
        return _retry(self.mcapi.GetNodeFlavour)(self.auth, node)
    
    def get_nodes(self, node_id_or_name = None, fields = None, **kw):
        """
        Returns an array of structs containing details about nodes. 
        If node_id_or_name is specified and is an array of node identifiers
        or hostnames,  or the filters keyword argument with struct of node
        attributes, or node attributes by keyword argument,
        only nodes matching the filter will be returned.

        If fields is specified, only the specified details will be returned. 
        NOTE that if fields is unspecified, the complete set of native fields are
        returned, which DOES NOT include tags at this time.

        Some fields may only be viewed by admins.
        
        Special params:
            
            fields: an optional list of fields to retrieve. The default is all.
            
            filters: an optional mapping with custom filters, which is the only
                way to support complex filters like negation and numeric comparisons.
                
            peer: a string (or sequence of strings) with the name(s) of peers
                to filter - or None for local nodes.
        """
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()

        if node_id_or_name is not None:
            return _retry(self.mcapi.GetNodes)(self.auth, node_id_or_name, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            
            if 'peer' in kw:
                peer = kw.pop('peer')
                
                name_to_id = self.peer_map.get
                
                if hasattr(peer, '__iter__'):
                    # we can't mix local and external nodes, so
                    # split and re-issue recursively in that case
                    if None in peer or self._local_peer in peer:
                        if None in peer:    
                            peer.remove(None)

                        if self._local_peer in peer:
                            peer.remove(self._local_peer)

                        return (
                            self.get_nodes(node_id_or_name, fields,
                                    filters = filters, peer=peer, **kw) + \
                            self.get_nodes(node_id_or_name, fields, 
                                    filters = filters, peer=None, **kw)
                         )
                    else:
                        peer_filter = map(name_to_id, peer)

                elif peer is None or peer == self._local_peer:
                    peer_filter = None
                else:
                    peer_filter = name_to_id(peer)
                
                filters['peer_id'] = peer_filter
            
            filters.update(kw)

            if not filters and not fieldstuple:
                if not self._nodes_cache:
                    self._nodes_cache = _retry(self.mcapi.GetNodes)(self.auth)
                return self._nodes_cache

            return _retry(self.mcapi.GetNodes)(self.auth, filters, *fieldstuple)
    
    def get_node_tags(self, node_tag_id = None, fields = None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()

        if node_tag_id is not None:
            return _retry(self.mcapi.GetNodeTags)(self.auth, node_tag_id,
                    *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetNodeTags)(self.auth, filters,
                    *fieldstuple)

    def get_slice_tags(self, slice_tag_id = None, fields = None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()

        if slice_tag_id is not None:
            return _retry(self.mcapi.GetSliceTags)(self.auth, slice_tag_id,
                    *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetSliceTags)(self.auth, filters,
                    *fieldstuple)
    
    def get_interfaces(self, interface_id_or_ip = None, fields = None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()

        if interface_id_or_ip is not None:
            return _retry(self.mcapi.GetInterfaces)(self.auth,
                    interface_id_or_ip, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetInterfaces)(self.auth, filters,
                    *fieldstuple)
        
    def get_slices(self, slice_id_or_name = None, fields = None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()

        if slice_id_or_name is not None:
            return _retry(self.mcapi.GetSlices)(self.auth, slice_id_or_name,
                    *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetSlices)(self.auth, filters,
                    *fieldstuple)
        
    def update_slice(self, slice_id_or_name, **kw):
        return _retry(self.mcapi.UpdateSlice)(self.auth, slice_id_or_name, kw)

    def delete_slice_node(self, slice_id_or_name, node_id_or_hostname):
        return _retry(self.mcapi.DeleteSliceFromNodes)(self.auth, slice_id_or_name, node_id_or_hostname)

    def start_multicall(self):
        self.threadlocal.mc = xmlrpclib.MultiCall(self.mcapi)
    
    def finish_multicall(self):
        mc = self.threadlocal.mc
        del self.threadlocal.mc
        return _retry(mc)()

    def get_slice_nodes(self, slicename):
        return self.get_slices(slicename, ['node_ids'])[0]['node_ids']

    def add_slice_nodes(self, slicename, nodes = None):
        self.update_slice(slicename, nodes = nodes)

    def get_node_info(self, node_id):
        self.start_multicall()
        info = self.get_nodes(node_id)
        tags = self.get_node_tags(node_id=node_id, fields=('tagname','value'))
        info, tags = self.finish_multicall()
        return info, tags

    def get_slice_id(self, slicename):
        slice_id = None
        slices = self.get_slices(slicename, fields=('slice_id',))
        if slices:
            slice_id = slices[0]['slice_id']

        # If it wasn't found, don't remember this failure, keep trying
        return slice_id

    def get_slice_vnet_sys_tag(self, slicename):
        slicetags = self.get_slice_tags(
            name = slicename,
            tagname = 'vsys_vnet',
            fields=('value',))

        if slicetags:
            return slicetags[0]['value']
        else:
            return None

    def blacklist_host(self, hostname):
        self._blacklist.add(hostname)

    def blacklisted(self):
        return self._blacklist

    def unblacklist_host(self, hostname):
        del self._blacklist[hostname]

    def reserve_host(self, hostname):
        self._reserved.add(hostname)

    def reserved(self):
        return self._reserved

    def unreserve_host(self, hostname):
        del self._reserved[hostname]


class PLCAPIFactory(object):
    """ 
    .. note::

        It allows PlanetLab RMs sharing a same slice, to use a same plcapi instance,
        and to sincronize blacklisted and reserved hosts.

    """
    # use lock to avoid concurrent access to the Api list at the same times by 2 different threads
    _lock = threading.Lock()
    _apis = dict()

    @classmethod 
    def get_api(cls, pl_user, pl_pass, pl_host,
            pl_ptn = "https://%(hostname)s:443/PLCAPI/",
            proxy = None):
        """ Get existing PLCAPI instance

        :param pl_user: Planelab user name (used for web login)
        :type pl_user: str
        :param pl_pass: Planetlab password (used for web login)
        :type pl_pass: str
        :param pl_host: Planetlab registry host (e.g. "www.planet-lab.eu")
        :type pl_host: str
        :param pl_ptn: XMLRPC service pattern (e.g. https://%(hostname)s:443/PLCAPI/)
        :type pl_ptn: str
        :param proxy: Proxy service url
        :type pl_ptn: str
        """
        if pl_user and pl_pass and pl_host:
            key = cls._make_key(pl_user, pl_host)
            with cls._lock:
                api = cls._apis.get(key)
                if not api:
                    api = cls.create_api(pl_user, pl_pass, pl_host, pl_ptn, proxy)
                return api
        return None

    @classmethod 
    def create_api(cls, pl_user, pl_pass, pl_host,
            pl_ptn = "https://%(hostname)s:443/PLCAPI/",
            proxy = None):
        """ Create an PLCAPI instance

        :param pl_user: Planelab user name (used for web login)
        :type pl_user: str
        :param pl_pass: Planetlab password (used for web login)
        :type pl_pass: str
        :param pl_host: Planetlab registry host (e.g. "www.planet-lab.eu")
        :type pl_host: str
        :param pl_ptn: XMLRPC service pattern (e.g. https://%(hostname)s:443/PLCAPI/)
        :type pl_ptn: str
        :param proxy: Proxy service url
        :type pl_ptn: str
        """
        api = PLCAPI(
            username = pl_user,
            password = pl_pass,
            hostname = pl_host,
            urlpattern = pl_ptn,
            proxy = proxy
        )
        key = cls._make_key(pl_user, pl_host)
        cls._apis[key] = api
        return api

    @classmethod 
    def _make_key(cls, *args):
        """ Hash the credentials in order to create a key

        :param args: list of arguments used to create the hash (user, host, port, ...)
        :type args: list of args

        """
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()

