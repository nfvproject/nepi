import logging
import os
import sys
import time
import threading

from neco.util import guid
from neco.util.timefuncs import strfnow, strfdiff, strfvalid 
from neco.execution.resource import ResourceFactory
from neco.execution.scheduler import HeapScheduler, Task, TaskStatus
from neco.util.parallel import ParallelRun

class ExperimentController(object):
    def __init__(self, root_dir = "/tmp", loglevel = 'error'): 
        super(ExperimentController, self).__init__()
        # root directory to store files
        self._root_dir = root_dir

        # generator of globally unique ids
        self._guid_generator = guid.GuidGenerator()
        
        # Resource managers
        self._resources = dict()

        # Scheduler
        self._scheduler = HeapScheduler()

        # Tasks
        self._tasks = dict()

        # Event processing thread
        self._stop = False
        self._cond = threading.Condition()
        self._thread = threading.Thread(target = self._process)
        self._thread.start()

        # Logging
        self._logger = logging.getLogger("neco.execution.ec")
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    def get_task(self, tid):
        return self._tasks.get(tid)

    def get_resource(self, guid):
        return self._resources.get(guid)

    @property
    def resources(self):
        return self._resources.keys()

    def register_resource(self, rtype, guid = None, creds = None):
        # Get next available guid
        guid = self._guid_generator.next(guid)
        
        # Instantiate RM
        rm = ResourceFactory.create(rtype, self, guid, creds)

        # Store RM
        self._resources[guid] = rm

        return guid

    def get_attributes(self, guid):
        rm = self.get_resource(guid)
        return rm.get_attributes()

    def get_filters(self, guid):
        rm = self.get_resource(guid)
        return rm.get_filters()

    def register_connection(self, guid1, guid2):
        rm1 = self.get_resource(guid1)
        rm2 = self.get_resource(guid2)

        rm1.connect(guid2)
        rm2.connect(guid1)

    def discover_resource(self, guid, filters):
        rm = self.get_resource(guid)
        return rm.discover(filters)

    def provision_resource(self, guid, filters):
        rm = self.get_resource(guid)
        return rm.provision(filters)

    def register_start(self, group1, time, after_status, group2):
        if isinstance(group1, int):
            group1 = list[group1]
        if isinstance(group2, int):
            group2 = list[group2]

        for guid1 in group1:
            for guid2 in group2:
                rm = self.get_resource(guid)
                rm.start_after(time, after_status, guid2)

    def register_stop(self, group1, time, after_status, group2):
        if isinstance(group1, int):
            group1 = list[group1]
        if isinstance(group2, int):
            group2 = list[group2]

        for guid1 in group1:
            for guid2 in group2:
                rm = self.get_resource(guid)
                rm.stop_after(time, after_status, guid2)

    def register_set(self, name, value, group1, time, after_status, group2):
        if isinstance(group1, int):
            group1 = list[group1]
        if isinstance(group2, int):
            group2 = list[group2]

        for guid1 in group1:
            for guid2 in group2:
                rm = self.get_resource(guid)
                rm.set_after(name, value, time, after_status, guid2)

    def get(self, guid, name):
        rm = self.get_resource(guid)
        return rm.get(name)

    def set(self, guid, name, value):
        rm = self.get_resource(guid)
        return rm.set(name, value)

    def status(self, guid):
        rm = self.get_resource(guid)
        return rm.status()

    def stop(self, guid):
        rm = self.get_resource(guid)
        return rm.stop()

    def deploy(self, group = None, start_when_all_ready = True):
        if not group:
            group = self.resources

        threads = []
        for guid in group:
            rm = self.get_resource(guid)

            kwargs = {'target': rm.deploy}
            if start_when_all_ready:
                towait = list(group)
                towait.remove(guid)
                kwargs['args'] = towait

            thread = threading.Thread(kwargs)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def release(self, group = None):
        if not group:
            group = self.resources

        threads = []
        for guid in group:
            rm = self.get_resource(guid)
            thread = threading.Thread(target=rm.release)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def shutdown(self):
        self.release()
        
        self._stop = True
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        if self._thread.is_alive():
           self._thread.join()

    def schedule(self, date, callback, track = False):
        """ Schedule a callback to be executed at time date.

            date    string containing execution time for the task.
                    It can be expressed as an absolute time, using
                    timestamp format, or as a relative time matching
                    ^\d+.\d+(h|m|s|ms|us)$

            callback    code to be executed for the task. Must be a
                        Python function, and receives args and kwargs
                        as arguments.

            track   if set to True, the task will be retrivable with
                    the get_task() method
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
        runner = ParallelRun(maxthreads = 50)
        runner.start()

        try:
            while not self._stop:
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

    def _execute(self, task):
        # Invoke callback
        task.status = TaskStatus.DONE

        try:
            task.result = task.callback()
        except:
            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while executing event: %s" % err)

            task.result = err
            task.status = TaskStatus.ERROR

