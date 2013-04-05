
from neco.util.timefuncs import strfnow, strfdiff, strfvalid 

import copy
import functools
import logging
import weakref

_reschedule_delay = "1s"

class ResourceAction:
    START = 0
    STOP = 1

class ResourceState:
    NEW = 0
    DEPLOYED = 1
    STARTED = 2
    STOPPED = 3
    FAILED = 4
    RELEASED = 5

def clsinit(cls):
    cls._clsinit()
    return cls

# Decorator to invoke class initialization method
@clsinit
class ResourceManager(object):
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
        self._conditions = dict() 

        # the resource instance gets a copy of all attributes
        # that can modify
        self._attrs = copy.deepcopy(self._attributes)

        self._state = ResourceState.NEW

        self._start_time = None
        self._stop_time = None

        # Logging
        self._logger = logging.getLogger("neco.execution.resource.Resource.%s" % 
            self.guid)

    @property
    def logger(self):
        return self._logger

    @property
    def guid(self):
        return self._guid

    @property
    def ec(self):
        return self._ec()

    @property
    def connections(self):
        return self._connections

    @property
    def conditons(self):
        return self._conditions

    @property
    def start_time(self):
        """ timestamp with  """
        return self._start_time

    @property
    def stop_time(self):
        return self._stop_time

    @property
    def state(self):
        return self._state

    def connect(self, guid):
        if (self._validate_connection(guid)):
            self._connections.add(guid)

    def discover(self, filters = None):
        pass

    def provision(self, filters = None):
        pass

    def start(self):
        if not self._state in [ResourceState.DEPLOYED, ResourceState.STOPPED]:
            self.logger.error("Wrong state %s for start" % self.state)

        self._start_time = strfnow()
        self._state = ResourceState.STARTED

    def stop(self):
        if not self._state in [ResourceState.STARTED]:
            self.logger.error("Wrong state %s for stop" % self.state)

        self._stop_time = strfnow()
        self._state = ResourceState.STOPPED

    def set(self, name, value):
        attr = self._attrs[name]
        attr.value = value

    def get(self, name):
        attr = self._attrs[name]
        return attr.value

    def register_condition(self, action, group, state, 
            time = None):
        if action not in self.conditions:
            self._conditions[action] = set()

        self.conditions.get(action).add((group, state, time))

    def _needs_reschedule(self, group, state, time):
        reschedule = False
        delay = _reschedule_delay 

        # check state and time elapsed on all RMs
        for guid in group:
            rm = self.ec.get_resource(guid)
            # If the RMs is lower than the requested state we must
            # reschedule (e.g. if RM is DEPLOYED but we required STARTED)
            if rm.state < state:
                reschedule = True
                break

            if time:
                if state == ResourceAction.START:
                    t = rm.start_time
                elif state == ResourceAction.STOP:
                    t = rm.stop_time
                else:
                    # Only keep time information for START and STOP
                    break

                delay = strfdiff(t, strnow()) 
                if delay < time:
                    reschedule = True
                    break

        return reschedule, delay

    def set_with_conditions(self, name, value, group, state, time):
        reschedule = False
        delay = _reschedule_delay 

        ## evaluate if set conditions are met

        # only can set with conditions after the RM is started
        if self.status != ResourceStatus.STARTED:
            reschedule = True
        else:
            reschedule, delay = self._needs_reschedule(group, state, time)

        if reschedule:
            callback = functools.partial(self.set_with_conditions, 
                    name, value, group, state, time)
            self.ec.schedule(delay, callback)
        else:
            self.set(name, value)

    def start_with_conditions(self):
        reschedule = False
        delay = _reschedule_delay 

        ## evaluate if set conditions are met

        # only can start when RM is either STOPPED or DEPLOYED
        if self.status not in [ResourceStatus.STOPPED, ResourceStatus.DEPLOYED]:
            reschedule = True
        else:
            for action, (group, state, time) in self.conditions.iteritems():
                if action == ResourceAction.START:
                    reschedule, delay = self._needs_reschedule(group, state, time)   
                    if reschedule:
                        break

        if reschedule:
            callback = functools.partial(self.start_with_conditions, 
                    group, state, time)
            self.ec.schedule(delay, callback)
        else:
            self.start()

    def stop_with_conditions(self):
        reschedule = False
        delay = _reschedule_delay 

        ## evaluate if set conditions are met

        # only can start when RM is either STOPPED or DEPLOYED
        if self.status != ResourceStatus.STARTED:
            reschedule = True
        else:
            for action, (group, state, time) in self.conditions.iteritems():
                if action == ResourceAction.STOP:
                    reschedule, delay = self._needs_reschedule(group, state, time)   
                    if reschedule:
                        break

        if reschedule:
            callback = functools.partial(self.stop_with_conditions, 
                    group, state, time)
            self.ec.schedule(delay, callback)
        else:
            self.stop()

    def deploy(self):
        self.discover()
        self.provision()
        self._state = ResourceState.DEPLOYED

    def release(self):
        self._state = ResourceState.RELEASED

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
    def create(cls, rtype, ec, guid):
        rclass = cls._resource_types[rtype]
        return rclass(ec, guid)

