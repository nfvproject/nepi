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

from nepi.util import guid
from nepi.util.parallel import ParallelRun
from nepi.util.timefuncs import tnow, tdiffsec, stabsformat, tsformat 
from nepi.execution.resource import ResourceFactory, ResourceAction, \
        ResourceState, ResourceState2str
from nepi.execution.scheduler import HeapScheduler, Task, TaskStatus
from nepi.execution.trace import TraceAttr

# TODO: use multiprocessing instead of threading
# TODO: Allow to reconnect to a running experiment instance! (reconnect mode vs deploy mode)

import functools
import logging
import os
import random
import sys
import time
import threading
import weakref

class FailureLevel(object):
    """ Describes the system failure state
    """
    OK = 1
    RM_FAILURE = 2
    EC_FAILURE = 3

class FailureManager(object):
    """ The FailureManager is responsible for handling errors,
    and deciding whether an experiment should be aborted
    """

    def __init__(self, ec):
        self._ec = weakref.ref(ec)
        self._failure_level = FailureLevel.OK

    @property
    def ec(self):
        """ Returns the Experiment Controller """
        return self._ec()

    @property
    def abort(self):
        if self._failure_level == FailureLevel.OK:
            for guid in self.ec.resources:
                state = self.ec.state(guid)
                critical = self.ec.get(guid, "critical")

                if state == ResourceState.FAILED and critical:
                    self._failure_level = FailureLevel.RM_FAILURE
                    self.ec.logger.debug("RM critical failure occurred on guid %d." \
                            " Setting EC FAILURE LEVEL to RM_FAILURE" % guid)
                    break

        return self._failure_level != FailureLevel.OK

    def set_ec_failure(self):
        self._failure_level = FailureLevel.EC_FAILURE


class ECState(object):
    """ State of the Experiment Controller
   
    """
    RUNNING = 1
    FAILED = 2
    TERMINATED = 3

