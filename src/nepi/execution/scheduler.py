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

import itertools
import heapq

class TaskStatus:
    NEW = 0
    DONE = 1
    ERROR = 2


class Task(object):
    """ This class is to define a task, that is represented by an id,
    an execution time 'timestamp' and an action 'callback """

    def __init__(self, timestamp, callback):
        self.id = None 
        self.timestamp = timestamp
        self.callback = callback
        self.result = None
        self.status = TaskStatus.NEW

class HeapScheduler(object):
    """ Create a Heap Scheduler.

    .. note::

        This class is thread safe.
        All calls to C Extensions are made atomic by the GIL in the CPython implementation.
        heapq.heappush, heapq.heappop, and list access are therefore thread-safe.

    """

    def __init__(self):
        super(HeapScheduler, self).__init__()
        self._queue = list() 
        self._valid = set()
        self._idgen = itertools.count(1)

    def schedule(self, task):
        """ Add the task 'task' in the heap of the scheduler

        :param task: task that need to be schedule
        :type task: task
        """
        if task.id == None:
            task.id = self._idgen.next()
        entry = (task.timestamp, task.id, task)
        self._valid.add(task.id)
        heapq.heappush(self._queue, entry)
        return task

    def remove(self, tid):
        """ Remove a task form the heap

        :param tid: Id of the task that need to be removed
        :type tid: int
        """
        try:
            self._valid.remove(tid)
        except:
            pass

    def next(self):
        """ Get the next task in the scheduler

        """
        while self._queue:
            try:
                timestamp, tid, task = heapq.heappop(self._queue)
                if tid in self._valid:
                    self.remove(tid)
                    return task
            except IndexError:
                # heap empty
                pass
        return None

