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

from nepi.util.timefuncs import tnow, tdiff, tdiffsec, stabsformat
from nepi.util.logger import Logger
from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.trace import TraceAttr

import copy
import functools
import logging
import os
import pkgutil
import sys
import weakref

reschedule_delay = "1s"

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

def failtrap(func):
    def wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except:
            import traceback
            err = traceback.format_exc()
            self.error(err)
            self.debug("SETTING guid %d to state FAILED" % self.guid)
            self.fail()
            raise
    
    return wrapped

# Decorator to invoke class initialization method
@clsinit
class ResourceManager(Logger):
    """ Base clase for all ResourceManagers. 
    
    A ResourceManger is specific to a resource type (e.g. Node, 
    Switch, Application, etc) on a specific backend (e.g. PlanetLab, 
    OMF, etc).

    The ResourceManager instances are responsible for interacting with
    and controlling concrete (physical or virtual) resources in the 
    experimental backends.
    
    """
    _rtype = "Resource"
    _attributes = None
    _traces = None
    _help = None
    _backend = None

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
        critical = Attribute("critical", "Defines whether the resource is critical. "
                " A failure on a critical resource will interrupt the experiment. ",
                type = Types.Bool,
                default = True,
                flags = Flags.ExecReadOnly)

        cls._register_attribute(critical)
        
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

    @classmethod
    def get_help(cls):
        """ Returns the description of the type of Resource

        """
        return cls._help

    @classmethod
    def get_backend(cls):
        """ Returns the identified of the backend (i.e. testbed, environment)
        for the Resource

        """
        return cls._backend

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

        # Each resource is placed on a deployment group by the EC
        # during deployment
        self.deployment_group = None

        self._start_time = None
        self._stop_time = None
        self._discover_time = None
        self._provision_time = None
        self._ready_time = None
        self._release_time = None
        self._finish_time = None
        self._failed_time = None

        self._state = ResourceState.NEW

    @property
    def guid(self):
        """ Returns the global unique identifier of the RM """
        return self._guid

    @property
    def ec(self):
        """ Returns the Experiment Controller """
        return self._ec()

    @property
    def connections(self):
        """ Returns the set of guids of connected RMs"""
        return self._connections

    @property
    def conditions(self):
        """ Returns the conditions to which the RM is subjected to.
        
        The object returned by this method is a dictionary indexed by
        ResourceAction."""
        return self._conditions

    @property
    def start_time(self):
        """ Returns the start time of the RM as a timestamp"""
        return self._start_time

    @property
    def stop_time(self):
        """ Returns the stop time of the RM as a timestamp"""
        return self._stop_time

    @property
    def discover_time(self):
        """ Returns the time discovering was finished for the RM as a timestamp"""
        return self._discover_time

    @property
    def provision_time(self):
        """ Returns the time provisioning was finished for the RM as a timestamp"""
        return self._provision_time

    @property
    def ready_time(self):
        """ Returns the time deployment was finished for the RM as a timestamp"""
        return self._ready_time

    @property
    def release_time(self):
        """ Returns the release time of the RM as a timestamp"""
        return self._release_time

    @property
    def finish_time(self):
        """ Returns the finalization time of the RM as a timestamp"""
        return self._finish_time

    @property
    def failed_time(self):
        """ Returns the time failure occured for the RM as a timestamp"""
        return self._failed_time

    @property
    def state(self):
        """ Get the current state of the RM """
        return self._state

    def log_message(self, msg):
        """ Returns the log message formatted with added information.

        :param msg: text message
        :type msg: str
        :rtype: str
        """
        return " %s guid: %d - %s " % (self._rtype, self.guid, msg)

    def register_connection(self, guid):
        """ Registers a connection to the RM identified by guid

        :param guid: Global unique identified of the RM to connect to
        :type guid: int
        """
        if self.valid_connection(guid):
            self.connect(guid)
            self._connections.add(guid)

    def unregister_connection(self, guid):
        """ Removes a registered connection to the RM identified by guid

        :param guid: Global unique identified of the RM to connect to
        :type guid: int
        """
        if guid in self._connections:
            self.disconnect(guid)
            self._connections.remove(guid)

    def discover(self):
        """ Performs resource discovery.

        This  method is responsible for selecting an individual resource
        matching user requirements.
        This method should be redefined when necessary in child classes.

        If overridden in child classes, make sure to use the failtrap 
        decorator to ensure the RM state will be set to FAILED in the event 
        of an exception.

        """
        self.set_discovered()

    def provision(self):
        """ Performs resource provisioning.

        This  method is responsible for provisioning one resource.
        After this method has been successfully invoked, the resource
        should be accessible/controllable by the RM.
        This method should be redefined when necessary in child classes.

        If overridden in child classes, make sure to use the failtrap 
        decorator to ensure the RM state will be set to FAILED in the event 
        of an exception.

        """
        self.set_provisioned()

    def start(self):
        """ Starts the RM.
        
        There is no generic start behavior for all resources.
        This method should be redefined when necessary in child classes.

        If overridden in child classes, make sure to use the failtrap 
        decorator to ensure the RM state will be set to FAILED in the event 
        of an exception.

        """
        if not self.state in [ResourceState.READY, ResourceState.STOPPED]:
            self.error("Wrong state %s for start" % self.state)
            return

        self.set_started()

    def stop(self):
        """ Interrupts the RM, stopping any tasks the RM was performing.
        
        There is no generic stop behavior for all resources.
        This method should be redefined when necessary in child classes.

        If overridden in child classes, make sure to use the failtrap 
        decorator to ensure the RM state will be set to FAILED in the event 
        of an exception.

        """
        if not self.state in [ResourceState.STARTED]:
            self.error("Wrong state %s for stop" % self.state)
            return
        
        self.set_stopped()

    def deploy(self):
        """ Execute all steps required for the RM to reach the state READY.

        This  method is responsible for deploying the resource (and invoking the
        discover and provision methods).
        This method should be redefined when necessary in child classes.

        If overridden in child classes, make sure to use the failtrap 
        decorator to ensure the RM state will be set to FAILED in the event 
        of an exception.

        """
        if self.state > ResourceState.READY:
            self.error("Wrong state %s for deploy" % self.state)
            return

        self.debug("----- READY ---- ")
        self.set_ready()

    def release(self):
        """ Perform actions to free resources used by the RM.
        
        This  method is responsible for releasing resources that were
        used during the experiment by the RM.
        This method should be redefined when necessary in child classes.

        If overridden in child classes, this method should never
        raise an error and it must ensure the RM is set to state RELEASED.

        """
        self.set_released()

    def finish(self):
        """ Sets the RM to state FINISHED. 
        
        The FINISHED state is different from STOPPED in that it should not be 
        directly invoked by the user.
        STOPPED indicates that the user interrupted the RM, FINISHED means
        that the RM concluded normally the actions it was supposed to perform.
        This method should be redefined when necessary in child classes.
        
        If overridden in child classes, make sure to use the failtrap 
        decorator to ensure the RM state will be set to FAILED in the event 
        of an exception.

        """

        self.set_finished()
 
    def fail(self):
        """ Sets the RM to state FAILED.

        """

        self.set_failed()

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
        """ Returns the value of the attribute

        :param name: Name of the attribute
        :type name: str
        :rtype: str
        """
        attr = self._attrs[name]
        return attr.value

    def enable_trace(self, name):
        """ Explicitly enable trace generation

        :param name: Name of the trace
        :type name: str
        """
        trace = self._trcs[name]
        trace.enabled = True
    
    def trace_enabled(self, name):
        """Returns True if trace is enables 

        :param name: Name of the trace
        :type name: str
        """
        trace = self._trcs[name]
        return trace.enabled
 
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

    def register_condition(self, action, group, state, time = None):
        """ Registers a condition on the resource manager to allow execution 
        of 'action' only after 'time' has elapsed from the moment all resources 
        in 'group' reached state 'state'

        :param action: Action to restrict to condition (either 'START' or 'STOP')
        :type action: str
        :param group: Group of RMs to wait for (list of guids)
        :type group: int or list of int
        :param state: State to wait for on all RM in group. (either 'STARTED', 'STOPPED' or 'READY')
        :type state: str
        :param time: Time to wait after 'state' is reached on all RMs in group. (e.g. '2s')
        :type time: str

        """

        if not action in self.conditions:
            self._conditions[action] = list()
        
        conditions = self.conditions.get(action)

        # For each condition to register a tuple of (group, state, time) is 
        # added to the 'action' list
        if not isinstance(group, list):
            group = [group]

        conditions.append((group, state, time))

    def unregister_condition(self, group, action = None):
        """ Removed conditions for a certain group of guids

        :param action: Action to restrict to condition (either 'START', 'STOP' or 'READY')
        :type action: str

        :param group: Group of RMs to wait for (list of guids)
        :type group: int or list of int

        """
        # For each condition a tuple of (group, state, time) is 
        # added to the 'action' list
        if not isinstance(group, list):
            group = [group]

        for act, conditions in self.conditions.iteritems():
            if action and act != action:
                continue

            for condition in list(conditions):
                (grp, state, time) = condition

                # If there is an intersection between grp and group,
                # then remove intersected elements
                intsec = set(group).intersection(set(grp))
                if intsec:
                    idx = conditions.index(condition)
                    newgrp = set(grp)
                    newgrp.difference_update(intsec)
                    conditions[idx] = (newgrp, state, time)
                 
    def get_connected(self, rtype = None):
        """ Returns the list of RM with the type 'rtype'

        :param rtype: Type of the RM we look for
        :type rtype: str
        :return: list of guid
        """
        connected = []
        rclass = ResourceFactory.get_resource_type(rtype)
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if not rtype or isinstance(rm, rclass):
                connected.append(rm)
        return connected

    def _needs_reschedule(self, group, state, time):
        """ Internal method that verify if 'time' has elapsed since 
        all elements in 'group' have reached state 'state'.

        :param group: Group of RMs to wait for (list of guids)
        :type group: int or list of int
        :param state: State to wait for on all RM in group. (either 'STARTED', 'STOPPED' or 'READY')
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
            # reschedule (e.g. if RM is READY but we required STARTED).
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
                    break

                # time already elapsed since RM changed state
                waited = "%fs" % tdiffsec(tnow(), t)

                # time still to wait
                wait = tdiffsec(stabsformat(time), stabsformat(waited))

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

        ## evaluate if conditions to start are met
        if self.ec.abort:
            return 

        # Can only start when RM is either STOPPED or READY
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

        ## evaluate if conditions to stop are met
        if self.ec.abort:
            return 

        # only can stop when RM is STARTED
        if self.state != ResourceState.STARTED:
            reschedule = True
            self.debug("---- RESCHEDULING STOP ---- state %s " % self.state )
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

    def deploy_with_conditions(self):
        """ Deploy RM when all the conditions in self.conditions for
        action 'READY' are satisfied.

        """
        reschedule = False
        delay = reschedule_delay 

        ## evaluate if conditions to deploy are met
        if self.ec.abort:
            return 

        # only can deploy when RM is either NEW, DISCOVERED or PROVISIONED 
        if self.state not in [ResourceState.NEW, ResourceState.DISCOVERED, 
                ResourceState.PROVISIONED]:
            reschedule = True
            self.debug("---- RESCHEDULING DEPLOY ---- state %s " % self.state )
        else:
            deploy_conditions = self.conditions.get(ResourceAction.DEPLOY, [])
            
            self.debug("---- DEPLOY CONDITIONS ---- %s" % deploy_conditions) 
            
            # Verify all start conditions are met
            for (group, state, time) in deploy_conditions:
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
            self.ec.schedule(delay, self.deploy_with_conditions)
        else:
            self.debug("----- STARTING ---- ")
            self.deploy()

    def connect(self, guid):
        """ Performs actions that need to be taken upon associating RMs.
        This method should be redefined when necessary in child classes.
        """
        pass

    def disconnect(self, guid):
        """ Performs actions that need to be taken upon disassociating RMs.
        This method should be redefined when necessary in child classes.
        """
        pass

    def valid_connection(self, guid):
        """Checks whether a connection with the other RM
        is valid.
        This method need to be redefined by each new Resource Manager.

        :param guid: Guid of the current Resource Manager
        :type guid: int
        :rtype:  Boolean

        """
        # TODO: Validate!
        return True
    
    def set_started(self):
        """ Mark ResourceManager as STARTED """
        self.set_state(ResourceState.STARTED, "_start_time")
        
    def set_stopped(self):
        """ Mark ResourceManager as STOPPED """
        self.set_state(ResourceState.STOPPED, "_stop_time")

    def set_ready(self):
        """ Mark ResourceManager as READY """
        self.set_state(ResourceState.READY, "_ready_time")

    def set_released(self):
        """ Mark ResourceManager as REALEASED """
        self.set_state(ResourceState.RELEASED, "_release_time")

    def set_finished(self):
        """ Mark ResourceManager as FINISHED """
        self.set_state(ResourceState.FINISHED, "_finish_time")

    def set_failed(self):
        """ Mark ResourceManager as FAILED """
        self.set_state(ResourceState.FAILED, "_failed_time")

    def set_discovered(self):
        """ Mark ResourceManager as DISCOVERED """
        self.set_state(ResourceState.DISCOVERED, "_discover_time")

    def set_provisioned(self):
        """ Mark ResourceManager as PROVISIONED """
        self.set_state(ResourceState.PROVISIONED, "_provision_time")

    def set_state(self, state, state_time_attr):
        # Ensure that RM state will not change after released
        if self._state == ResourceState.RELEASED:
            return 
   
        setattr(self, state_time_attr, tnow())
        self._state = state

class ResourceFactory(object):
    _resource_types = dict()

    @classmethod
    def resource_types(cls):
        """Return the type of the Class"""
        return cls._resource_types

    @classmethod
    def get_resource_type(cls, rtype):
        """Return the type of the Class"""
        return cls._resource_types.get(rtype)

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
    # Once the factory is populated, don't repopulate
    if not ResourceFactory.resource_types():
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

    for importer, modname, ispkg in pkgutil.walk_packages(search_path, 
            prefix = "nepi.resources."):

        loader = importer.find_module(modname)
        
        try:
            # Notice: Repeated calls to load_module will act as a reload of teh module
            if modname in sys.modules:
                module = sys.modules.get(modname)
            else:
                module = loader.load_module(modname)

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

                    if not modname in sys.modules:
                        sys.modules[modname] = module

        except:
            import traceback
            import logging
            err = traceback.format_exc()
            logger = logging.getLogger("Resource.find_types()")
            logger.error("Error while loading Resource Managers %s" % err)

    return types


