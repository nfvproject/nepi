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

from nepi.util.timefuncs import strfnow, strfdiff, strfvalid
from nepi.util.logger import Logger
from nepi.execution.trace import TraceAttr

import copy
import functools
import logging
import os
import pkgutil
import weakref

reschedule_delay = "0.5s"

class ResourceAction:
    """ Action that a user can order to a Resource Manager
   
    """
    DEPLOY = 0
    START = 1
    STOP = 2

class ResourceState:
    """ State of a Resource Manager
   
    """
    NEW = 0
    DISCOVERED = 1
    PROVISIONED = 2
    READY = 3
    STARTED = 4
    STOPPED = 5
    FINISHED = 6
    FAILED = 7
    RELEASED = 8

ResourceState2str = dict({
    ResourceState.NEW : "NEW",
    ResourceState.DISCOVERED : "DISCOVERED",
    ResourceState.PROVISIONED : "PROVISIONED",
    ResourceState.READY : "READY",
    ResourceState.STARTED : "STARTED",
    ResourceState.STOPPED : "STOPPED",
    ResourceState.FINISHED : "FINISHED",
    ResourceState.FAILED : "FAILED",
    ResourceState.RELEASED : "RELEASED",
    })

def clsinit(cls):
    """ Initializes template information (i.e. attributes and traces)
    for the ResourceManager class
    """
    cls._clsinit()
    return cls

def clsinit_copy(cls):
    """ Initializes template information (i.e. attributes and traces)
    for the ResourceManager class, inheriting attributes and traces
    from the parent class
    """
    cls._clsinit_copy()
    return cls

