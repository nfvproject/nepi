import copy
import logging
import weakref

class Resource(object):
    # static template for resource filters
    _filters = dict()
    
    # static template for resource attributes
    _attributes = dict()

    @classmethod
    def _register_filter(cls, attr):
        """ Resource subclasses will invoke this method to add a 
        filter attribute"""
        cls._filters[attr.name] = attr

    @classmethod
    def _register_attributes(cls, attr):
        """ Resource subclasses will invoke this method to add a 
        resource attribute"""
        cls._attributes[attr.name] = attr

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
        loglevel = "debug"
        self._logger = logging.getLogger("neco.execution.resource.Resource.%s" % 
            self.guid)
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    @property
    def guid(self):
        return self._guid

    @property
    def ec(self):
        return self._ec()

    def connect(self, guid):
        if (self._validate_connection(guid)):
            self._connections.add(guid)

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

    def stop(self):
        pass

    def _validate_connection(self, guid):
        # TODO: Validate!
        return True

class ResourceFactory(object):
    _resource_types = dict()

    @classmethod
    def register_type(cls, rtype, rclass):
        cls._resource_types[rtype] = rclass

    @classmethod
    def create(cls, rtype, ec, guid):
        rclass = cls._resource[rtype]
        return rclass(ec, guid)
