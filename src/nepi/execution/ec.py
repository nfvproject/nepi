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

import functools
import logging
import os
import random
import sys
import time
import threading

from nepi.util import guid
from nepi.util.parallel import ParallelRun
from nepi.util.timefuncs import tnow, tdiffsec, stabsformat, tsformat 
from nepi.execution.resource import ResourceFactory, ResourceAction, \
        ResourceState, ResourceState2str
from nepi.execution.scheduler import HeapScheduler, Task, TaskStatus
from nepi.execution.trace import TraceAttr

# TODO: use multiprocessing instead of threading
# TODO: When a failure occurs during deployment, scp and ssh processes are left running behind!!
# TODO: Allow to reconnect to a running experiment instance! (reconnect mode vs deploy mode)

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
                       It will be used in the name of the directory 
                        where experiment related information is stored
        :type exp_id: str

    .. note::

        An experiment, or scenario, is defined by a concrete use, behavior,
        configuration and interconnection of resources that describe a single
        experiment case (We call this the experiment description). 
        A same experiment (scenario) can be run many times.

        The ExperimentController (EC), is the entity responsible for 
        managing an experiment instance (run). The same scenario can be 
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
        In order for a new type of resource to be supported in NEPI
        a new RM must be implemented. NEPI already provides different
        RMs to control basic resources, and new can be extended from
        the existing ones.

        Through the EC interface the user can create ResourceManagers (RMs),
        configure them and interconnect them, in order to describe an experiment.
        Describing an experiment through the EC does not run the experiment.
        Only when the 'deploy()' method is invoked on the EC, will the EC take 
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
        exp_id, which can be re-used by different ExperimentController instances,
        and the run_id, which unique to a ExperimentController instance, and
        is automatically generated by NEPI.
        
    """

    def __init__(self, exp_id = None): 
        super(ExperimentController, self).__init__()
        # Logging
        self._logger = logging.getLogger("ExperimentController")

        # Run identifier. It identifies a concrete instance (run) of an experiment.
        # Since a same experiment (same configuration) can be run many times,
        # this id permits to identify concrete exoeriment run
        self._run_id = tsformat()

        # Experiment identifier. Usually assigned by the user
        self._exp_id = exp_id or "exp-%s" % os.urandom(8).encode('hex')

        # generator of globally unique ids
        self._guid_generator = guid.GuidGenerator()
        
        # Resource managers
        self._resources = dict()

        # Scheduler
        self._scheduler = HeapScheduler()

        # Tasks
        self._tasks = dict()

        # RM groups 
        self._groups = dict()

        # generator of globally unique id for groups
        self._group_id_generator = guid.GuidGenerator()
 
        # Event processing thread
        self._cond = threading.Condition()
        self._thread = threading.Thread(target = self._process)
        self._thread.setDaemon(True)
        self._thread.start()

        # EC state
        self._state = ECState.RUNNING

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
    def finished(self):
        """ Put the state of the Experiment Controller into a final state :
            Either TERMINATED or FAILED

        """
        return self.ecstate in [ECState.FAILED, ECState.TERMINATED]

    def wait_finished(self, guids):
        """ Blocking method that wait until all the RM from the 'guid' list 
            reached the state FINISHED

        :param guids: List of guids
        :type guids: list
        """
        return self.wait(guids)

    def wait_started(self, guids):
        """ Blocking method that wait until all the RM from the 'guid' list 
            reached the state STARTED

        :param guids: List of guids
        :type guids: list
        """
        return self.wait(guids, states = [ResourceState.STARTED,
            ResourceState.STOPPED,
            ResourceState.FAILED,
            ResourceState.FINISHED])

    def wait_released(self, guids):
        """ Blocking method that wait until all the RM from the 'guid' list 
            reached the state RELEASED

        :param guids: List of guids
        :type guids: list
        """
        return self.wait(guids, states = [ResourceState.RELEASED,
            ResourceState.STOPPED,
            ResourceState.FAILED,
            ResourceState.FINISHED])

    def wait(self, guids, states = [ResourceState.FINISHED, 
            ResourceState.FAILED,
            ResourceState.STOPPED]):
        """ Blocking method that waits until all the RM from the 'guid' list 
            reached state 'state' or until a failure occurs
            
        :param guids: List of guids
        :type guids: list
        """
        if isinstance(guids, int):
            guids = [guids]

        # we randomly alter the order of the guids to avoid ordering
        # dependencies (e.g. LinuxApplication RMs runing on the same
        # linux host will be synchronized by the LinuxNode SSH lock)
        random.shuffle(guids)

        while True:
            # If no more guids to wait for or an error occured, then exit
            if len(guids) == 0 or self.finished:
                break

            # If a guid reached one of the target states, remove it from list
            guid = guids[0]
            state = self.state(guid)

            if state in states:
                guids.remove(guid)
            else:
                # Debug...
                self.logger.debug(" WAITING FOR %g - state %s " % (guid,
                    self.state(guid, hr = True)))

                # Take the opportunity to 'refresh' the states of the RMs.
                # Query only the first up to N guids (not to overwhelm 
                # the local machine)
                n = 100
                lim = n if len(guids) > n else ( len(guids) -1 )
                nguids = guids[0: lim]

                # schedule state request for all guids (take advantage of
                # scheduler multi threading).
                for guid in nguids:
                    callback = functools.partial(self.state, guid)
                    self.schedule("0s", callback)

                # If the guid is not in one of the target states, wait and
                # continue quering. We keep the sleep big to decrease the
                # number of RM state queries
                time.sleep(2)
  
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

    def stop_with_conditions(self, guid):
        """ Stop a specific RM defined by its 'guid' only if all the conditions are true

            :param guid: Guid of the RM
            :type guid: int

        """
        rm = self.get_resource(guid)
        return rm.stop_with_conditions()

    def start_with_conditions(self, guid):
        """ Start a specific RM defined by its 'guid' only if all the conditions are true

            :param guid: Guid of the RM
            :type guid: int

        """
        rm = self.get_resource(guid)
        return rm.start_with_conditions()

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
            # If no guids list was indicated, all 'NEW' RMs will be deployed
            guids = []
            for guid in self.resources:
                if self.state(guid) == ResourceState.NEW:
                    guids.append(guid)
                
        if isinstance(guids, int):
            guids = [guids]

        # Create deployment group 
        if not group:
            group = self._group_id_generator.next(guid)

        if group not in self._groups:
            self._groups[group] = []

        self._groups[group].extend(guids)

        # Before starting deployment we disorder the guids list with the
        # purpose of speeding up the whole deployment process.
        # It is likely that the user inserted in the 'guids' list closely
        # resources one after another (e.g. all applications
        # connected to the same node can likely appear one after another).
        # This can originate a slow down in the deployment since the N 
        # threads the parallel runner uses to processes tasks may all
        # be taken up by the same family of resources waiting for the 
        # same conditions (e.g. LinuxApplications running on a same 
        # node share a single lock, so they will tend to be serialized).
        # If we disorder the guids list, this problem can be mitigated.
        random.shuffle(guids)

        def wait_all_and_start(group):
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
                # If all resources are read, we schedule the start
                for guid in guids:
                    rm = self.get_resource(guid)
                    self.schedule("0s", rm.start_with_conditions)

        if wait_all_ready:
            # Schedule a function to check that all resources are
            # READY, and only then schedule the start.
            # This aimes at reducing the number of tasks looping in the 
            # scheduler. 
            # Intead of having N start tasks, we will have only one for 
            # the whole group.
            callback = functools.partial(wait_all_and_start, group)
            self.schedule("1s", callback)

        for guid in guids:
            rm = self.get_resource(guid)
            rm.deployment_group = group
            self.schedule("0s", rm.deploy)

            if not wait_all_ready:
                self.schedule("1s", rm.start_with_conditions)

            if rm.conditions.get(ResourceAction.STOP):
                # Only if the RM has STOP conditions we
                # schedule a stop. Otherwise the RM will stop immediately
                self.schedule("2s", rm.stop_with_conditions)

    def release(self, guids = None):
        """ Release al RMs on the guids list or 
        all the resources if no list is specified

            :param guids: List of RM guids
            :type guids: list

        """
        if not guids:
            guids = self.resources

        for guid in guids:
            rm = self.get_resource(guid)
            self.schedule("0s", rm.release)

        self.wait_released(guids)
        
    def shutdown(self):
        """ Shutdown the Experiment Controller. 
        Releases all the resources and stops task processing thread

        """
        self.release()

        # Mark the EC state as TERMINATED
        self._state = ECState.TERMINATED

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
        nthreads = int(os.environ.get("NEPI_NTHREADS", "50"))

        runner = ParallelRun(maxthreads = nthreads)
        runner.start()

        try:
            while not self.finished:
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
                    runner.put(self._execute, task)
        except: 
            import traceback
            err = traceback.format_exc()
            self.logger.error("Error while processing tasks in the EC: %s" % err)

            self._state = ECState.FAILED
        finally:   
            self.logger.debug("Exiting the task processing loop ... ")
            runner.sync()
            runner.destroy()

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

            # Set the EC to FAILED state (this will force to exit the task
            # processing thread)
            self._state = ECState.FAILED

            # Notify condition to wake up the processing thread
            self._notify()

            # Propage error to the ParallelRunner
            raise

    def _notify(self):
        """ Awakes the processing thread in case it is blocked waiting
        for a new task to be scheduled.
        """
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()

