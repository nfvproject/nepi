# -*- coding: utf-8 -*-

import copy
import logging
import sys
import weakref


class ConnectorsMapProxy(object):
    """ ConnectorMapProxy is used to admit expressions such as:
        box.c.connector1.connect(box2.c.connector2)
    """
    def __init__(self, owner):
        self._owner = weakref.ref(owner)
    
    def __getattr__(self, name):
        return self._owner()._connectors[name]

    def __setattr__(self, name, value):
        if name != "_owner":
            raise RuntimeError("Can't override attribute")
        super(ConnectorsMapProxy, self).__setattr__(name, value)


class ConnectionsProxy(object):
    """ ConnectionProxy is used to admit experssions such as:
        [connected_box1, connected_box2] = box.cn.connector1
    """
    def __init__(self, owner):
        self._owner = weakref.ref(owner)
    
    def __getattr__(self, name):
         return [ box for (box, name2) in self._owner()._connections[name] ]

    def __setattr__(self, name, value):
        if name != "_owner":
            raise RuntimeError("Can't override attribute")
        super(ConnectionsProxy, self).__setattr__(name, value)


class ConnectorsMap(object):
    def __init__(self):
        super(ConnectorsMap, self).__init__()
        self._connectors = dict()
        self._c = ConnectorsMapProxy(self)
        # connections -- list of all connected objects by connector
        self._connections = dict()
        self._cn = ConnectionsProxy(self)

    @property
    def connectors(self):
        return self._connectors.keys()

    @property
    def c(self):
        return self._c

    @property
    def cn(self):
        return self._cn

    def add_connector(self, connector):
        self._connectors[connector.name] = connector
        self._connections[connector.name] = list()
        connector.owner = self

    def clone_connectors(self, other):
        self._c = ConnectorsMapProxy(self)
        self._connectors = dict()
        self._cn = ConnectionsProxy(self)
        self._connections = dict()
        for conn in other._connectors.values():
            new = conn.clone()
            self.add_connector(new)

    @property
    def connections(self):
        connections = list()
        for connector_name in self._connections.keys():
            for (other_box, other_connector_name) in self._connections[connector_name]:
                connections.append((self, connector_name, other_box, other_connector_name))
        return connections

    def is_connected(self, connector, other_connector):
        return (other_connector.owner, other_connector.name) in self._connections[connector.name]

    def connect(self, connector, other_connector):
        cn = (other_connector.owner, other_connector.name)
        self._connections[connector.name].append(cn)

    def disconnect(self, connector, other_connector):
        cn = (other_connector.owner, other_connector.name)
        self._connections[connector.name].remove(cn)


class Connector(object):
    def __init__(self, name, help, max = -1, min = 0):
        super(Connector, self).__init__()
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
        # Box owner
        self._owner = None
        # name -- display name for the connector type
        self._name = name
        # help -- help text
        self._help = help
        # connection rules
        self._connection_rules = list()

        self._logger = logging.getLogger("nepi.design.connectors")

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

    def get_owner(self):
        # Gives back a strong-reference not a weak one
        return self._owner()

    def set_owner(self, owner):
        self._owner = weakref.ref(owner)

    owner = property(get_owner, set_owner)

    def list_connection_rules(self):
        return self._connection_rules

    def add_connection_rule(self, rule):
        self._connection_rules.append(rule)

    def is_full(self):
        """Return True if the connector has the maximum number of connections
        """
        return len(self.owner._connections[self.name]) == self.max

    def is_complete(self):
        """Return True if the connector has the minimum number of connections
        """
        return len(self.owner._connections[self.name]) >= self.min

    def is_connected(self, other_connector):
        return self.owner.is_connected(self, other_connector)

    def connect(self, other_connector, connect_other_side = True):
        if self.can_connect(other_connector):
            could_connect = True
            if connect_other_side:
                could_connect = other_connector.connect(self, False)
            if could_connect:
                self.owner.connect(self, other_connector)
                return True
        self._logger.error("could not connect guid(%d).c.%s with guid(%d).c.%s.", 
                    self.owner.guid, self.name, 
                    other_connector.owner.guid, other_connector.name)
        return False

    def disconnect(self, other_connector, disconnect_other_side = True):
        if (other_connector.owner, other_connector.name) in self.owner._connections[self.name]:
            could_disconnect = True
            if disconnect_other_side:
                could_disconnect = other_connector.disconnect(self, False)
            if could_disconnect:
                self.owner.disconnect(self, other_connector)
                return True
        self._logger.error("could not disconnect guid(%d).c.%s from guid(%d).c.%s .", 
                    connector.owner.guid, connector.name, 
                    other_connector.owner.guid, other_connector.name)
        return False

    def can_connect(self, other_connector):
        # can't connect with self
        if self.owner.guid == other_connector.owner.guid:
            self._logger.error("can't connect box with self %s %d.", 
                    self.owner.box_id, self.owner.guid)
            return False
        # can't add more connections
        if self.is_full():
            self._logger.error("Connector %s for %s %d is full.", 
                    self.name, self.owner.box_id, self.owner.guid)
            return False
        # is already connected
        if self.owner.is_connected(self, other_connector):
            return False
        # look over all connection rules
        for rule in self._connection_rules:
            if rule.can_connect(self.owner, self.name, other_connector.owner, 
                    other_connector.name):
                return True
        self._logger.error("No connection rule found for %s guid(%d).%s to %s guid(%d).%s. ", 
                    self.owner.box_id, self.owner.guid, self.name, 
                    other_connector.owner.box_id, other_connector.owner.guid, 
                    other_connector.name)
        return False

    def clone(self):
        return copy.copy(self)


class ConnectionRule(object):
    def __init__(self, box_id, connector_name, other_box_id, 
            other_connector_name, can_cross_controllers):
        super(ConnectionRule, self).__init__()
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

    def can_connect(self, box, connector_name, other_box, other_connector_name):
        if not box.controller:
             self._logger.error("No controller asociated to box %d, can not performe full validation.", box.guid)

        if not other_box.controller:
            self._logger.error("No controller asociated to box %d, can not perform full validation.", other_box.guid)

        if (self.can_cross_controllers or not box.controller or not other_box.controller or box.controller == other_box.controller) and \
                (not self.box_id or self.box_id == box.box_id) and \
                (not self.connector_name or self.connector_name == connector_name) and \
                (not self.other_box_id or self.other_box_id == other_box.box_id) and \
                (not self.other_connector_name or self.other_connector_name == other_connector_name):
            return True
        return False