class ExperimentController(object):
    """
    .. class:: Class Args :
      
        :param exp_id: Human readable identifier for the experiment scenario. 
        :type exp_id: str

    .. note::

        An experiment, or scenario, is defined by a concrete set of resources,
        behavior, configuration and interconnection of those resources. 
        The Experiment Description (ED) is a detailed representation of a
        single experiment. It contains all the necessary information to 
        allow repeating the experiment. NEPI allows to describe
        experiments by registering components (resources), configuring them
        and interconnecting them.
        
        A same experiment (scenario) can be executed many times, generating 
        different results. We call an experiment execution (instance) a 'run'.

        The ExperimentController (EC), is the entity responsible of
        managing an experiment run. The same scenario can be 
        recreated (and re-run) by instantiating an EC and recreating 
        the same experiment description. 

        In NEPI, an experiment is represented as a graph of interconnected
        resources. A resource is a generic concept in the sense that any
        component taking part of an experiment, whether physical of
        virtual, is considered a resource. A resources could be a host, 
        a virtual machine, an application, a simulator, a IP address.

        A ResourceManager (RM), is the entity responsible for managing a 
        single resource. ResourceManagers are specific to a resource
        type (i.e. An RM to control a Linux application will not be
        the same as the RM used to control a ns-3 simulation).
        To support a new type of resource in NEPI, a new RM must be 
        implemented. NEPI already provides a variety of
        RMs to control basic resources, and new can be extended from
        the existing ones.

        Through the EC interface the user can create ResourceManagers (RMs),
        configure them and interconnect them, to describe an experiment.
        Describing an experiment through the EC does not run the experiment.
        Only when the 'deploy()' method is invoked on the EC, the EC will take 
        actions to transform the 'described' experiment into a 'running' experiment.

        While the experiment is running, it is possible to continue to
        create/configure/connect RMs, and to deploy them to involve new
        resources in the experiment (this is known as 'interactive' deployment).
        
        An experiments in NEPI is identified by a string id, 
        which is either given by the user, or automatically generated by NEPI.  
        The purpose of this identifier is to separate files and results that 
        belong to different experiment scenarios. 
        However, since a same 'experiment' can be run many times, the experiment
        id is not enough to identify an experiment instance (run).
        For this reason, the ExperimentController has two identifier, the 
        exp_id, which can be re-used in different ExperimentController,
        and the run_id, which is unique to one ExperimentController instance, and
        is automatically generated by NEPI.
        
    """

    def __init__(self, exp_id = None): 
        super(ExperimentController, self).__init__()
        # Logging
        self._logger = logging.getLogger("ExperimentController")

        # Run identifier. It identifies a concrete execution instance (run) 
        # of an experiment.
        # Since a same experiment (same configuration) can be executed many 
        # times, this run_id permits to separate result files generated on 
        # different experiment executions
        self._run_id = tsformat()

        # Experiment identifier. Usually assigned by the user
        # Identifies the experiment scenario (i.e. configuration, 
        # resources used, etc)
        self._exp_id = exp_id or "exp-%s" % os.urandom(8).encode('hex')

        # generator of globally unique ids
        self._guid_generator = guid.GuidGenerator()
        
        # Resource managers
        self._resources = dict()

        # Scheduler. It a queue that holds tasks scheduled for
        # execution, and yields the next task to be executed 
        # ordered by execution and arrival time
        self._scheduler = HeapScheduler()

        # Tasks
        self._tasks = dict()

        # RM groups (for deployment) 
        self._groups = dict()

        # generator of globally unique id for groups
        self._group_id_generator = guid.GuidGenerator()

        # Flag to stop processing thread
        self._stop = False
    
        # Entity in charge of managing system failures
        self._fm = FailureManager(self)

        # EC state
        self._state = ECState.RUNNING

        # The runner is a pool of threads used to parallelize 
        # execution of tasks
        nthreads = int(os.environ.get("NEPI_NTHREADS", "50"))
        self._runner = ParallelRun(maxthreads = nthreads)

        # Event processing thread
        self._cond = threading.Condition()
        self._thread = threading.Thread(target = self._process)
        self._thread.setDaemon(True)
        self._thread.start()

    @property
    def logger(self):
        """ Return the logger of the Experiment Controller

        """
        return self._logger

    @property
    def ecstate(self):
        """ Return the state of the Experiment Controller

        """
        return self._state

    @property
    def exp_id(self):
        """ Return the experiment id assigned by the user

        """
        return self._exp_id

    @property
    def run_id(self):
        """ Return the experiment instance (run) identifier  

        """
        return self._run_id

    @property
    def abort(self):
        return self._fm.abort

    def wait_finished(self, guids):
        """ Blocking method that wait until all RMs in the 'guid' list 
            reach a state >= STOPPED (i.e. FINISHED, STOPPED, FAILED or 
            RELEASED ) or until a System Failure occurs (e.g. Task Failure) 

        :param guids: List of guids
        :type guids: list

        """

        def quit():
            return self.abort

        return self.wait(guids, state = ResourceState.STOPPED, 
                quit = quit)

    def wait_started(self, guids):
        """ Blocking method that wait until all RMs in the 'guid' list 
            reach a state >= STARTED or until a System Failure occurs 
            (e.g. Task Failure) 

        :param guids: List of guids
        :type guids: list
        """

        def quit():
            return self.abort

        return self.wait(guids, state = ResourceState.STARTED, 
                quit = quit)

    def wait_released(self, guids):
        """ Blocking method that wait until all RMs in the 'guid' list 
            reach a state = RELEASED or until the EC fails

        :param guids: List of guids
        :type guids: list
        """

        def quit():
            return self._state == ECState.FAILED

        return self.wait(guids, state = ResourceState.RELEASED, 
                quit = quit)

    def wait_deployed(self, guids):
        """ Blocking method that wait until all RMs in the 'guid' list 
            reach a state >= READY or until a System Failure occurs 
            (e.g. Task Failure) 

        :param guids: List of guids
        :type guids: list
        """

        def quit():
            return self.abort

        return self.wait(guids, state = ResourceState.READY, 
                quit = quit)

    def wait(self, guids, state, quit):
        """ Blocking method that wait until all RMs in the 'guid' list 
            reach a state >= 'state' or until quit yileds True
           
        :param guids: List of guids
        :type guids: list
        """
        if isinstance(guids, int):
            guids = [guids]

        # Make a copy to avoid modifying the original guids list
        guids = list(guids)

        while True:
            # If there are no more guids to wait for
            # or the quit function returns True, exit the loop
            if len(guids) == 0 or quit():
                break

            # If a guid reached one of the target states, remove it from list
            guid = guids[0]
            rstate = self.state(guid)
            
            hrrstate = ResourceState2str.get(rstate)
            hrstate = ResourceState2str.get(state)

            if rstate >= state:
                guids.remove(guid)
                self.logger.debug(" guid %d DONE - state is %s, required is >= %s " % (
                    guid, hrrstate, hrstate))
            else:
                # Debug...
                self.logger.debug(" WAITING FOR guid %d - state is %s, required is >= %s " % (
                    guid, hrrstate, hrstate))
                time.sleep(0.5)
  
    def get_task(self, tid):
        """ Get a specific task

        :param tid: Id of the task
        :type tid: int
        :rtype: Task
        """
        return self._tasks.get(tid)

    def get_resource(self, guid):
        """ Get a specific Resource Manager

        :param guid: Id of the task
        :type guid: int
        :rtype: ResourceManager
        """
        return self._resources.get(guid)

    @property
    def resources(self):
        """ Returns the list of all the Resource Manager Id

        :rtype: set

        """
        return self._resources.keys()

    def register_resource(self, rtype, guid = None):
        """ Register a Resource Manager. It creates a new 'guid', if it is not specified, 
        for the RM of type 'rtype' and add it to the list of Resources.

        :param rtype: Type of the RM
        :type rtype: str
        :return: Id of the RM
        :rtype: int
        """
        # Get next available guid
        guid = self._guid_generator.next(guid)
        
        # Instantiate RM
        rm = ResourceFactory.create(rtype, self, guid)

        # Store RM
        self._resources[guid] = rm

        return guid

    def get_attributes(self, guid):
        """ Return all the attibutes of a specific RM

        :param guid: Guid of the RM
        :type guid: int
        :return: List of attributes
        :rtype: list
        """
        rm = self.get_resource(guid)
        return rm.get_attributes()

    def register_connection(self, guid1, guid2):
        """ Registers a guid1 with a guid2. 
            The declaration order is not important

            :param guid1: First guid to connect
            :type guid1: ResourceManager

            :param guid2: Second guid to connect
            :type guid: ResourceManager
        """
        rm1 = self.get_resource(guid1)
        rm2 = self.get_resource(guid2)

        rm1.register_connection(guid2)
        rm2.register_connection(guid1)

    def register_condition(self, guids1, action, guids2, state,
            time = None):
        """ Registers an action START or STOP for all RM on guids1 to occur 
            time 'time' after all elements in guids2 reached state 'state'.

            :param guids1: List of guids of RMs subjected to action
            :type guids1: list

            :param action: Action to register (either START or STOP)
            :type action: ResourceAction

            :param guids2: List of guids of RMs to we waited for
            :type guids2: list

            :param state: State to wait for on RMs (STARTED, STOPPED, etc)
            :type state: ResourceState

            :param time: Time to wait after guids2 has reached status 
            :type time: string

        """
        if isinstance(guids1, int):
            guids1 = [guids1]
        if isinstance(guids2, int):
            guids2 = [guids2]

        for guid1 in guids1:
            rm = self.get_resource(guid1)
            rm.register_condition(action, guids2, state, time)

    def enable_trace(self, guid, name):
        """ Enable trace

        :param name: Name of the trace
        :type name: str
        """
        rm = self.get_resource(guid)
        rm.enable_trace(name)

    def trace_enabled(self, guid, name):
        """ Returns True if trace is enabled

        :param name: Name of the trace
        :type name: str
        """
        rm = self.get_resource(guid)
        return rm.trace_enabled(name)

    def trace(self, guid, name, attr = TraceAttr.ALL, block = 512, offset = 0):
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
        rm = self.get_resource(guid)
        return rm.trace(name, attr, block, offset)

    def discover(self, guid):
        """ Discover a specific RM defined by its 'guid'

            :param guid: Guid of the RM
            :type guid: int

        """
        rm = self.get_resource(guid)
        return rm.discover()

    def provision(self, guid):
        """ Provision a specific RM defined by its 'guid'

            :param guid: Guid of the RM
            :type guid: int

        """
        rm = self.get_resource(guid)
        return rm.provision()

    def get(self, guid, name):
        """ Get a specific attribute 'name' from the RM 'guid'

            :param guid: Guid of the RM
            :type guid: int

            :param name: attribute's name
            :type name: str

        """
        rm = self.get_resource(guid)
        return rm.get(name)

    def set(self, guid, name, value):
        """ Set a specific attribute 'name' from the RM 'guid' 
            with the value 'value' 

            :param guid: Guid of the RM
            :type guid: int

            :param name: attribute's name
            :type name: str

            :param value: attribute's value

        """
        rm = self.get_resource(guid)
        return rm.set(name, value)

    def state(self, guid, hr = False):
        """ Returns the state of a resource

            :param guid: Resource guid
            :type guid: integer

            :param hr: Human readable. Forces return of a 
                status string instead of a number 
            :type hr: boolean

        """
        rm = self.get_resource(guid)
        state = rm.state

        if hr:
            return ResourceState2str.get(state)

        return state

    def stop(self, guid):
        """ Stop a specific RM defined by its 'guid'

            :param guid: Guid of the RM
            :type guid: int

        """
        rm = self.get_resource(guid)
        return rm.stop()

    def start(self, guid):
        """ Start a specific RM defined by its 'guid'

            :param guid: Guid of the RM
            :type guid: int

        """
        rm = self.get_resource(guid)
        return rm.start()

    def set_with_conditions(self, name, value, guids1, guids2, state,
            time = None):
        """ Set value 'value' on attribute with name 'name' on all RMs of
            guids1 when 'time' has elapsed since all elements in guids2 
            have reached state 'state'.

            :param name: Name of attribute to set in RM
            :type name: string

            :param value: Value of attribute to set in RM
            :type name: string

            :param guids1: List of guids of RMs subjected to action
            :type guids1: list

            :param action: Action to register (either START or STOP)
            :type action: ResourceAction

            :param guids2: List of guids of RMs to we waited for
            :type guids2: list

            :param state: State to wait for on RMs (STARTED, STOPPED, etc)
            :type state: ResourceState

            :param time: Time to wait after guids2 has reached status 
            :type time: string

        """
        if isinstance(guids1, int):
            guids1 = [guids1]
        if isinstance(guids2, int):
            guids2 = [guids2]

        for guid1 in guids1:
            rm = self.get_resource(guid)
            rm.set_with_conditions(name, value, guids2, state, time)

    def deploy(self, guids = None, wait_all_ready = True, group = None):
        """ Deploy all resource manager in guids list

        :param guids: List of guids of RMs to deploy
        :type guids: list

        :param wait_all_ready: Wait until all RMs are ready in
            order to start the RMs
        :type guid: int

        :param group: Id of deployment group in which to deploy RMs
        :type group: int

        """
        self.logger.debug(" ------- DEPLOY START ------ ")

        if not guids:
            # If no guids list was passed, all 'NEW' RMs will be deployed
            guids = []
            for guid in self.resources:
                if self.state(guid) == ResourceState.NEW:
                    guids.append(guid)
                
        if isinstance(guids, int):
            guids = [guids]

        # Create deployment group
        # New guids can be added to a same deployment group later on
        new_group = False
        if not group:
            new_group = True
            group = self._group_id_generator.next()

        if group not in self._groups:
            self._groups[group] = []

        self._groups[group].extend(guids)

        def wait_all_and_start(group):
            # Function that checks if all resources are READY
            # before scheduling a start_with_conditions for each RM
            reschedule = False
            
            # Get all guids in group
            guids = self._groups[group]

            for guid in guids:
                if self.state(guid) < ResourceState.READY:
                    reschedule = True
                    break

            if reschedule:
                callback = functools.partial(wait_all_and_start, group)
                self.schedule("1s", callback)
            else:
                # If all resources are ready, we schedule the start
                for guid in guids:
                    rm = self.get_resource(guid)
                    self.schedule("0s", rm.start_with_conditions)

        if wait_all_ready and new_group:
            # Schedule a function to check that all resources are
            # READY, and only then schedule the start.
            # This aims at reducing the number of tasks looping in the 
            # scheduler. 
            # Instead of having many start tasks, we will have only one for 
            # the whole group.
            callback = functools.partial(wait_all_and_start, group)
            self.schedule("0s", callback)

        for guid in guids:
            rm = self.get_resource(guid)
            rm.deployment_group = group
            self.schedule("0s", rm.deploy_with_conditions)

            if not wait_all_ready:
                self.schedule("0s", rm.start_with_conditions)

            if rm.conditions.get(ResourceAction.STOP):
                # Only if the RM has STOP conditions we
                # schedule a stop. Otherwise the RM will stop immediately
                self.schedule("0s", rm.stop_with_conditions)

    def release(self, guids = None):
        """ Release al RMs on the guids list or 
        all the resources if no list is specified

            :param guids: List of RM guids
            :type guids: list

        """
        if not guids:
            guids = self.resources

        # Remove all pending tasks from the scheduler queue
        for tid in list(self._scheduler.pending):
            self._scheduler.remove(tid)

        self._runner.empty()

        for guid in guids:
            rm = self.get_resource(guid)
            self.schedule("0s", rm.release)

        self.wait_released(guids)
        
    def shutdown(self):
        """ Shutdown the Experiment Controller. 
        Releases all the resources and stops task processing thread

        """
        # If there was a major failure we can't exit gracefully
        if self._state == ECState.FAILED:
            raise RuntimeError("EC failure. Can not exit gracefully")

        self.release()

        # Mark the EC state as TERMINATED
        self._state = ECState.TERMINATED

        # Stop processing thread
        self._stop = True

        # Notify condition to wake up the processing thread
        self._notify()
        
        if self._thread.is_alive():
           self._thread.join()

    def schedule(self, date, callback, track = False):
        """ Schedule a callback to be executed at time date.

            :param date: string containing execution time for the task.
                    It can be expressed as an absolute time, using
                    timestamp format, or as a relative time matching
                    ^\d+.\d+(h|m|s|ms|us)$

            :param callback: code to be executed for the task. Must be a
                        Python function, and receives args and kwargs
                        as arguments.

            :param track: if set to True, the task will be retrivable with
                    the get_task() method

            :return : The Id of the task
        """
        timestamp = stabsformat(date)
        task = Task(timestamp, callback)
        task = self._scheduler.schedule(task)

        if track:
            self._tasks[task.id] = task

        # Notify condition to wake up the processing thread
        self._notify()

        return task.id
     
    def _process(self):
        """ Process scheduled tasks.

        .. note::

        The _process method is executed in an independent thread held by the 
        ExperimentController for as long as the experiment is running.
        
        Tasks are scheduled by invoking the schedule method with a target callback. 
        The schedule method is given a execution time which controls the
        order in which tasks are processed. 

        Tasks are processed in parallel using multithreading. 
        The environmental variable NEPI_NTHREADS can be used to control
        the number of threads used to process tasks. The default value is 50.

        Exception handling:

        To execute tasks in parallel, an ParallelRunner (PR) object, holding
        a pool of threads (workers), is used.
        For each available thread in the PR, the next task popped from 
        the scheduler queue is 'put' in the PR.
        Upon receiving a task to execute, each PR worker (thread) invokes the 
        _execute method of the EC, passing the task as argument. 
        This method, calls task.callback inside a try/except block. If an 
        exception is raised by the tasks.callback, it will be trapped by the 
        try block, logged to standard error (usually the console), and the EC 
        state will be set to ECState.FAILED.
        The invocation of _notify immediately after, forces the processing
        loop in the _process method, to wake up if it was blocked waiting for new 
        tasks to arrived, and to check the EC state.
        As the EC is in FAILED state, the processing loop exits and the 
        'finally' block is invoked. In the 'finally' block, the 'sync' method
        of the PR is invoked, which forces the PR to raise any unchecked errors
        that might have been raised by the workers.

        """

        self._runner.start()

        while not self._stop:
            try:
                self._cond.acquire()

                task = self._scheduler.next()
                
                if not task:
                    # No task to execute. Wait for a new task to be scheduled.
                    self._cond.wait()
                else:
                    # The task timestamp is in the future. Wait for timeout 
                    # or until another task is scheduled.
                    now = tnow()
                    if now < task.timestamp:
                        # Calculate timeout in seconds
                        timeout = tdiffsec(task.timestamp, now)

                        # Re-schedule task with the same timestamp
                        self._scheduler.schedule(task)
                        
                        task = None

                        # Wait timeout or until a new task awakes the condition
                        self._cond.wait(timeout)
               
                self._cond.release()

                if task:
                    # Process tasks in parallel
                    self._runner.put(self._execute, task)
            except: 
                import traceback
                err = traceback.format_exc()
                self.logger.error("Error while processing tasks in the EC: %s" % err)

                # Set the EC to FAILED state 
                self._state = ECState.FAILED
            
                # Set the FailureManager failure level to EC failure
                self._fm.set_ec_failure()

        self.logger.debug("Exiting the task processing loop ... ")
        
        self._runner.sync()
        self._runner.destroy()

    def _execute(self, task):
        """ Executes a single task. 

            :param task: Object containing the callback to execute
            :type task: Task

        .. note::

        If the invokation of the task callback raises an
        exception, the processing thread of the ExperimentController
        will be stopped and the experiment will be aborted.

        """
        # Invoke callback
        task.status = TaskStatus.DONE

        try:
            task.result = task.callback()
        except:
            import traceback
            err = traceback.format_exc()
            task.result = err
            task.status = TaskStatus.ERROR
            
            self.logger.error("Error occurred while executing task: %s" % err)

    def _notify(self):
        """ Awakes the processing thread in case it is blocked waiting
        for a new task to be scheduled.
        """
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()

