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
# Author: Lucia Guevgeozian Odizzio <lucia.guevgeozian_odizzio@inria.fr>

import xmlrpclib
import hashlib
import threading


class MANIFOLDAPI(object):
    """
    API to query different data platforms as SFA, TopHat, OML Central Server,
    using Manifold Framework, the backend of MySlice.
    """
    def __init__(self, username, password, hostname, urlpattern): 
        
        self.auth_pwd = dict(AuthMethod='password', Username=username, 
            AuthString=password)
        self._url = urlpattern % {'hostname':hostname}
        self.lock = threading.Lock()
        self.auth = self.get_session_key()

    @property
    def api(self):
        return xmlrpclib.Server(self._url, allow_none = True)

    def get_session_key(self):
        """
        Retrieves the session key, in order to use the same session for 
        queries.
        """
        query = {'timestamp' : 'now', 'object': 'local:session',      
            'filters' : [], 'fields' : [], 'action' : 'create'}

        session = self.api.forward(self.auth_pwd, query)

        if not session['value']:
            msg = "Can not authenticate in Manifold API"
            raise RuntimeError, msg

        session_key = session['value'][0]['session']
        return dict(AuthMethod='session', session=session_key)

    def get_resource_info(self, filters=None, fields=None):
        """
        Create and execute the Manifold API Query to get the resources 
        according fields and filters.
        :param filters: resource's constraints for the experiment
        :type filters: dict
        :param fields: desire fields in the result of the query
        :type fields: list
        """
        query = {'action' : 'get', 'object' : 'resource'}

        if filters:
            filters = self._map_attr_to_resource_filters(filters)

            qfilters = list()
            for filtername, filtervalue in filters.iteritems():
                newfilter = [filtername, "==", filtervalue]
                qfilters.append(newfilter)
            
            query['filters'] = qfilters

        if fields:
            fields = self._check_valid_fields(fields)

            if fields:
                query['fields'] = fields

        return self.api.forward(self.auth, query)['value']
        
    def get_resource_urn(self, filters=None):
        """
        Retrieves the resources urn of the resources matching filters.
        """
        return self.get_resource_info(filters, 'urn')

    def get_slice_resources(self, slicename):
        """
        Retrieves resources attached to user's slice.
        return value: list of resources' urn
        """
        result = []
        query = {'action' : 'get', 'object' : 'resource', 
            'filters' : [['slice','==', slicename]],
            'fields' : ['urn']}

        with self.lock:
            value = self.api.forward(self.auth, query)['value']

        for resource in value:
            result.append(resource['urn'])
        
        return result

    def add_resource_to_slice(self, slicename, resource_urn):
        """
        Add resource to user's slice. The query needs to specify the new
        resource plus the previous resources already in the slice.
        """
        resources = self.get_slice_resources(slicename)
        resources.append(resource_urn) 

        urn_list = list()
        for r in resources:
            urn_dict = dict()
            urn_dict['urn'] = r
            urn_list.append(urn_dict)
            
        query = {'action' : 'update', 'object' : 'slice', 
            'filters' : [['slice_hrn','==', slicename]],
            'params' : {'resource' : urn_list}}
 
        with self.lock:
            self.api.forward(self.auth, query)

        resources = self.get_slice_resources(slicename)
        if resource_urn in resources:
            return True
        else:
            msg = "Failed while trying to add %s to slice" % resource_urn
            print msg
            # check how to do warning
            return False

    def remove_resource_from_slice(self, slicename, resource_urn):
        """
        Remove resource from user's slice. The query needs to specify the list
        of previous resources in the slice without the one to be remove.
        """
        resources = self.get_slice_resources(slicename)
        resources.remove(resource_urn)

        urn_list = list()
        for r in resources:
            urn_dict = dict()
            urn_dict['urn'] = r
            urn_list.append(urn_dict)

        query = {'action' : 'update', 'object' : 'slice',
            'filters' : [['slice_hrn','==', slicename]],
            'params' : {'resource' : urn_list}}

        with self.lock:
            self.api.forward(self.auth, query)

        resources = self.get_slice_resources(slicename)
        if resource_urn not in resources:
            return True
        else:
            msg = "Failed while trying to remove %s to slice" % resource_urn
            # check how to do warning
            return False

    def _get_metadata(self):
        """
        This method is useful to retrive metadata from different platforms
        in order to update fields and possible filters.
        """
        query = {'action' : 'get', 'object' : 'local:object', 
            'filters' : [['table','=','resource']]}
        
        res = self.api.forward(self.auth, query)

        valid_fields = list()
        for i in res['value'][0]['column']:
            valid_fields.append(i['name'])

        return valid_fields
        
    def _map_attr_to_resource_filters(self, filters):
        """
        Depending on the object used for the Manifold query, the filters and 
        fields can change its sintaxis. A resource field in a slice object
        query adds 'resource.' to the field. Other changes don't follow any 
        particular convention.
        """
        #TODO: find out useful filters
        attr_to_filter = {
            'hostname' : 'hostname',
            'longitude' : 'longitude',
            'latitude' : 'latitude',
            'network' : 'network',
            'component_id' : 'component_id'
        }

        mapped_filters = dict()
        for filtername, filtervalue in filters.iteritems():
            if attr_to_filter[filtername]:
                new_filtername = attr_to_filter[filtername]
                mapped_filters[new_filtername] = filtervalue
        
        return mapped_filters
         
    def _check_valid_fields(self, fields):
        """
        The fields can be a predefine set, define in the Manifold metadata.
        """
        valid_fields = self._get_metadata()

        if not isinstance(fields, list):
            fields = [fields]

        for field in fields:
            if field not in valid_fields:
                fields.remove(field)
                #self.warn(" Invalid Manifold field or filter ")
        
        return fields


class MANIFOLDAPIFactory(object):
    """
    API Factory to manage a map of MANIFOLDAPI instances as key-value pairs, it
    instanciate a single instance per key. The key represents the same SFA, 
    MF (ManiFold) credentials.
    """

    _lock = threading.Lock()
    _apis = dict()

    @classmethod
    def get_api(cls, username, password, 
            #hostname = "manifold.pl.sophia.inria.fr",
            hostname ="test.myslice.info",
            urlpattern = "http://%(hostname)s:7080"):
        """
        :param username: Manifold user (also used for MySlice web login)
        :type username: str
        :param password: Manifold password (also used for MySlice web login)
        :type password: str
        :param hostname: Hostname of the Manifold API to query SFA, TopHat, etc
        :type hostname: str
        :param urlpattern: Url of the Manifold API to query SFA, TopHat, etc
        :type urlpattern: str
        """

        if username and password:
            key = cls.make_key(username, password)
            with cls._lock:
                api = cls._apis.get(key)
    
                if not api:
                    api = MANIFOLDAPI(username, password, hostname, urlpattern)
                    cls._apis[key] = api

                return api

        return None

    @classmethod
    def make_key(cls, *args):
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()


