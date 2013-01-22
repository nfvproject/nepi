import xmlrpclib
import threading
import socket
import time

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

class SLICEAPI(object):
    """ API to perform queries to MySlice (using MySliceAPI aka TopHatAPI) to discover and provision resources for the experiment.
        
        A query is defined by the following tuple: {{{(action, method, timestamp, filters, params, fields, callback)}}}

        action:: an operation to run
        object:: the object on which the operation if performed (string)
        timestamp:: a temporal specification (planned for further use: cache, historical data, etc.)
        filters:: a set of predicates in the form (key, operation, value) used to filter the list of results to be returned (array of array)
        params:: a set of (key, value) parameters (dict)
        fields:: a set of fields to be returned by the function call (array of string)
        callback:: describes a return channel (planned for further use: callback, periodic or asynchronous requests, etc.)

        The returned value of the query is an array of dictionaries.

        #### More doc of SLICEAPI here ###
        
    """

    _expected_action = set(['Get', 'Update', 'Create', 'Delete', 'Execute'])

    _expected_object = set(['slice', 'resource', 'node', 'network'])

    # The same fields are used in the filters
    _expected_fields = set(['slice_hrn', 'lease.start_time', 'lease.duration', 'lease.urn', 'lease.granularity',
                            'lease.slice_id', 'resource.network', 'resource.type', 'resource.hrn', 'resource.hostname']) ### Complete with new fields ###

    _required_methods = set() ### todavia no se para que es ###

    def __init__(self, username=None, password=None, sessionkey=None, proxy=None,
            hostname = "demo.myslice.info",
            urlpattern = "https://%(hostname)s:7080"):
            localPeerName = "ple"):
        if sessionkey is not None:
            self.auth = dict(AuthMethod='session', session=sessionkey)
        elif username is not None and password is not None:
            self.auth = dict(AuthMethod='password', Username=username, AuthString=password)
        else:
            self.auth = dict(AuthMethod='anonymous')

        self._localPeerName = localPeerName
        self._url = urlpattern % {'hostname':hostname}

        ### Esto lo dejo pero todavia no se si se usaria un proxy ###
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
        ###

        self.threadlocal = threading.local()

    @property
    def api(self):
        # Cannot reuse same proxy in all threads, py2.7 is not threadsafe
        return xmlrpclib.ServerProxy(
            self._url ,
            transport = self._proxyTransport(),
            allow_none = True)

    # For multicall
    @property
    def mcapi(self):
        try:
            return self.threadlocal.mc
        except AttributeError:
            return self.api

    def test(self, slice_hrn):
        import warnings

        # validate XMLRPC server checking supported API calls
        # system.listMethods may be used to enumerate the methods implemented by the XML-RPC server. The system.listMethods
        # method requires no parameters. It returns an array of strings, each of which is the name of a method implemented by the server.

        methods = set(_retry(self.mcapi.system.listMethods)())
        # por ahora devuelve 
        # <Fault 8001: 'no such subHandler system'>

        if self._required_methods - methods:
            warnings.warn("Unsupported REQUIRED methods: %s" % ( ", ".join(sorted(self._required_methods - methods)), ) )
            return False
        if self._expected_action - methods:
            warnings.warn("Unsupported EXPECTED actions: %s" % ( ", ".join(sorted(self._expected_action - methods)), ) )

        try:
            # test authorization
            network_types = _retry(self.mcapi.Get)(self.auth, "network", [], {}, [])
        except (xmlrpclib.ProtocolError, xmlrpclib.Fault),e:
            warnings.warn(str(e))

        return True

    @property
    def network_types(self):
        try:
            return self._network_types
        except AttributeError:
            # network_types en plc devuelve ipv4, consulta rapida
            # la consulta siguiente devuelve los sfa deployment en la federacion
            # buscar simil network_types en myslice
            self._network_types = _retry(self.mcapi.Get)(self.auth, "network", [], {}, [])
            return self._network_types

