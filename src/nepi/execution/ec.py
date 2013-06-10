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
from nepi.util.timefuncs import strfnow, strfdiff, strfvalid 
from nepi.execution.resource import ResourceFactory, ResourceAction, \
        ResourceState, ResourceState2str
from nepi.execution.scheduler import HeapScheduler, Task, TaskStatus
from nepi.execution.trace import TraceAttr

# TODO: use multiprocessing instead of threading
# TODO: When a failure occurrs during deployment scp and ssh processes are left running behind!!

class ECState(object):
    """ State of the Experiment Controller
   
    """
    RUNNING = 1
    FAILED = 2
    TERMINATED = 3

class ExperimentController(object):
    """
    .. class:: Class Args :
      
        :param exp_id: Id of the experiment
        :type exp_id: int
        :param root_dir: Root directory of the experiment
        :type root_dir: str

    .. note::

       This class is the only one used by the User. Indeed, the user "talks"
       only with the Experiment Controller and this latter forward to 
       the different Resources Manager the order provided by the user.

    """

    def __init__(self, exp_id = None, root_dir = "/tmp"): 
        super(ExperimentController, self).__init__()
        # root directory to store files
        self._root_dir = root_dir

        # experiment identifier given by the user
        self._exp_id = exp_id or "nepi-exp-%s" % os.urandom(8).encode('hex')

        # generator of globally unique ids
        self._guid_generator = guid.GuidGenerator()
        
        # Resource managers
        self._resources = dict()

        # Scheduler
        self._scheduler = HeapScheduler()

        # Tasks
        self._tasks = dict()

        # Event processing thread
        self._cond = threading.Condition()
        self._thread = threading.Thread(target = self._process)
        self._thread.setDaemon(True)
        self._thread.start()

        # EC state
        self._state = ECState.RUNNING

        # Logging
        self._logger = logging.getLogger("ExperimentController")

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
        """ Return the experiment ID

        """
        exp_id = self._exp_id
        if not exp_id.startswith("nepi-"):
            exp_id = "nepi-" + exp_id
        return exp_id

    @property
    def finished(self):
        """ Put the state of the Experiment Controller into a final state :
            Either TERMINATED or FAILED

        """
        return self.ecstate in [ECState.FAILED, ECState.TERMINATED]

    def wait_finished(self, guids):
        """ Blocking method that wait until all the RM from the 'guid' list 
            reach the state FINISHED

        :param guids: List of guids
        :type guids: list
        """
        if isinstance(guids, int):
            guids = [guids]

        while not all([self.state(guid) in [ResourceState.FINISHED, 
            ResourceState.STOPPED, 
            ResourceState.FAILED] \
                for guid in guids]) and not self.finished:
            # We keep the sleep as large as possible to 
            # decrese the number of RM state requests
            time.sleep(2)
    
    def get_task(self, tid):
        """ Get a specific task

        :param tid: Id of the task
        :type tid: int
        :rtype:  unknow
        """
        return self._tasks.get(tid)

    def get_resource(self, guid):
        """ Get a specific Resource Manager

        :param guid: Id of the task
        :type guid: int
        :rtype:  ResourceManager
        """
        return self._resources.get(guid)

    @property
    def resources(self):
        """ Returns the list of all the Resource Manager Id

        :rtype:  set
        """
        return self._resources.keys()

    def register_resource(self, rtype, guid = None):
        """ Register a Resource Manager. It creates a new 'guid', if it is not specified, 
        for the RM of type 'rtype' and add it to the list of Resources.

        :param rtype: Type of the RM
        :type rtype: str
        :return : Id of the RM
        :rtype:  int
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
        :return : List of attributes
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

        rm1.connect(guid2)
        rm2.connect(guid1)

    def register_condition(self, group1, action, group2, state,
            time = None):
        """ Registers an action START or STOP for all RM on group1 to occur 
            time 'time' after all elements in group2 reached state 'state'.

            :param group1: List of guids of RMs subjected to action
            :type group1: list

            :param action: Action to register (either START or STOP)
            :type action: ResourceAction

            :param group2: List of guids of RMs to we waited for
            :type group2: list

            :param state: State to wait for on RMs (STARTED, STOPPED, etc)
            :type state: ResourceState

            :param time: Time to wait after group2 has reached status 
            :type time: string

        """
        if isinstance(group1, int):
            group1 = [group1]
        if isinstance(group2, int):
            group2 = [group2]

        for guid1 in group1:
            rm = self.get_resource(guid1)
            rm.register_condition(action, group2, state, time)

    def register_trace(self, guid, name):
        """ Enable trace

        :param name: Name of the trace
        :type name: str
        """
        rm = self.get_resource(guid)
        rm.register_trace(name)

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
        if hr:
            return ResourceState2str.get(rm.state)

        return rm.state

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

    def set_with_conditions(self, name, value, group1, group2, state,
            time = None):
        """ Set value 'value' on attribute with name 'name' on all RMs of
            group1 when 'time' has elapsed since all elements in group2 
            have reached state 'state'.

            :param name: Name of attribute to set in RM
            :type name: string

            :param value: Value of attribute to set in RM
            :type name: string

            :param group1: List of guids of RMs subjected to action
            :type group1: list

            :param action: Action to register (either START or STOP)
            :type action: ResourceAction

            :param group2: List of guids of RMs to we waited for
            :type group2: list

            :param state: State to wait for on RMs (STARTED, STOPPED, etc)
            :type state: ResourceState

            :param time: Time to wait after group2 has reached status 
            :type time: string

        """
        if isinstance(group1, int):
            group1 = [group1]
        if isinstance(group2, int):
            group2 = [group2]

        for guid1 in group1:
            rm = self.get_resource(guid)
            rm.set_with_conditions(name, value, group2, state, time)

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
        return rm.start_with_condition()

    def deploy(self, group = None, wait_all_ready = True):
        """ Deploy all resource manager in group

        :param group: List of guids of RMs to deploy
        :type group: list

        :param wait_all_ready: Wait until all RMs are ready in
            order to start the RMs
        :type guid: int

        """
        self.logger.debug(" ------- DEPLOY START ------ ")

        if not group:
            group = self.resources

        # Before starting deployment we disorder the group list with the
        # purpose of speeding up the whole deployment process.
        # It is likely that the user inserted in the 'group' list closely
        # resources one after another (e.g. all applications
        # connected to the same node can likely appear one after another).
        # This can originate a slow down in the deployment since the N 
        # threads the parallel runner uses to processes tasks may all
        # be taken up by the same family of resources waiting for the 
        # same conditions (e.g. LinuxApplications running on a same 
        # node share a single lock, so they will tend to be serialized).
        # If we disorder the group list, this problem can be mitigated.
        random.shuffle(group)

        def wait_all_and_start(group):
            reschedule = False
            for guid in group:
                rm = self.get_resource(guid)
                if rm.state < ResourceState.READY:
                    reschedule = True
                    break

            if reschedule:
                callback = functools.partial(wait_all_and_start, group)
                self.schedule("1s", callback)
            else:
                # If all resources are read, we schedule the start
                for guid in group:
                    rm = self.get_resource(guid)
                    self.schedule("0.01s", rm.start_with_conditions)

        if wait_all_ready:
            # Schedule the function that will check all resources are
            # READY, and only then it will schedule the start.
            # This is aimed to reduce the number of tasks looping in the scheduler.
            # Intead of having N start tasks, we will have only one
            callback = functools.partial(wait_all_and_start, group)
            self.schedule("1s", callback)

        for guid in group:
            rm = self.get_resource(guid)
            self.schedule("0.001s", rm.deploy)

            if not wait_all_ready:
                self.schedule("1s", rm.start_with_conditions)

            if rm.conditions.get(ResourceAction.STOP):
                # Only if the RM has STOP conditions we
                # schedule a stop. Otherwise the RM will stop immediately
                self.schedule("2s", rm.stop_with_conditions)


    def release(self, group = None):
        """ Release the elements of the list 'group' or 
        all the resources if any group is specified

            :param group: List of RM
            :type group: list

        """
        if not group:
            group = self.resources

        threads = []
        for guid in group:
            rm = self.get_resource(guid)
            thread = threading.Thread(target=rm.release)
            threads.append(thread)
            thread.setDaemon(True)
            thread.start()

        while list(threads) and not self.finished:
            thread = threads[0]
            # Time out after 5 seconds to check EC not terminated
            thread.join(5)
            if not thread.is_alive():
                threads.remove(thread)
        
    def shutdown(self):
        """ Shutdown the Experiment Controller. 
        It means : Release all the resources and stop the scheduler

        """
        self.release()

        self._stop_scheduler()
        
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
        timestamp = strfvalid(date)
        
        task = Task(timestamp, callback)
        task = self._scheduler.schedule(task)

        if track:
            self._tasks[task.id] = task
  
        # Notify condition to wake up the processing thread
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()

        return task.id
     
    def _process(self):
        """ Process at executing the task that are in the scheduler.

        """

        runner = ParallelRun(maxthreads = 50)
        runner.start()

        try:
            while not self.finished:
                self._cond.acquire()
                task = self._scheduler.next()
                self._cond.release()
                
                if not task:
                    # It there are not tasks in the tasks queue we need to 
                    # wait until a call to schedule wakes us up
                    self._cond.acquire()
                    self._cond.wait()
                    self._cond.release()
                else: 
                    # If the task timestamp is in the future the thread needs to wait
                    # until time elapse or until another task is scheduled
                    now = strfnow()
                    if now < task.timestamp:
                        # Calculate time difference in seconds
                        timeout = strfdiff(task.timestamp, now)
                        # Re-schedule task with the same timestamp
                        self._scheduler.schedule(task)
                        # Sleep until timeout or until a new task awakes the condition
                        self._cond.acquire()
                        self._cond.wait(timeout)
                        self._cond.release()
                    else:
                        # Process tasks in parallel
                        runner.put(self._execute, task)
        except: 
            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while processing tasks in the EC: %s" % err)

            self._state = ECState.FAILED
   
        # Mark EC state as terminated
        if self.ecstate == ECState.RUNNING:
            # Synchronize to get errors if occurred
            runner.sync()
            self._state = ECState.TERMINATED

    def _execute(self, task):
        """ Invoke the callback of the task 'task'

            :param task: Id of the task
            :type task: int

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
            
            self._logger.error("Error occurred while executing task: %s" % err)

            self._stop_scheduler()

            # Propage error to the ParallelRunner
            raise

    def _stop_scheduler(self):
        """ Stop the scheduler and put the EC into a FAILED State.

        """

        # Mark the EC as failed
        self._state = ECState.FAILED

        # Wake up the EC in case it was sleeping
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()

