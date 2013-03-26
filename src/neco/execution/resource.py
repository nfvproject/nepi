import copy
import logging
import weakref

def clsinit(cls):
    cls._clsinit()
    return cls

# Decorator to invoke class initialization method
@clsinit
class Resource(object):
    _rtype = "Resource"
    _filters = None
    _attributes = None

    @classmethod
    def _register_filter(cls, attr):
        """ Resource subclasses will invoke this method to add a 
        filter attribute"""
        cls._filters[attr.name] = attr

    @classmethod
    def _register_attribute(cls, attr):
        """ Resource subclasses will invoke this method to add a 
        resource attribute"""
        cls._attributes[attr.name] = attr

    @classmethod
    def _register_filters(cls):
        """ Resource subclasses will invoke this method to add a 
        filter attribute"""
        pass

    @classmethod
    def _register_attributes(cls):
        """ Resource subclasses will invoke this method to add a 
        resource attribute"""
        pass

    @classmethod
    def _clsinit(cls):
        # static template for resource filters
        cls._filters = dict()
        cls._register_filters()

        # static template for resource attributes
        cls._attributes = dict()
        cls._register_attributes()

    @classmethod
    def rtype(cls):
        return cls._rtype

    @classmethod
    def get_filters(cls):
        return copy.deepcopy(cls._filters.values())

    @classmethod
    def get_attributes(cls):
        return copy.deepcopy(cls._attributes.values())

    def __init__(self, ec, guid):
        self._guid = guid
        self._ec = weakref.ref(ec)
        self._connections = set()
        # the resource instance gets a copy of all attributes
        # that can modify
        self._attrs = copy.deepcopy(self._attributes)

        # Logging
        self._logger = logging.getLogger("neco.execution.resource.Resource.%s" % 
            self.guid)

    @property
    def guid(self):
        return self._guid

    @property
    def ec(self):
        return self._ec()

    def connect(self, guid):
        if (self._validate_connection(guid)):
            self._connections.add(guid)

    @property
    def connections(self):
        return self._connections

    def discover(self, filters):
        pass

    def provision(self, filters):
        pass

    def set(self, name, value):
        attr = self._attrs[name]
        attr.value = value

    def get(self, name):
        attr = self._attrs[name]
        return attr.value

    def start_after(self, time, after_status, guid):
        pass

    def stop_after(self, time, after_status, guid):
        pass

    def set_after(self, name, value, time, after_status, guid):
        pass

    def next_step(self):
        pass

    def stop(self):
        pass

    def _validate_connection(self, guid):
        # TODO: Validate!
        return True

class ResourceFactory(object):
    _resource_types = dict()

    @classmethod
    def resource_types(cls):
        return cls._resource_types

    @classmethod
    def register_type(cls, rclass):
        cls._resource_types[rclass.rtype()] = rclass

    @classmethod
    def create(cls, rtype, ec, guid, creds):
        rclass = cls._resource_types[rtype]
        return rclass(ec, guid, creds)

