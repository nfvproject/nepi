import itertools
import heapq

class Task(object):
    def __init__(self, timestamp, callback):
        self.id = None 
        self.timestamp = timestamp
        self.callback = callback

class HeapScheduler(object):
    """ This class is thread safe.
    All calls to C Extensions are made atomic by the GIL in the CPython implementation.
    heapq.heappush, heapq.heappop, and list access are therefore thread-safe """

    def __init__(self):
        super(HeapScheduler, self).__init__()
        self._queue = list() 
        self._valid = set()
        self._idgen = itertools.count(1)

    def schedule(self, task):
        if task.id == None:
            task.id = self._idgen.next()
        entry = (task.timestamp, task.id, task)
        self._valid.add(task.id)
        heapq.heappush(self._queue, entry)
        return task

    def remove(self, tid):
        try:
            self._valid.remove(tid)
        except:
            pass

    def next(self):
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

