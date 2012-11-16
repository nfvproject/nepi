import xmlrpclib
import functools
import socket
import time
import threading

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
        ['AddNodeTag', 'AddConfFile', 'DeletePersonTag', 'AddNodeType', 'DeleteBootState', 'SliceListNames', 'DeleteKey', 
         'SliceGetTicket', 'SliceUsersList', 'SliceUpdate', 'GetNodeGroups', 'SliceCreate', 'GetNetworkMethods', 'GetNodeFlavour', 
         'DeleteNode', 'BootNotifyOwners', 'AddPersonKey', 'AddNode', 'UpdateNodeGroup', 'GetAddressTypes', 'AddIlink', 'DeleteNetworkType', 
         'GetInitScripts', 'GenerateNodeConfFile', 'AddSite', 'BindObjectToPeer', 'SliceListUserSlices', 'GetPeers', 'AddPeer', 'DeletePeer', 
         'AddRole', 'DeleteRole', 'SetPersonPrimarySite', 'AddSiteAddress', 'SliceDelete', 'NotifyPersons', 'GetKeyTypes', 'GetConfFiles', 
         'GetIlinks', 'AddTagType', 'GetNodes', 'DeleteNodeTag', 'DeleteSliceFromNodesWhitelist', 'UpdateAddress', 'ResetPassword', 
         'AddSliceToNodesWhitelist', 'AddRoleToTagType', 'AddLeases', 'GetAddresses', 'AddInitScript', 'RebootNode', 'GetPCUTypes', 
         'RefreshPeer', 'GetBootMedium', 'UpdateKey', 'UpdatePCU', 'GetSession', 'AddInterfaceTag', 'UpdatePCUType', 'GetInterfaces', 
         'SliceExtendedInfo', 'SliceNodesList', 'DeleteRoleFromTagType', 'DeleteSlice', 'GetSites', 'DeleteMessage', 'GetSliceFamily', 
         'GetPlcRelease', 'UpdateTagType', 'AddSliceInstantiation', 'ResolveSlices', 'GetSlices', 'DeleteRoleFromPerson', 'GetSessions', 
         'UpdatePeer', 'VerifyPerson', 'GetPersonTags', 'DeleteKeyType', 'AddSlice', 'SliceUserAdd', 'DeleteSession', 'GetMessages', 
         'DeletePCU', 'GetPeerData', 'DeletePersonFromSite', 'DeleteTagType', 'GetPCUs', 'UpdateLeases', 'AddMessage', 
         'DeletePCUProtocolType', 'DeleteInterfaceTag', 'AddPersonToSite', 'GetSlivers', 'SliceNodesDel', 'DeleteAddressTypeFromAddress', 
         'AddNodeGroup', 'GetSliceTags', 'DeleteSite', 'GetSiteTags', 'UpdateMessage', 'DeleteSliceFromNodes', 'SliceRenew', 
         'UpdatePCUProtocolType', 'DeleteSiteTag', 'GetPCUProtocolTypes', 'GetEvents', 'GetSliceTicket', 'AddPersonTag', 'BootGetNodeDetails', 
         'DeleteInterface', 'DeleteNodeGroup', 'AddPCUProtocolType', 'BootCheckAuthentication', 'AddSiteTag', 'AddAddressTypeToAddress', 
         'DeleteConfFile', 'DeleteInitScript', 'DeletePerson', 'DeleteIlink', 'DeleteAddressType', 'AddBootState', 'AuthCheck', 
         'NotifySupport', 'GetSliceInstantiations', 'AddPCUType', 'AddPCU', 'AddSession', 'GetEventObjects', 'UpdateSiteTag', 
         'UpdateNodeTag', 'AddPerson', 'BlacklistKey', 'UpdateInitScript', 'AddSliceToNodes', 'RebootNodeWithPCU', 'GetNodeTags', 
         'GetSliceKeys', 'GetSliceSshKeys', 'AddNetworkMethod', 'SliceNodesAdd', 'DeletePersonFromSlice', 'ReportRunlevel', 
         'GetNetworkTypes', 'UpdateSite', 'DeleteConfFileFromNodeGroup', 'UpdateNode', 'DeleteSliceInstantiation', 'DeleteSliceTag', 
         'BootUpdateNode', 'UpdatePerson', 'UpdateConfFile', 'SliceUserDel', 'DeleteLeases', 'AddConfFileToNodeGroup', 'UpdatePersonTag', 
         'DeleteConfFileFromNode', 'AddPersonToSlice', 'UnBindObjectFromPeer', 'AddNodeToPCU', 'GetLeaseGranularity', 'DeletePCUType', 
         'GetTagTypes', 'GetNodeTypes', 'UpdateInterfaceTag', 'GetRoles', 'UpdateSlice', 'UpdateSliceTag', 'AddSliceTag', 'AddNetworkType', 
         'AddInterface', 'AddAddressType', 'AddRoleToPerson', 'DeleteNodeType', 'GetLeases', 'UpdateInterface', 'SliceInfo', 'DeleteAddress', 
         'SliceTicketGet', 'GetPersons', 'GetWhitelist', 'AddKeyType', 'UpdateAddressType', 'GetPeerName', 'DeleteNetworkMethod', 
         'UpdateIlink', 'AddConfFileToNode', 'GetKeys', 'DeleteNodeFromPCU', 'GetInterfaceTags', 'GetBootStates', 'SetInterfaceSens', 'SetNodeLoadm', 
         'GetInterfaceRate', 'GetNodeLoadw', 'SetInterfaceKey', 'GetNodeSlices', 'GetNodeLoadm', 'SetSliceVref', 'GetInterfaceIwpriv', 'SetNodeLoadw', 
         'SetNodeSerial', 'GetNodePlainBootstrapfs', 'SetNodeMEMw', 'GetNodeResponse', 'SetInterfaceRate', 'SetSliceInitscript', 
         'SetNodeFcdistro', 'GetNodeLoady', 'SetNodeArch', 'SetNodeKargs', 'SetNodeMEMm', 'SetNodeBWy', 'SetNodeBWw', 
         'SetInterfaceSecurityMode', 'SetNodeBWm', 'SetNodeASType', 'GetNodeKargs', 'GetPersonColumnconf', 'GetNodeResponsem', 
         'GetNodeCPUy', 'GetNodeCramfs', 'SetNodeSlicesw', 'SetPersonColumnconf', 'SetNodeSlicesy', 'GetNodeCPUw', 'GetNodeBWy', 
         'GetNodeCPUm', 'GetInterfaceDriver', 'GetNodeLoad', 'GetInterfaceMode', 'GetNodeSerial', 'SetNodeSlicesm', 'SetNodeLoady', 
         'GetNodeReliabilityw', 'SetSliceFcdistro', 'GetNodeReliabilityy', 'SetInterfaceEssid', 'SetSliceInitscriptCode', 
         'GetNodeExtensions', 'GetSliceOmfControl', 'SetNodeCity', 'SetInterfaceIfname', 'SetNodeHrn', 'SetNodeNoHangcheck', 
         'GetNodeNoHangcheck', 'GetSliceFcdistro', 'SetNodeCountry', 'SetNodeKvariant', 'GetNodeKvariant', 'GetNodeMEMy', 
         'SetInterfaceIwpriv', 'GetNodeMEMw', 'SetInterfaceBackdoor', 'GetInterfaceFreq', 'SetInterfaceChannel', 'SetInterfaceNw', 
         'GetPersonShowconf', 'GetSliceInitscriptCode', 'SetNodeMEM', 'GetInterfaceEssid', 'GetNodeMEMm', 'SetInterfaceMode', 
         'SetInterfaceIwconfig', 'GetNodeSlicesm', 'GetNodeBWm', 'SetNodePlainBootstrapfs', 'SetNodeRegion', 'SetNodeCPU', 
         'GetNodeSlicesw', 'SetNodeBW', 'SetNodeSlices', 'SetNodeCramfs', 'GetNodeSlicesy', 'GetInterfaceKey', 'GetSliceInitscript', 
         'SetNodeCPUm', 'SetSliceArch', 'SetNodeLoad', 'SetNodeResponse', 'GetSliceSliverHMAC', 'GetNodeBWw', 'GetNodeRegion', 
         'SetNodeMEMy', 'GetNodeASType', 'SetNodePldistro', 'GetSliceArch', 'GetNodeCountry', 'SetSliceOmfControl', 'GetNodeHrn', 
         'GetNodeCity', 'SetInterfaceAlias', 'GetNodeBW', 'GetNodePldistro', 'GetSlicePldistro', 'SetNodeASNumber', 'GetSliceHmac', 
         'SetSliceHmac', 'GetNodeMEM', 'GetNodeASNumber', 'GetInterfaceAlias', 'GetSliceVref', 'GetNodeArch', 'GetSliceSshKey', 
         'GetInterfaceKey4', 'GetInterfaceKey2', 'GetInterfaceKey3', 'GetInterfaceKey1', 'GetInterfaceBackdoor', 'GetInterfaceIfname', 
         'SetSliceSliverHMAC', 'SetNodeReliability', 'GetNodeCPU', 'SetPersonShowconf', 'SetNodeExtensions', 'SetNodeCPUy', 
         'SetNodeCPUw', 'GetNodeResponsew', 'SetNodeResponsey', 'GetInterfaceSens', 'SetNodeResponsew', 'GetNodeResponsey', 
         'GetNodeReliability', 'GetNodeReliabilitym', 'SetNodeResponsem', 'SetInterfaceDriver', 'GetInterfaceSecurityMode', 
         'SetNodeDeployment', 'SetNodeReliabilitym', 'GetNodeFcdistro', 'SetInterfaceFreq', 'GetInterfaceNw', 'SetNodeReliabilityy', 
         'SetNodeReliabilityw', 'GetInterfaceIwconfig', 'SetSlicePldistro', 'SetSliceSshKey', 'GetNodeDeployment', 'GetInterfaceChannel', 
         'SetInterfaceKey2', 'SetInterfaceKey3', 'SetInterfaceKey1', 'SetInterfaceKey4'])
     
    _required_methods = set()

    def __init__(self, username=None, password=None, sessionkey=None, proxy=None,
            hostname = "www.planet-lab.eu",
            urlpattern = "https://%(hostname)s:443/PLCAPI/",
            localPeerName = "PLE"):
        if sessionkey is not None:
            self.auth = dict(AuthMethod='session', session=sessionkey)
        elif username is not None and password is not None:
            self.auth = dict(AuthMethod='password', Username=username, AuthString=password)
        else:
            self.auth = dict(AuthMethod='anonymous')
        
        self._localPeerName = localPeerName
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
            self._proxyTransport = lambda : HTTPSProxyTransport(proxy)
        else:
            self._proxyTransport = lambda : None
        
        self.threadlocal = threading.local()
    
    @property
    def api(self):
        # Cannot reuse same proxy in all threads, py2.7 is not threadsafe
        return xmlrpclib.ServerProxy(
            self._url ,
            transport = self._proxyTransport(),
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
            warnings.warn("Unsupported REQUIRED methods: %s" % ( ", ".join(sorted(self._required_methods - methods)), ) )
            return False
        if self._expected_methods - methods:
            warnings.warn("Unsupported EXPECTED methods: %s" % ( ", ".join(sorted(self._expected_methods - methods)), ) )
        
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
            self._peer_map[None] = self._localPeerName
            return self._peer_map
    

    def GetNodeFlavour(self, node):
        """
        Returns detailed information on a given node's flavour, i.e. its base installation.

        This depends on the global PLC settings in the PLC_FLAVOUR area, optionnally overridden by any of the following tags if set on that node:
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
    
    def GetNodes(self, nodeIdOrName=None, fields=None, **kw):
        """
        Returns an array of structs containing details about nodes. 
        If nodeIdOrName is specified and is an array of node identifiers or hostnames, 
        or the filters keyword argument with struct of node attributes, 
        or node attributes by keyword argument,
        only nodes matching the filter will be returned.

        If fields is specified, only the specified details will be returned. 
        NOTE that if fields is unspecified, the complete set of native fields are returned, 
        which DOES NOT include tags at this time.

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
        if nodeIdOrName is not None:
            return _retry(self.mcapi.GetNodes)(self.auth, nodeIdOrName, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            
            if 'peer' in kw:
                peer = kw.pop('peer')
                
                nameToId = self.peer_map.get
                
                if hasattr(peer, '__iter__'):
                    # we can't mix local and external nodes, so
                    # split and re-issue recursively in that case
                    if None in peer or self._localPeerName in peer:
                        if None in peer:    
                            peer.remove(None)
                        if self._localPeerName in peer:
                            peer.remove(self._localPeerName)
                        return (
                            self.GetNodes(nodeIdOrName, fields, filters=filters, peer=peer, **kw)
                            + self.GetNodes(nodeIdOrName, fields, filters=filters, peer=None, **kw)
                        )
                    else:
                        peer_filter = map(nameToId, peer)
                elif peer is None or peer == self._localPeerName:
                    peer_filter = None
                else:
                    peer_filter = nameToId(peer)
                
                filters['peer_id'] = peer_filter
            
            filters.update(kw)
            return _retry(self.mcapi.GetNodes)(self.auth, filters, *fieldstuple)
    
    def GetNodeTags(self, nodeTagId=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if nodeTagId is not None:
            return _retry(self.mcapi.GetNodeTags)(self.auth, nodeTagId, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetNodeTags)(self.auth, filters, *fieldstuple)

    def GetSliceTags(self, sliceTagId=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if sliceTagId is not None:
            return _retry(self.mcapi.GetSliceTags)(self.auth, sliceTagId, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetSliceTags)(self.auth, filters, *fieldstuple)
    
    def GetInterfaces(self, interfaceIdOrIp=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if interfaceIdOrIp is not None:
            return _retry(self.mcapi.GetInterfaces)(self.auth, interfaceIdOrIp, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetInterfaces)(self.auth, filters, *fieldstuple)
        
    def GetSlices(self, sliceIdOrName=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if sliceIdOrName is not None:
            return _retry(self.mcapi.GetSlices)(self.auth, sliceIdOrName, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.GetSlices)(self.auth, filters, *fieldstuple)
        
    def UpdateSlice(self, sliceIdOrName, **kw):
        return _retry(self.mcapi.UpdateSlice)(self.auth, sliceIdOrName, kw)

    def StartMulticall(self):
        self.threadlocal.mc = xmlrpclib.MultiCall(self.mcapi)
    
    def FinishMulticall(self):
        mc = self.threadlocal.mc
        del self.threadlocal.mc
        return _retry(mc)()

    def GetSliceNodes(self, slicename):
        return self.GetSlices(slicename, ['node_ids'])[0]['node_ids']

    def AddSliceNodes(self, slicename,  nodes = None):
        self.UpdateSlice(slicename, nodes = nodes)

    def GetNodeInfo(self, node_id):
        self.StartMulticall()
        info = self.GetNodes(node_id)
        tags = self.GetNodeTags(node_id=node_id, fields=('tagname','value'))
        info, tags = self.FinishMulticall()
        return info, tags

    def GetSliceId(self, slicename):
        slice_id = None
        slices = self.GetSlices(slicename, fields=('slice_id',))
        if slices:
            slice_id = slices[0]['slice_id']
        # If it wasn't found, don't remember this failure, keep trying
        return slice_id

    def GetSliceVnetSysTag(self, slicename):
        slicetags = self.GetSliceTags(
            name = slicename,
            tagname = 'vsys_vnet',
            fields=('value',))
        if slicetags:
            return slicetags[0]['value']
        else:
            return None
 
def plcapi(auth_user, auth_string, plc_host, plc_url, proxy):
    api = None
    if auth_user:
        api = PLCAPI(
            username = auth_user,
            password = auth_string,
            hostname = plc_host,
            urlpattern = plc_url,
            proxy = proxy
        )
    else:
        # anonymous access - may not be enough for much
        api = PLCAPI()
    return api


