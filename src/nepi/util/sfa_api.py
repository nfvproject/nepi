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
#         Lucia Guevgeozian Odizzio <lucia.guevgeozian_odizzio@inria.fr>


import logging
import hashlib

from parser import sfa_sfav1
import subprocess
import warnings

import threading

class SFAApi(object):

    def __init__(self, aggregate = 'ple', slice_id = None, sfi_auth = None, sfi_user = None,
            sfi_registry = None, sfi_sm = None, timeout = None, private_key = None):
    
        self._resources = dict()
        self._reservable_resources = list()
        self._leases = dict()
        self._slice_tags = dict()
        self._slice_resources = set()
        self._slice_leases = set()
        self._aggregate = aggregate
        self._slice_hrn = slice_id
        # TODO: take into account Rspec version, SFA V1, GENI V2, GENI V3
        # For now is SFA V1 from PlanetLab and Nitos (wrong namespace)
        self._parser = sfa_sfav1.SFAResourcesParser(['ple', 'omf'])
        self._lock = threading.Lock()

        # Paremeters to contact the XMLRPC SFA service
        self._sfi_parameters = {'-a': sfi_auth, '-u': sfi_user,
                '-r': sfi_registry, '-s': sfi_sm, '-t': timeout,
                '-k': private_key}

        #self._logger = logging.getLogger('nepi.utils.sfiapi')
        self._fetch_resources_info()
        self._fetch_slice_info()

    def _sfi_command_options(self):
        command_options = " ".join("%s %s" % (k,v) for (k,v) in \
                self._sfi_parameters.iteritems() if v is not None)
        return command_options

    def _sfi_command_exec(self, command):
        args = command.split(" ")
        s = subprocess.Popen(args, stdout = subprocess.PIPE,
                stdin = subprocess.PIPE)
        xml, err = s.communicate()
        if err:
           raise RuntimeError("Command excecution problem, error: %s", err)
        return xml

    def _fetch_resources_info(self, resources = True):
        command_options = self._sfi_command_options()
        command = "sfi.py " + command_options + " resources -l all"
        try:
            xml = self._sfi_command_exec(command)
        except:
            #self._logger.error("Error in SFA responds: %s", xml)
            raise
        if resources:
            self._resources, self._leases = self._parser.resources_from_xml(xml, resources = True)
        else:
            self._leases = self._parser.resources_from_xml(xml)
        #self._update_reservable()
        return xml
    
    def _fetch_slice_info(self):
        command_options = self._sfi_command_options()
        command = "sfi.py " + command_options + " resources -l all"
        command = command + " " + self._slice_hrn
        try:
            xml = self._sfi_command_exec(command)
        except:
            #self._logger.error("Error in SFA responds: %s", xml)
            raise
        self._slice_resources, self._slice_leases, self._slice_tags = \
            self._parser.resources_from_xml(xml, sliver = True, resources = True)
        return xml

    def _update_reservable(self):
        for rid, r in self._resources.iteritems():
            if (r['resource_type'] == 'node' and r['exclusive'].upper() == 'TRUE') \
                 or (r['resource_type'] == 'channel'):
                self._reservable_resources.append(rid)


    def discover_resources(self, resourceId=None, fields=[], **kwargs):
        result = dict()
        resources = self._resources

        if resourceId is not None:
            resource_ids = resourceId
            if not isinstance(resource_ids, list):
                resource_ids = [resource_ids]
            resources = self._filter_by_resourceId(resources, resource_ids)
        else:
            for filter, value in kwargs.items():
                resources = self._filter_by_filter(resources, filter, value)
        if not fields:
            return resources
        else:
            for k, info in resources.iteritems():
                info = self._extract_fields(info, fields)
                result[k] = info
            return result
                
    def _filter_by_resourceId(self, resources, resource_ids):
        return dict((k, resources[k]) for k in resource_ids if k in resources)

    def _filter_by_filter(self, resources, filter, value):
        d = dict()
        for k in resources.keys():
            if filter in resources[k]:
                if resources[k][filter] == value:
                    d[k] = resources[k]
        return d
               
    def _extract_fields(self, info, fields):
        return dict((k, info[k]) for k in fields if k in info)

    def discover_fields(self):
        resources = self._resources
        fields = []
        for k, data in resources.iteritems():
            for field in data:
                if field not in fields:
                    fields.append(field)
        return fields

    def discover_leases(self, resourceId=None):
        leases = self._leases

        if resourceId is not None:
            resource_ids = resourceId
            if not isinstance(resourceId, list):
                resource_ids = [resource_ids]
            leases = self._filterbyresourceId(leases, resource_ids)
        return leases

    def find_resources(self, leases, resources, rtype, quantity, start_time, duration, slot):
        result = dict()
        if rtype not in ['node', 'channel']:
            raise RuntimeError("Unknown type")

        finish_time = start_time + duration * slot

        leases_resources = dict()
        reservable_resources = dict()
        for lid, lease in leases.iteritems():
            if lease[0]['type'] == rtype:
                leases_resources.update({lid: lease})
        #print leases_resources
        for rid, resource in resources.iteritems():
            if rtype == 'node' and (resource['type'] == 'node' and resource['exclusive'].upper() == 'TRUE'):
                reservable_resources.update({rid: resource})
            elif rtype == 'channel':
                reservable_resources.update({rid: resource})
            #if resource['type'] == 'rtype' and resources['exclusive'].upper() == 'TRUE':\
            # (in case adding exclusive tag to channels)

        free_resources = list(set(reservable_resources.keys()) - set(leases_resources.keys()))
    
        if len(free_resources) >= quantity:
            free_resources = free_resources[:quantity]
            for rid, resource in resources.iteritems():
                if rid in free_resources:
                    result[rid] = resource
            return result
        else:
            maybe_free = []
            new_quan = quantity - len(free_resources)
            print new_quan

            for lid, lease in leases_resources.iteritems():
                for l in lease:
                    st = int(l['start_time'])
                    ft = st + int(l['duration']) * slot
                    if (st <= finish_time <= ft) or (st <= start_time <= ft):
                        if lid in maybe_free:
                            maybe_free.remove(lid)
                        break
                    else:
                        if lid not in maybe_free:
                            maybe_free.append(lid)
                if len(maybe_free) >= new_quan:
                    free_resources = [free_resources, maybe_free]
                    free_resources = sum(free_resources, [])
                    for rid, resource in resources.iteritems():
                        if rid in free_resources:
                            result[rid] = resource
                        return result
                    #return free_resources
            warnings.warn("There aren't enough nodes")

                                 
    def provision_resource(self, new_resource, start_time = None, duration = None):
        import os, tempfile
        with self._lock:
            xml = self._fetch_slice_info()
            new_xml = self._parser.create_reservation_xml(xml, self._slice_hrn,\
            new_resource, start_time, duration, self._aggregate)
            fh, fname = tempfile.mkstemp()
            print fname
            os.write(fh, new_xml)
            os.close(fh)
            try:
                command_options = self._sfi_command_options()
                command = "sfi.py " + command_options + " create %s %s" % (self._slice_hrn, fname)
                out = self._sfi_command_exec(command)
            except:
                raise
        xml = self._fetch_slice_info()
        return self._parser.verify_reservation_xml(xml, self._slice_hrn, new_resource, start_time,\
                duration, self._aggregate)

    def release_resource(self, resource, start_time = None, duration = None):
        import os, tempfile
        with self._lock:
            xml = self._fetch_slice_info()
            new_xml = self._parser.release_reservation_xml(xml, self._slice_hrn, resource,\
            start_time, duration, self._aggregate)
            fh, fname = tempfile.mkstemp()
            print fname
            os.write(fh, new_xml)
            os.close(fh)
            try:
                command_options = self._sfi_command_options()
                command = "sfi.py " + command_options + " create %s %s" % (self._slice_hrn, fname)
                out = self._sfi_command_exec(command)
            except:
                raise
        xml = self._fetch_slice_info()
        return not self._parser.verify_reservation_xml(xml, self._slice_hrn, resource, start_time,\
            duration, self._aggregate)


class SFAApiFactory(object):
    lock = threading.Lock()
    _apis = dict()

    @classmethod
    def get_api(slice_id = None, sfi_auth = None, sfi_user = None,
            sfi_registry = None, sfi_sm = None, timeout = None, private_key = None):

        key = cls.make_key(aggregate = 'ple', slice_id, sfi_auth, sfi_user, sfi_registry, sfi_sm,
            timeout, private_key)
        api = cls._apis.get(key)
        cls.lock.acquire()
        api._fetch_resources_info(resources = False)
        api._fetch_slice_info()
        cls.lock.release()

        if not api:
            api = SFAApi(slice_id = None, sfi_auth = None, sfi_user = None,
            sfi_registry = None, sfi_sm = None, timeout = None, private_key = None)
            cls._apis[key] = api

        return api

    @classmethod
    def make_key(cls, *args):
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()

