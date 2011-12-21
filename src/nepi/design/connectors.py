# -*- coding: utf-8 -*-

"""
Common connector class
"""

import sys

class Connector(object):
    def __init__(self, box_id, name, help, max = -1, min = 0):
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
        # Box typed identified
        self._box_id = box_id
        # name -- display name for the connector type
        self._name = name
        # help -- help text
        self._help = help
        # connection rules
        self._connection_rules = list()

        self._logger = logging.getLogger("nepi.design.connectors")

    @property
    def box_id(self):
        return self._box_id

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
    
    def list_connection_rules(self):
        return self._connection_rules

    def add_connection_rule(self, rule):
        self._connection_rules.append(rule)

    def is_full(self, box):
        """Return True if the connector has the maximum number of connections
        """
        return len(box.connections) == self.connector_type.max

    def is_complete(self, box):
        """Return True if the connector has the minimum number of connections
        """
        return len(box.connections) >= self.connector_type.min

    def can_connect(self, box, connector_name, other_box, connector_name):
        # can't connect with self
        if box.guid == other_box.guid:
            return False
        if self.is_full(box):
            return False
        if box.is_connected(connector_name, other_box, other_connector_name):
            return False
        # look over all connection rules
        for rule in self._connection_rules:
            if rule.can_connect(box, connector_box, other_box, other_connection_name):
                return True
        self._logger.warn("Connector.can_connect(): No connection rule found for %d %s to %d %s.", 
                    box.guid, connector_name, other_box.guid, other_connector_name)
        return False


class ConnectionRule(object):
    def __init__(self, box_id, connector_name, other_box_id, 
            other_connector_name, can_cross_controllers):
        super(Connector, self).__init__()
        self._box_id = box_id
        self._connector_name = connector_name
        self._other_box_id = other_box_id
        self._other_connector_name = other_connector_name
        self._can_cross_controllers = can_cross_controllers
        
        self._logger = logging.getLogger("nepi.design.connectors")

    @property
    def box_id(self):
        return self._box_id

    @property
    def other_box_id(self):
        return self._other_box_id

    @property
    def connector_name(self):
        return self._connector_name

    @property
    def other_connector_name(self):
        return self._other_connector_name

    @property
    def can_cross_controllers(self):
        return self._can_cross_controllers

    def can_connect(self, box, connector_box, other_box, other_connection_name):
        if not box.controller:
            self._logger.warn("ConnectionRule.can_connect(): no controller asociated to box %d.", 
                    box.guid)
            return False

        if not other_box.controller:
            self._logger.warn("ConnectionRule.can_connect(): no controller asociated to box %d.", 
                    other_box.guid)
            return False

        if (self.can_cross_controllers or box.controller == other_box.controller) and /
            (not self.box_id or self.box_id == box.box_id) and /
            (not self.connector_name or self.connector_name == box.connector_name) and /
            (not self.other_box_id or self.other_box_id == other_box.box_id) and /
            (not self.other_connector_name or self.other_connector_name == other_box.connector_name):
                return True
        return False