# Decorator to invoke class initialization method
@clsinit
class ResourceManager(Logger):
    _rtype = "Resource"
    _attributes = None
    _traces = None

    @classmethod
    def _register_attribute(cls, attr):
        """ Resource subclasses will invoke this method to add a 
        resource attribute

        """
        cls._attributes[attr.name] = attr

    @classmethod
    def _remove_attribute(cls, name):
        """ Resource subclasses will invoke this method to remove a 
        resource attribute

        """
        del cls._attributes[name]

    @classmethod
    def _register_trace(cls, trace):
        """ Resource subclasses will invoke this method to add a 
        resource trace

        """
        cls._traces[trace.name] = trace

    @classmethod
    def _remove_trace(cls, name):
        """ Resource subclasses will invoke this method to remove a 
        resource trace

        """
        del cls._traces[name]

    @classmethod
    def _register_attributes(cls):
        """ Resource subclasses will invoke this method to register
        resource attributes

        """
        pass

    @classmethod
    def _register_traces(cls):
        """ Resource subclasses will invoke this method to register
        resource traces

        """
        pass

    @classmethod
    def _clsinit(cls):
        """ ResourceManager child classes have different attributes and traces.
        Since the templates that hold the information of attributes and traces
        are 'class attribute' dictionaries, initially they all point to the 
        parent class ResourceManager instances of those dictionaries. 
        In order to make these templates independent from the parent's one,
        it is necessary re-initialize the corresponding dictionaries. 
        This is the objective of the _clsinit method
        """
        # static template for resource attributes
        cls._attributes = dict()
        cls._register_attributes()

        # static template for resource traces
        cls._traces = dict()
        cls._register_traces()

    @classmethod
    def _clsinit_copy(cls):
        """ Same as _clsinit, except that it also inherits all attributes and traces
        from the parent class.
        """
        # static template for resource attributes
        cls._attributes = copy.deepcopy(cls._attributes)
        cls._register_attributes()

        # static template for resource traces
        cls._traces = copy.deepcopy(cls._traces)
        cls._register_traces()

    @classmethod
    def rtype(cls):
        """ Returns the type of the Resource Manager

        """
        return cls._rtype

    @classmethod
    def get_attributes(cls):
        """ Returns a copy of the attributes

        """
        return copy.deepcopy(cls._attributes.values())

    @classmethod
    def get_traces(cls):
        """ Returns a copy of the traces

        """
        return copy.deepcopy(cls._traces.values())

    def __init__(self, ec, guid):
        super(ResourceManager, self).__init__(self.rtype())
        
        self._guid = guid
        self._ec = weakref.ref(ec)
        self._connections = set()
        self._conditions = dict() 

        # the resource instance gets a copy of all attributes
        self._attrs = copy.deepcopy(self._attributes)

        # the resource instance gets a copy of all traces
        self._trcs = copy.deepcopy(self._traces)

        self._state = ResourceState.NEW

        self._start_time = None
        self._stop_time = None
        self._discover_time = None
        self._provision_time = None
        self._ready_time = None
        self._release_time = None

    @property
    def guid(self):
        """ Returns the guid of the current RM """
        return self._guid

    @property
    def ec(self):
        """ Returns the Experiment Controller """
        return self._ec()

    @property
    def connections(self):
        """ Returns the set of connection for this RM"""
        return self._connections

    @property
    def conditions(self):
        """ Returns the list of conditions for this RM
        The list is a dictionary with for each action, a list of tuple 
        describing the conditions. """
        return self._conditions

    @property
    def start_time(self):
        """ Returns timestamp with the time the RM started """
        return self._start_time

    @property
    def stop_time(self):
        """ Returns timestamp with the time the RM stopped """
        return self._stop_time

    @property
    def discover_time(self):
        """ Returns timestamp with the time the RM passed to state discovered """
        return self._discover_time

    @property
    def provision_time(self):
        """ Returns timestamp with the time the RM passed to state provisioned """
        return self._provision_time

    @property
    def ready_time(self):
        """ Returns timestamp with the time the RM passed to state ready  """
        return self._ready_time

    @property
    def release_time(self):
        """ Returns timestamp with the time the RM was released """
        return self._release_time

    @property
    def state(self):
        """ Get the state of the current RM """
        return self._state

    def log_message(self, msg):
        """ Improve debugging message by adding more information 
            as the guid and the type of the RM

        :param msg: Message to log
        :type msg: str
        :rtype: str
        """
        return " %s guid: %d - %s " % (self._rtype, self.guid, msg)

    def connect(self, guid):
        """ Connect the current RM with the RM 'guid'

        :param guid: Guid of the RM the current RM will be connected
        :type guid: int
        """
        if self.valid_connection(guid):
            self._connections.add(guid)

    def discover(self):
        """ Discover the Resource. As it is specific for each RM, 
        this method take the time when the RM become DISCOVERED and
        change the status """
        self._discover_time = strfnow()
        self._state = ResourceState.DISCOVERED

    def provision(self):
        """ Provision the Resource. As it is specific for each RM, 
        this method take the time when the RM become PROVISIONNED and
        change the status """
        self._provision_time = strfnow()
        self._state = ResourceState.PROVISIONED

    def start(self):
        """ Start the Resource Manager. As it is specific to each RM, this methods
        just change, after some verifications, the status to STARTED and save the time.

        """
        if not self._state in [ResourceState.READY, ResourceState.STOPPED]:
            self.error("Wrong state %s for start" % self.state)
            return

        self._start_time = strfnow()
        self._state = ResourceState.STARTED

    def stop(self):
        """ Stop the Resource Manager. As it is specific to each RM, this methods
        just change, after some verifications, the status to STOPPED and save the time.

        """
        if not self._state in [ResourceState.STARTED]:
            self.error("Wrong state %s for stop" % self.state)
            return

        self._stop_time = strfnow()
        self._state = ResourceState.STOPPED

    def set(self, name, value):
        """ Set the value of the attribute

        :param name: Name of the attribute
        :type name: str
        :param name: Value of the attribute
        :type name: str
        """
        attr = self._attrs[name]
        attr.value = value

    def get(self, name):
        """ Start the Resource Manager

        :param name: Name of the attribute
        :type name: str
        :rtype: str
        """
        attr = self._attrs[name]
        return attr.value

    def register_trace(self, name):
        """ Enable trace

        :param name: Name of the trace
        :type name: str
        """
        trace = self._trcs[name]
        trace.enabled = True

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        """ Get information on collected trace

        :param name: Name of the trace
        :type name: str

        :param attr: Can be one of:
                         - TraceAttr.ALL (complete trace content), 
                         - TraceAttr.STREAM (block in bytes to read starting at offset), 
                         - TraceAttr.PATH (full path to the trace file),
                         - TraceAttr.SIZE (size of trace file). 
        :type attr: str

        :param block: Number of bytes to retrieve from trace, when attr is TraceAttr.STREAM 
        :type name: int

        :param offset: Number of 'blocks' to skip, when attr is TraceAttr.STREAM 
        :type name: int

        :rtype: str
        """
        pass

    def register_condition(self, action, group, state, 
            time = None):
        """ Registers a condition on the resource manager to allow execution 
        of 'action' only after 'time' has elapsed from the moment all resources 
        in 'group' reached state 'state'

        :param action: Action to restrict to condition (either 'START' or 'STOP')
        :type action: str
        :param group: Group of RMs to wait for (list of guids)
        :type group: int or list of int
        :param state: State to wait for on all RM in group. (either 'STARTED' or 'STOPPED')
        :type state: str
        :param time: Time to wait after 'state' is reached on all RMs in group. (e.g. '2s')
        :type time: str

        """
        conditions = self.conditions.get(action)
        if not conditions:
            conditions = list()
            self._conditions[action] = conditions

        # For each condition to register a tuple of (group, state, time) is 
        # added to the 'action' list
        if not isinstance(group, list):
            group = [group]

        conditions.append((group, state, time))

    def get_connected(self, rtype):
        """ Return the list of RM with the type 'rtype' 

        :param rtype: Type of the RM we look for
        :type rtype: str
        :return : list of guid
        """
        connected = []
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if rm.rtype() == rtype:
                connected.append(rm)
        return connected

    def _needs_reschedule(self, group, state, time):
        """ Internal method that verify if 'time' has elapsed since 
        all elements in 'group' have reached state 'state'.

        :param group: Group of RMs to wait for (list of guids)
        :type group: int or list of int
        :param state: State to wait for on all RM in group. (either 'STARTED' or 'STOPPED')
        :type state: str
        :param time: Time to wait after 'state' is reached on all RMs in group. (e.g. '2s')
        :type time: str

        .. note : time should be written like "2s" or "3m" with s for seconds, m for minutes, h for hours, ...
        If for example, you need to wait 2min 30sec, time could be "150s" or "2.5m".
        For the moment, 2m30s is not a correct syntax.

        """
        reschedule = False
        delay = reschedule_delay 

        # check state and time elapsed on all RMs
        for guid in group:
            rm = self.ec.get_resource(guid)
            # If the RM state is lower than the requested state we must
            # reschedule (e.g. if RM is READY but we required STARTED)
            if rm.state < state:
                reschedule = True
                break

            # If there is a time restriction, we must verify the
            # restriction is satisfied 
            if time:
                if state == ResourceState.DISCOVERED:
                    t = rm.discover_time
                if state == ResourceState.PROVISIONED:
                    t = rm.provision_time
                elif state == ResourceState.READY:
                    t = rm.ready_time
                elif state == ResourceState.STARTED:
                    t = rm.start_time
                elif state == ResourceState.STOPPED:
                    t = rm.stop_time
                else:
                    # Only keep time information for START and STOP
                    break

                d = strfdiff(strfnow(), t)
                wait = strfdiff(strfvalid(time),strfvalid(str(d)+"s"))
                if wait > 0.001:
                    reschedule = True
                    delay = "%fs" % wait
                    break
        return reschedule, delay

    def set_with_conditions(self, name, value, group, state, time):
        """ Set value 'value' on attribute with name 'name' when 'time' 
            has elapsed since all elements in 'group' have reached state
           'state'

        :param name: Name of the attribute to set
        :type name: str
        :param name: Value of the attribute to set
        :type name: str
        :param group: Group of RMs to wait for (list of guids)
        :type group: int or list of int
        :param state: State to wait for on all RM in group. (either 'STARTED', 'STOPPED' or 'READY')
        :type state: str
        :param time: Time to wait after 'state' is reached on all RMs in group. (e.g. '2s')
        :type time: str

        """

        reschedule = False
        delay = reschedule_delay 

        ## evaluate if set conditions are met

        # only can set with conditions after the RM is started
        if self.state != ResourceState.STARTED:
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
        """ Starts RM when all the conditions in self.conditions for
        action 'START' are satisfied.

        """
        reschedule = False
        delay = reschedule_delay 

        ## evaluate if set conditions are met

        # only can start when RM is either STOPPED or READY
        if self.state not in [ResourceState.STOPPED, ResourceState.READY]:
            reschedule = True
            self.debug("---- RESCHEDULING START ---- state %s " % self.state )
        else:
            start_conditions = self.conditions.get(ResourceAction.START, [])
            
            self.debug("---- START CONDITIONS ---- %s" % start_conditions) 
            
            # Verify all start conditions are met
            for (group, state, time) in start_conditions:
                # Uncomment for debug
                #unmet = []
                #for guid in group:
                #    rm = self.ec.get_resource(guid)
                #    unmet.append((guid, rm._state))
                #
                #self.debug("---- WAITED STATES ---- %s" % unmet )

                reschedule, delay = self._needs_reschedule(group, state, time)
                if reschedule:
                    break

        if reschedule:
            self.ec.schedule(delay, self.start_with_conditions)
        else:
            self.debug("----- STARTING ---- ")
            self.start()

    def stop_with_conditions(self):
        """ Stops RM when all the conditions in self.conditions for
        action 'STOP' are satisfied.

        """
        reschedule = False
        delay = reschedule_delay 

        ## evaluate if set conditions are met

        # only can stop when RM is STARTED
        if self.state != ResourceState.STARTED:
            reschedule = True
        else:
            self.debug(" ---- STOP CONDITIONS ---- %s" % 
                    self.conditions.get(ResourceAction.STOP))

            stop_conditions = self.conditions.get(ResourceAction.STOP, []) 
            for (group, state, time) in stop_conditions:
                reschedule, delay = self._needs_reschedule(group, state, time)
                if reschedule:
                    break

        if reschedule:
            callback = functools.partial(self.stop_with_conditions)
            self.ec.schedule(delay, callback)
        else:
            self.debug(" ----- STOPPING ---- ") 
            self.stop()

    def deploy(self):
        """ Execute all steps required for the RM to reach the state READY

        """
        if self._state > ResourceState.READY:
            self.error("Wrong state %s for deploy" % self.state)
            return

        self.debug("----- READY ---- ")
        self._ready_time = strfnow()
        self._state = ResourceState.READY

    def release(self):
        """Clean the resource at the end of the Experiment and change the status

        """
        self._release_time = strfnow()
        self._state = ResourceState.RELEASED

    def valid_connection(self, guid):
        """Check if the connection is available. This method need to be 
        redefined by each new Resource Manager.

        :param guid: Guid of the current Resource Manager
        :type guid: int
        :rtype:  Boolean

        """
        # TODO: Validate!
        return True

