#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common connector base classes
"""

import sys

class ConnectorTypeBase(object):
    def __init__(self, testbed_id, factory_id, name, max = -1, min = 0):
        super(ConnectorTypeBase, self).__init__()
        if max == -1:
            max = sys.maxint
        elif max <= 0:
            raise RuntimeError, "The maximum number of connections allowed need to be more than 0"
        if min < 0:
            raise RuntimeError, "The minimum number of connections allowed needs to be at least 0"
        # connector_type_id -- univoquely identifies a connector type 
        # across testbeds
        self._connector_type_id = self.make_connector_type_id(
            testbed_id, factory_id, name)
        # name -- display name for the connector type
        self._name = name
        # max -- maximum amount of connections that this type support, 
        # -1 for no limit
        self._max = max
        # min -- minimum amount of connections required by this type of connector
        self._min = min

    @property
    def connector_type_id(self):
        return self._connector_type_id

    @property
    def name(self):
        return self._name

    @property
    def max(self):
        return self._max

    @property
    def min(self):
        return self._min
    
    @staticmethod
    def make_connector_type_id(testbed_id, factory_id, name):
        testbed_id = testbed_id.lower() if testbed_id else None
        factory_id = factory_id.lower() if factory_id else None
        name = name.lower() if name else None
        return (testbed_id, factory_id, name)
    
    @staticmethod
    def _type_resolution_order(connector_type_id):
        testbed_id, factory_id, name = connector_type_id
        
        # the key is always a candidate
        yield connector_type_id
        
        # Try wildcard combinations
        if (testbed_id, None, name) != connector_type_id:
            yield (testbed_id, None, name)
        if (None, factory_id, name) != connector_type_id:
            yield (None, factory_id, name)
        if (None, None, name) != connector_type_id:
            yield (None, None, name)


