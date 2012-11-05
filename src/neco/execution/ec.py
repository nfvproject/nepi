import logging
import os
import sys
import threading
import time
import weakref

from neco.execution import scheduler, tasks
from neco.util import guid
from neco.util.timefuncs import strfnow, strfdiff, strfvalid 
from neco.util.parallel import ParallelRun

_reschedule_delay = "0.1s"

class ExperimentController(object):
    def __init__(self, root_dir = "/tmp", loglevel = 'error'):
        super(ExperimentController, self).__init__()
        # root directory to store files
        self._root_dir = root_dir

        # generator of globally unique ids
        self._guid_generator = guid.GuidGenerator()
        
        # Scheduler
        self._scheduler = scheduler.HeapScheduler()

        # Tasks
        self._tasks = dict()
 
        # Resources
        self._resources = dict()
       
        # Event processing thread
        self._cond = threading.Condition()
        self._stop = False
        self._thread = threading.Thread(target = self._process_tasks)
        self._thread.start()
       
        # Logging
        self._logger = logging.getLogger("neco.execution.ec")
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    def resource(self, guid):
        return self._resources.get(guid)

    def terminate(self):
        self._stop = True
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        if self._thread.is_alive():
           self._thread.join()

    def task_info(self, tid):
        task = self._tasks.get(tid)
        if not task:
            return (None, None)
        return (task.status, task.result)

    def schedule(self, date, callback, args = None, kwargs = None):
        """
            date    string containing execution time for the task.
                    It can be expressed as an absolute time, using
                    timestamp format, or as a relative time matching
                    ^\d+.\d+(h|m|s|ms|us)$

            callback    code to be executed for the task. Must be a
                        Python function, and receives args and kwargs
                        as arguments.
                        The callback will always be invoked passing a 
                        week reference to the controller as first 
                        argument.
                        The callback must return a (status, result) 
                        tuple where status is one of : 
                        task.TaskStatus.FAIL, 
                        task.TaskStatus.SUCCESS, 
                        task.TaskStatus.RETRY, 
                        task.TaskStatus.RECYCLE 
        """
        timestamp = strfvalid(date)
        
        args = args or []
        kwargs = kwargs or {}

        task = tasks.Task(timestamp, callback, args, kwargs)
        task = self._schedule(task)

        self._tasks[task.id] = task

        return task.id

    ###########################################################################
    #### Internal methods
    ###########################################################################

    def _schedule(self, task):
        task = self._scheduler.schedule(task)

        # Notify condition to wake up the processing thread
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        return task
     
    def _process_tasks(self):
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
                        runner.put(self._execute_task, task)
        except:  
            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while processing tasks in the EC: %s" % err)
 
    def _execute_task(self, task):
        # Invoke callback
        ec = weakref.ref(self)
        try:
            (task.status, task.result) = task.callback(ec, *task.args, **task.kwargs)
        except:
            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while executing event: %s" % err)

            # task marked as FAIL
            task.status = tasks.TaskStatus.FAIL
            task.result = err

        if task.status == tasks.TaskStatus.RETRY:
            # Re-schedule same task in the near future
            task.timestamp = strfvalid(_reschedule_delay)
            self._schedule(task)
        elif task.status == tasks.TaskStatus.RECYCLE:
            # Re-schedule t in the future
            timestamp = strfvalid(task.result)
            self.schedule(timestamp, task.callback, task.args, task.kwargs)

