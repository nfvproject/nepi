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

import threading
import hashlib
import re
import os

from nepi.util.logger import Logger

try:
    from sfa.client.sfi import Sfi
    from sfa.util.xrn import hrn_to_urn
except ImportError:
    log = Logger("SFA API")
    log.debug("Packages sfa-common or sfa-client not installed.\
         Could not import sfa.client.sfi or sfa.util.xrn")

from nepi.util.sfarspec_proc import SfaRSpecProcessing

class SFAAPI(object):
    """
    API for quering the SFA service.
    """
    def __init__(self, sfi_user, sfi_auth, sfi_registry, sfi_sm, private_key, ec,
        timeout):

        self._blacklist = set()
        self._reserved = set()
        self._resources_cache = None
        self._already_cached = False
        self._log = Logger("SFA API")
        self.api = Sfi()
        self.rspec_proc = SfaRSpecProcessing()
        self.lock_slice = threading.Lock()
        self.lock_blist = threading.Lock()
        self.lock_resv = threading.Lock()

        self.api.options.timeout = timeout
        self.api.options.raw = None
        self.api.options.user = sfi_user
        self.api.options.auth = sfi_auth
        self.api.options.registry = sfi_registry
        self.api.options.sm = sfi_sm
        self.api.options.user_private_key = private_key

        # Load blacklist from file
        if ec.get_global('PlanetlabNode', 'persist_blacklist'):
            self._set_blacklist()

    def _set_blacklist(self):
        nepi_home = os.path.join(os.path.expanduser("~"), ".nepi")
        plblacklist_file = os.path.join(nepi_home, "plblacklist.txt")
        with open(plblacklist_file, 'r') as f:
            hosts_tobl = f.read().splitlines()
            if hosts_tobl:
                for host in hosts_tobl:
                    self._blacklist.add(host)

    def _sfi_exec_method(self, command, slicename=None, rspec=None, urn=None):
        """
        Execute sfi method.
        """
        if command in ['describe', 'delete', 'allocate', 'provision']:
            if not slicename:
                raise TypeError("The slice hrn is expected for this method %s" % command)
            if command == 'allocate' and not rspec:
                raise TypeError("RSpec is expected for this method %s" % command)
            
            if command == 'allocate':
                args_list = [slicename, rspec]
            elif command == 'delete':
                args_list = [slicename, urn]
            else: args_list = [slicename, '-o', '/tmp/rspec_output']

        elif command == 'resources':
            args_list = ['-o', '/tmp/rspec_output']

        else: raise TypeError("Sfi method not supported")

        self.api.command = command
        self.api.command_parser = self.api.create_parser_command(self.api.command)
        (command_options, command_args) = self.api.command_parser.parse_args(args_list)
        #print "1 %s" % command_options.info
        #command_options.info = ""
        #print "2 %s" % command_options.info
        self.api.command_options = command_options
        self.api.read_config()
        self.api.bootstrap()

        self.api.dispatch(command, command_options, command_args)
        with open("/tmp/rspec_output.rspec", "r") as result_file:
            result = result_file.read()
        return result

    def get_resources_info(self):
        """
        Get all resources and its attributes from aggregate.
        """
        try:
            rspec_slice = self._sfi_exec_method('resources')
        except:
            raise RuntimeError("Fail to list resources")
   
        self._resources_cache = self.rspec_proc.parse_sfa_rspec(rspec_slice)
        self._already_cached = True
        return self._resources_cache

    def get_resources_hrn(self, resources=None):
        """
        Get list of resources hrn, without the resource info.
        """
        if not resources:
            if not self._already_cached:
                resources = self.get_resources_info()['resource']
            else:
                resources = self._resources_cache['resource']

        component_tohrn = dict()
        for resource in resources:
            hrn = resource['hrn'].replace('\\', '')
            component_tohrn[resource['component_name']] = hrn

        return component_tohrn
            
    def get_slice_resources(self, slicename):
        """
        Get resources and info from slice.
        """
        try:
            with self.lock_slice:
                rspec_slice = self._sfi_exec_method('describe', slicename)
        except:
            raise RuntimeError("Fail to describe resource for slice %s" % slicename)

        result = self.rspec_proc.parse_sfa_rspec(rspec_slice)
        return result


    def add_resource_to_slice(self, slicename, resource_hrn, leases=None):
        """
        Get the list of resources' urn, build the rspec string and call the allocate 
        and provision method.
        """
        resources_hrn_new = list()
        resource_parts = resource_hrn.split('.')
        resource_hrn = '.'.join(resource_parts[:2]) + '.' + '\\.'.join(resource_parts[2:])
        resources_hrn_new.append(resource_hrn)

        slice_resources = self.get_slice_resources(slicename)['resource']

        with self.lock_slice:
            if slice_resources:
                slice_resources_hrn = self.get_resources_hrn(slice_resources)
                for s_hrn_key, s_hrn_value in slice_resources_hrn.iteritems():
                    s_parts = s_hrn_value.split('.')
                    s_hrn = '.'.join(s_parts[:2]) + '.' + '\\.'.join(s_parts[2:])
                    resources_hrn_new.append(s_hrn)

            resources_urn = self._get_resources_urn(resources_hrn_new)
            rspec = self.rspec_proc.build_sfa_rspec(slicename, resources_urn, leases)
            f = open("/tmp/rspec_input.rspec", "w")
            f.truncate(0)
            f.write(rspec)
            f.close()
            
            if not os.path.getsize("/tmp/rspec_input.rspec") > 0:
                raise RuntimeError("Fail to create rspec file to allocate resource in slice %s" % slicename)

            try:
                self._sfi_exec_method('allocate', slicename, "/tmp/rspec_input.rspec")
            except:
                raise RuntimeError("Fail to allocate resource for slice %s" % slicename)            
            try:
                self._sfi_exec_method('provision', slicename) 
            except:
                raise RuntimeError("Fail to provision resource for slice %s" % slicename)
            return True

    def remove_resource_from_slice(self, slicename, resource_hrn, leases=None):
        """
        Get the list of resources' urn, build the rspec string and call the allocate 
        and provision method.
        """
        resource_urn = self._get_resources_urn([resource_hrn]).pop()
        try:
            self._sfi_exec_method('delete', slicename, urn=resource_urn)
        except:
            raise RuntimeError("Fail to delete resource for slice %s" % slicename)
        return True


    def _get_resources_urn(self, resources_hrn):
        """
        Builds list of resources' urn based on hrn.
        """
        resources_urn = list()

        for resource in resources_hrn:
            resources_urn.append(hrn_to_urn(resource, 'node'))
            
        return resources_urn

    def blacklist_resource(self, resource_hrn):
        with self.lock_blist:
            self._blacklist.add(resource_hrn)
        with self.lock_resv:
            if resource_hrn in self._reserved:
                self._reserved.remove(resource_hrn)

    def blacklisted(self, resource_hrn):
        with self.lock_blist:
            if resource_hrn in self._blacklist:
                return True
        return False

    def reserve_resource(self, resource_hrn):
        self._reserved.add(resource_hrn)

    def reserved(self, resource_hrn):
        with self.lock_resv:
            if resource_hrn in self._reserved:
                return True
            else:
                self.reserve_resource(resource_hrn)
                return False

class SFAAPIFactory(object):
    """
    API Factory to manage a map of SFAAPI instances as key-value pairs, it
    instanciate a single instance per key. The key represents the same SFA, 
    credentials.
    """

    _lock = threading.Lock()
    _apis = dict()

   
    @classmethod
    def get_api(cls, sfi_user, sfi_auth, sfi_registry, sfi_sm, private_key, ec,
            timeout = None):

        if sfi_user and sfi_sm:
            key = cls.make_key(sfi_user, sfi_sm)
            with cls._lock:
                api = cls._apis.get(key)

                if not api:
                    api = SFAAPI(sfi_user, sfi_auth, sfi_registry, sfi_sm, private_key,
                        ec, timeout)
                    cls._apis[key] = api

                return api

        return None

    @classmethod
    def make_key(cls, *args):
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()