# En planet lab las 3 autoridades que existen son PLE PLC y PLJ, como yo pertenezco a PLE la consulta devuelve los otros dos peers
#res = srv.GetPeers(auth, {}, ['shortname','peername','peer_id'])
#[{'shortname': 'PLJ', 'peer_id': 2, 'peername': 'plj'}, {'shortname': 'PLC', 'peer_id': 1, 'peername': 'PlanetLab'}]
# Sin filtros devuelve todo esto
# {'node_ids': [], 'key_ids': [], 'person_ids': [], 'peername': 'plj', 'peer_url': 'https://www.planet-lab.jp/PLCAPI/', 'slice_ids': [], 'hrn_root': 'plj', 'site_ids': [], 'peer_id': 2, 'shortname': 'PLJ'}
# El simil en myslice seria preguntar por networks, que devuelve
#[{'network_hrn': 'ple', 'network_name': 'PlanetLab Europe'}, {'network_hrn': 'tophat', 'network_name': 'TopHat'}, {'network_hrn': 'omf', 'network_name': 'NITOS'}, {'network_hrn': 'senslab', 'network_name': 'SensLab'}]
# Se pierde el id de la network, sirve para algo dsp?

    @property
    def peer_map(self):
        try:
            return self._peer_map
        except AttributeError:
            #peers = _retry(self.mcapi.GetPeers)(self.auth, {}, ['shortname','peername','peer_id'])
            peers = _retry(self.mcapi.Get)(self.auth, "network", {}, [])
            self._peer_map = dict(
                (peer['network_hrn'], peer['network_name'])
                for peer in peers
            )
            self._peer_map.update(
                (peer['network_name'], peer['network_hrn'])
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

###  myslice api q no anda!!! no aplica filtros, y con objeto 'node' da error ###
        return _retry(self.mcapi.Get)(self.auth, 'resource', [['hostname', '=', node]], {}, ['fcdistro', 'extensions', 'nodefamily', 'plain'])

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
            return _retry(self.mcapi.Get)(self.auth, 'resource', ['hostname', '=', nodeIdOrName, {}, *fieldstuple)
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
            return _retry(self.mcapi.Get)(self.auth, 'resource', filters, {}, *fieldstuple)

    def GetNodeTags(self, nodeTagId=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if nodeTagId is not None:
            return _retry(self.mcapi.Get)(self.auth, 'resource', ['', '=','nodeTagId'], {}, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.Get)(self.auth, 'resource', [['', '=','nodeTagId'], filters], {}, *fieldstuple)

    def GetSliceTags(self, sliceTagId=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if sliceTagId is not None:
            return _retry(self.mcapi.Get)(self.auth, 'slice', ['slice_hrn', '=', sliceTagId], {}, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.Get)(self.auth, 'slice', filters, {}, *fieldstuple)

    def GetInterfaces(self, interfaceIdOrIp=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if interfaceIdOrIp is not None:
            return _retry(self.mcapi.Get)(self.auth, 'resource', ['interfaces', '=', interfaceIdOrIp], {}, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.Get)(self.auth, 'resource', filters, {},['interfaces', *fieldstuple])

    def GetSlices(self, sliceIdOrName=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if sliceIdOrName is not None:
            return _retry(self.mcapi.Get)(self.auth, 'slice', ['slice_hrn', '=', sliceIdOrName, {}, *fieldstuple)
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
            return _retry(self.mcapi.Get)(self.auth, 'slice', filters, {}, *fieldstuple)

## Habria que hacer una query por leases, pero averiguar bien porq lease tambien es un metodo!

    def GetLeases(self, nodeIdOrName=None, fields=None, **kw):
        if fields is not None:
            fieldstuple = (fields,)
        else:
            fieldstuple = ()
        if nodeIdOrName is not None:
            return _retry(self.mcapi.Get)(self.auth, 'slice', [['node_id', '=', nodeIdOrName]], {}, ['lease.start_time', 'lease.duration', 'lease.urn', 'lease.granularity','lease.slice_id', *fieldstuple])
        else:
            filters = kw.pop('filters',{})
            filters.update(kw)
        return _retry(self.mcapi.Get)(self.auth, 'slice', filters, {}, ['lease.start_time', 'lease.duration', 'lease.urn', 'lease.granularity','lease.slice_id', *fieldstuple])        

    def UpdateSlice(self, sliceIdOrName, **kw):
        return _retry(self.mcapi.Update)(self.auth, 'slice', sliceIdOrName, kw)

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



#ret = srv.Get(auth, "slice", [["slice_hrn", '=', "ple.upmc.myslicedemo"]], {}, ["slice_hrn", "lease.start_time", "lease.duration", "lease.urn", "lease.granularity", "lease.slice_id", "resource.network", "resource.type", "resource.hrn", "resource.hostname"])
