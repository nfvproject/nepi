# -*- coding: utf-8 -*-

"""
Common connector class
"""

import sys

class ConnectorType(object):
    def __init__(self, testbed_id, factory_id, name, help, max = -1, min = 0):
        super(ConnectorType, self).__init__()

        if max == -1:
            max = sys.maxint
        elif max <= 0:
            raise RuntimeError, "The maximum number of connections allowed need to be more than 0"
        if min < 0:
            raise RuntimeError, "The minimum number of connections allowed needs to be at least 0"
        # max -- maximum amount of connections that this type support, 
        # -1 for no limit
        self._max = max
        # min -- minimum amount of connections required by this type of connector
        self._min = min
       
        # connector_type_id -- univoquely identifies a connector type 
        # across testbeds
        self._connector_type_id = self.make_connector_type_id(
            testbed_id, factory_id, name)
        
        # name -- display name for the connector type
        self._name = name

        # help -- help text
        self._help = help

        # from_connections -- connections where the other connector is the "From"
        # to_connections -- connections where the other connector is the "To"
        # keys in the dictionary correspond to the 
        # connector_type_id for possible connections. The value is a tuple:
        # (can_cross, connect)
        # can_cross: indicates if the connection is allowed accros different
        #    testbed instances
        # code: is the connection function to be invoked when the elements
        #    are connected
        self._from_connections = dict()
        self._to_connections = dict()

    def __str__(self):
        return "ConnectorType%r" % (self._connector_type_id,)

    @property
    def connector_type_id(self):
        return self._connector_type_id

    @property
    def name(self):
        return self._name

    @property
    def help(self):
        return self._help

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

    def add_from_connection(self, testbed_id, factory_id, name, can_cross, 
            init_code, compl_code):
        type_id = self.make_connector_type_id(testbed_id, factory_id, name)
        self._from_connections[type_id] = (can_cross, init_code, compl_code)

    def add_to_connection(self, testbed_id, factory_id, name, can_cross, 
            init_code, compl_code):
        type_id = self.make_connector_type_id(testbed_id, factory_id, name)
        self._to_connections[type_id] = (can_cross, init_code, compl_code)

    def connect_to_init_code(self, testbed_id, factory_id, name, must_cross):
        return self._connect_to_code(testbed_id, factory_id, name, must_cross)[0]

    def connect_to_compl_code(self, testbed_id, factory_id, name, must_cross):
        return self._connect_to_code(testbed_id, factory_id, name, must_cross)[1]

    def _connect_to_code(self, testbed_id, factory_id, name,
            must_cross):
        connector_type_id = self.make_connector_type_id(testbed_id, factory_id, name)
        for lookup_type_id in self._type_resolution_order(connector_type_id):
            if lookup_type_id in self._to_connections:
                (can_cross, init_code, compl_code) = self._to_connections[lookup_type_id]
                if must_cross == can_cross:
                    return (init_code, compl_code)
        else:
            return (False, False)
 
    def can_connect(self, testbed_id, factory_id, name, must_cross):
        connector_type_id = self.make_connector_type_id(testbed_id, factory_id, name)
        for lookup_type_id in self._type_resolution_order(connector_type_id):
            if lookup_type_id in self._from_connections:
                (can_cross, init_code, compl_code) = self._from_connections[lookup_type_id]
            elif lookup_type_id in self._to_connections:
                (can_cross, init_code, compl_code) = self._to_connections[lookup_type_id]
            else:
                # keep trying
                continue
            if must_cross == can_cross:
                return True
        else:
            return False

