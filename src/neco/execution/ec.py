import logging
import os
import sys
import time

from neco.util import guid
from neco.execution.resource import ResourceFactory

class ExperimentController(object):
    def __init__(self, root_dir = "/tmp", loglevel = 'error'):
        super(ExperimentController, self).__init__()
        # root directory to store files
        self._root_dir = root_dir

        # generator of globally unique ids
        self._guid_generator = guid.GuidGenerator()
        
        # Resource managers
        self._resources = dict()

        # Groups of resources
        self._groups = dict()
       
        # Logging
        self._logger = logging.getLogger("neco.execution.ec")
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    def resource(self, guid):
        return self._resources.get(guid)

    def resources(self):
        return self._resources.keys()

    def release(self, group = None):
        # TODO
        pass

    def deploy(self, group = None):
        # TODO
        pass

    def register_resource(self, rtype, guid = None, creds = None):
        # Get next available guid
        guid = self._guid_generator.next(guid)
        
        # Instantiate RM
        rm = ResourceFactory.create(rtype, self, guid,creds)

        # Store RM
        self._resources[guid] = rm

        return guid

    def get_attributes(self, guid):
        rm = self._resources[guid]
        return rm.get_attributes()

    def get_filters(self, guid):
        rm = self._resources[guid]
        return rm.get_filters()

    def register_connection(self, guid1, guid2):
        rm1 = self._resources[guid1]
        rm2 = self._resources[guid2]

        rm1.connect(guid2)
        rm2.connect(guid1)

    def register_group(self, guids, gguid = None):
        gguid = self._guid_generator.next(gguid)
        self._groups[gguid] = guids

    def discover_resource(self, guid, filters):
        rm = self._resources[guid]
        return rm.discover(filters)

    def provision_resource(self, guid, filters):
        rm = self._resources[guid]
        return rm.provision(filters)

    def register_start(self, gguid1, time, after_status, gguid2):
        if isinstance(gguid1, int):
            gguid1 = list[gguid1]
        if isinstance(gguid2, int):
            gguid2 = list[gguid2]

        for guid1 in gguid1:
            for guid2 in gguid2:
                rm = self._resources(guid1)
                rm.start_after(time, after_status, guid2)

    def register_stop(self, gguid1, time, after_status, gguid2):
        if isinstance(gguid1, int):
            gguid1 = list[gguid1]
        if isinstance(gguid2, int):
            gguid2 = list[gguid2]

        for guid1 in gguid1:
            for guid2 in gguid2:
                rm = self._resources(guid1)
                rm.stop_after(time, after_status, guid2)

    def register_set(self, name, value, gguid1, time, after_status, gguid2):
        if isinstance(gguid1, int):
            gguid1 = list[gguid1]
        if isinstance(group2, int):
            gguid2 = list[gguid2]

        for guid1 in gguid1:
            for guid2 in gguid2:
                rm = self._resources(guid1)
                rm.set_after(name, value, time, after_status, guid2)

    def get(self, guid, name):
        rm = self._resources(guid)
        return rm.get(name)

    def set(self, guid, name, value):
        rm = self._resources(guid)
        return rm.set(name, value)

    def status(self, guid):
        rm = self._resources(guid)
        return rm.status()

    def stop(self, guid):
        rm = self._resources(guid)
        return rm.stop()

