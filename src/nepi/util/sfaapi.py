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
    API for quering the SFA service. It uses Sfi class from the tool sfi client.
    """
    def __init__(self, sfi_user, sfi_auth, sfi_registry, sfi_sm, private_key, ec,
        batch, rtype, timeout):

        self._blacklist = set()
        self._reserved = set()
        self._resources_cache = None
        self._already_cached = False
        self._ec = ec 
        self.apis = 1

        if batch:
            self._testbed_res = rtype
            self._count = 0
            self._total = self._get_total_res()
            self._slice_resources_batch = list()

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
        """
        Initialize the blacklist with previous nodes blacklisted, in 
        previous runs.
        """
        nepi_home = os.path.join(os.path.expanduser("~"), ".nepi")
        plblacklist_file = os.path.join(nepi_home, "plblacklist.txt")
        with open(plblacklist_file, 'r') as f:
            hosts_tobl = f.read().splitlines()
            if hosts_tobl:
                for host in hosts_tobl:
                    self._blacklist.add(host)

    def _get_total_res(self):
        """
        Get the total amount of resources instanciated using this API,
        to be able to add them using the same Allocate and Provision
        call at once. Specially for Wilabt testbed that doesn't allow 
        to add slivers after the slice already has some.
        """
        rms = list()
        res_gids = self._ec.resources
        for gid in res_gids:
            rm = self._ec.get_resource(gid)
            if self._testbed_res.lower() in rm._rtype.lower():
                rms.append(rm)
        return rms

    def _sfi_exec_method(self, command, slicename=None, rspec=None, urn=None, action=None):
        """
        Execute sfi method, which correspond to SFA call. It can be the following
        calls: Describe, Delete, Allocate, Provision, ListResources.
        """
        if command in ['describe', 'delete', 'allocate', 'provision', 'action']:
            if not slicename:
                raise TypeError("The slice hrn is expected for this method %s" % command)
            if command == 'allocate' and not rspec:
                raise TypeError("RSpec is expected for this method %s" % command)
            
            if command == 'allocate':
                args_list = [slicename, rspec]
            else:
                args_list = [slicename]
            if command != 'delete':
                args_list = args_list + ['-o', '/tmp/rspec_output']
            if command == 'action':
                args_list = [slicename, action]

        elif command == 'resources':
            args_list = ['-o', '/tmp/rspec_output']

        else: raise TypeError("Sfi method not supported")

        self.api.command = command
        self.api.command_parser = self.api.create_parser_command(self.api.command)
        (command_options, command_args) = self.api.command_parser.parse_args(args_list)
        self.api.command_options = command_options
        self.api.read_config()
        self.api.bootstrap()

        try:
            os.remove("/tmp/rspec_output.rspec")
        except OSError:
            self._log.debug("Couldn't remove temporary output file for RSpec or it doesn't exist")

        try:
            self.api.dispatch(command, command_options, command_args)
            with open("/tmp/rspec_output.rspec", "r") as result_file:
                result = result_file.read()
                return result
        except:
            self._log.debug(" Couldn't retrive rspec output information from method %s " % command)
            return None

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
            self._log.debug("Fail to describe resources for slice %s, slice may be empty" % slicename)

        if rspec_slice is not None:
            result = self.rspec_proc.parse_sfa_rspec(rspec_slice)
            return result
        else:
            return {'resource':[],'lease':[]}


    def add_resource_to_slice(self, slicename, resource_hrn, leases=None):
        """
        Get the list of resources' urn, build the rspec string and call the allocate 
        and provision method.
        """
        resources_hrn_new = list()
        resource_parts = resource_hrn.split('.')
        resource_hrn = '.'.join(resource_parts[:2]) + '.' + '\\.'.join(resource_parts[2:])
        resources_hrn_new.append(resource_hrn)

        with self.lock_slice:
            rspec_slice = self._sfi_exec_method('describe', slicename)
            if rspec_slice is not None:
                slice_resources = self.rspec_proc.parse_sfa_rspec(rspec_slice)['resource']
            else: slice_resources = []
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

            # ALLOCATE
            try:
                self._log.debug("Allocating resources in slice %s" % slicename)
                out = self._sfi_exec_method('allocate', slicename, "/tmp/rspec_input.rspec")
            except:
                raise RuntimeError("Fail to allocate resource for slice %s" % slicename)

            if out is not None:
                # PROVISION
                try:
                    self._log.debug("Provisioning resources in slice %s" % slicename)
                    self._sfi_exec_method('provision', slicename) 
                except:
                    raise RuntimeError("Fail to provision resource for slice %s" % slicename)
                return True

    def add_resource_to_slice_batch(self, slicename, resource_hrn, properties=None, leases=None):
        """
        Method to add all resources together to the slice. Previous deletion of slivers.
        Specially used for wilabt that doesn't allow to add more resources to the slice
        after some resources are added. Every sliver have to be deleted and the batch 
        has to be added at once.
        """
        self._count += 1
        self._slice_resources_batch.append(resource_hrn)
        resources_hrn_new = list()
        if self._count == len(self._total):
            for resource_hrn in self._slice_resources_batch:
                resource_parts = resource_hrn.split('.')
                resource_hrn = '.'.join(resource_parts[:2]) + '.' + '\\.'.join(resource_parts[2:])
                resources_hrn_new.append(resource_hrn)
            with self.lock_slice:
                self._sfi_exec_method('delete', slicename)
                # Re implementing urn from hrn because the library sfa-common doesn't work for wilabt
                resources_urn = self._get_urn(resources_hrn_new)
                rspec = self.rspec_proc.build_sfa_rspec(slicename, resources_urn, properties, leases)
                f = open("/tmp/rspec_input.rspec", "w")
                f.truncate(0)
                f.write(rspec)
                f.close()

                if not os.path.getsize("/tmp/rspec_input.rspec") > 0:
                    raise RuntimeError("Fail to create rspec file to allocate resources in slice %s" % slicename)

                # ALLOCATE    
                try:
                    self._log.debug("Allocating resources in slice %s" % slicename)
                    out = self._sfi_exec_method('allocate', slicename, "/tmp/rspec_input.rspec")
                except:
                    raise RuntimeError("Fail to allocate resource for slice %s" % slicename)

                if out is not None:
                    # PROVISION
                    try:
                        self._log.debug("Provisioning resources in slice %s" % slicename)
                        self._sfi_exec_method('provision', slicename)
                        self._sfi_exec_method('action', slicename=slicename, action='geni_start')
                    except:
                        raise RuntimeError("Fail to provision resource for slice %s" % slicename)
                    return True
                else:
                    raise RuntimeError("Fail to allocate resources for slice %s" % slicename)
    
        else:
            self._log.debug(" Waiting for more nodes to add the batch to the slice ")

    def _get_urn(self, resources_hrn):
        """
        Get urn from hrn.
        """
        resources_urn = list()
        for hrn in resources_hrn:
            hrn = hrn.replace("\\", "").split('.')
            node = hrn.pop()
            auth = '.'.join(hrn)
            urn = ['urn:publicid:IDN+', auth, '+node+', node]
            urn = ''.join(urn)
            resources_urn.append(urn)
        return resources_urn

    def remove_resource_from_slice(self, slicename, resource_hrn, leases=None):
        """
        Remove slivers from slice. Currently sfi doesn't support removing particular
        slivers.
        """
        resource_urn = self._get_resources_urn([resource_hrn]).pop()
        with self.lock_slice:
            try:
                self._sfi_exec_method('delete', slicename, urn=resource_urn)
            except:
                raise RuntimeError("Fail to delete resource for slice %s" % slicename)
            return True

    def remove_all_from_slice(self, slicename):
        """
        De-allocate and de-provision all slivers of the named slice.
        Currently sfi doesn't support removing particular
        slivers, so this method works only for removing every sliver. Setting the
        resource_hrn parameter is not necessary.
        """
        with self.lock_slice:
            try:
                self._sfi_exec_method('delete', slicename)
            except:
                raise RuntimeError("Fail to delete slivers for slice %s" % slicename)
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
        """
        Adding resource_hrn to blacklist, and taking 
        the resource from the reserved list.
        """
        with self.lock_blist:
            self._blacklist.add(resource_hrn)
        with self.lock_resv:
            if resource_hrn in self._reserved:
                self._reserved.remove(resource_hrn)

    def blacklisted(self, resource_hrn):
        """
        Check if the resource is in the blacklist. 
        """
        with self.lock_blist:
            if resource_hrn in self._blacklist:
                return True
        return False

    def reserve_resource(self, resource_hrn):
        """
        Add resource to the reserved list.
        """
        self._reserved.add(resource_hrn)

    def reserved(self, resource_hrn):
        """
        Check that the resource in not reserved.
        """
        with self.lock_resv:
            if resource_hrn in self._reserved:
                return True
            else:
                self.reserve_resource(resource_hrn)
                return False

    def release(self):
        """
        Remove hosts from the reserved and blacklist lists, and in case
        the persist attribute is set, it saves the blacklisted hosts
        in the blacklist file.
        """
        self.apis -= 1
        if self.apis == 0:
            blacklist = self._blacklist
            self._blacklist = set()
            self._reserved = set()
#            if self._ecobj.get_global('PlanetlabSfaNode', 'persist_blacklist'):
#                if blacklist:
#                    to_blacklist = list()
#                    hostnames = self.get_nodes(list(blacklist), ['hostname'])
#                    for hostname in hostnames:
#                        to_blacklist.append(hostname['hostname'])
#
#                    nepi_home = os.path.join(os.path.expanduser("~"), ".nepi")
#                    plblacklist_file = os.path.join(nepi_home, "plblacklist.txt")
#
#                    with open(plblacklist_file, 'w') as f:
#                        for host in to_blacklist:
#                            f.write("%s\n" % host)
#


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
            batch = False, rtype = None, timeout = None):

        if sfi_user and sfi_sm:
            key = cls.make_key(sfi_user, sfi_sm)
            with cls._lock:
                api = cls._apis.get(key)

                if not api:
                    api = SFAAPI(sfi_user, sfi_auth, sfi_registry, sfi_sm, private_key,
                        ec, batch, rtype, timeout)
                    cls._apis[key] = api
                else:
                    api.apis += 1

                return api

        return None

    @classmethod
    def make_key(cls, *args):
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()