class ResourceFactory(object):
    _resource_types = dict()

    @classmethod
    def resource_types(cls):
        """Return the type of the Class"""
        return cls._resource_types

    @classmethod
    def register_type(cls, rclass):
        """Register a new Ressource Manager"""
        cls._resource_types[rclass.rtype()] = rclass

    @classmethod
    def create(cls, rtype, ec, guid):
        """Create a new instance of a Ressource Manager"""
        rclass = cls._resource_types[rtype]
        return rclass(ec, guid)

def populate_factory():
    """Register all the possible RM that exists in the current version of Nepi.
    """
    for rclass in find_types():
        ResourceFactory.register_type(rclass)

def find_types():
    """Look into the different folders to find all the 
    availables Resources Managers

    """
    search_path = os.environ.get("NEPI_SEARCH_PATH", "")
    search_path = set(search_path.split(" "))
   
    import inspect
    import nepi.resources 
    path = os.path.dirname(nepi.resources.__file__)
    search_path.add(path)

    types = []

    for importer, modname, ispkg in pkgutil.walk_packages(search_path):
        loader = importer.find_module(modname)
        try:
            module = loader.load_module(loader.fullname)
            for attrname in dir(module):
                if attrname.startswith("_"):
                    continue

                attr = getattr(module, attrname)

                if attr == ResourceManager:
                    continue

                if not inspect.isclass(attr):
                    continue

                if issubclass(attr, ResourceManager):
                    types.append(attr)
        except:
            import traceback
            import logging
            err = traceback.format_exc()
            logger = logging.getLogger("Resource.find_types()")
            logger.error("Error while lading Resource Managers %s" % err)

    return types


