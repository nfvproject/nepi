#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import Queue
import traceback
import sys

N_PROCS = None

class ParallelMap(object):
    def __init__(self, maxthreads = None, maxqueue = None, results = True):
        global N_PROCS
        
        if maxthreads is None:
            if N_PROCS is None:
                try:
                    f = open("/proc/cpuinfo")
                    try:
                        N_PROCS = sum("processor" in l for l in f)
                    finally:
                        f.close()
                except:
                    pass
            maxthreads = N_PROCS
        
        if maxthreads is None:
            maxthreads = 4

        self.queue = Queue.Queue(maxqueue or 0)
    
        self.workers = [ threading.Thread(target = self.worker) 
                         for x in xrange(maxthreads) ]
        
        self.delayed_exceptions = []
        
        if results:
            self.rvqueue = Queue.Queue()
        else:
            self.rvqueue = None
        
    def put(self, callable, *args, **kwargs):
        self.queue.put((callable, args, kwargs))
    
    def put_nowait(self, callable, *args, **kwargs):
        self.queue.put_nowait((callable, args, kwargs))

    def start(self):
        for thread in self.workers:
            thread.start()
    
    def join(self):
        for thread in self.workers:
            # That's the shutdown signal
            self.queue.put(None)
            
        self.queue.join()
        for thread in self.workers:
            thread.join()
        
        if self.delayed_exceptions:
            typ,val,loc = self.delayed_exceptions[0]
            raise typ,val,loc
        
    def worker(self):
        while True:
            task = self.queue.get()
            if task is None:
                self.queue.task_done()
                break
            
            try:
                try:
                    callable, args, kwargs = task
                    rv = callable(*args, **kwargs)
                    
                    if self.rvqueue is not None:
                        self.rvqueue.put(rv)
                finally:
                    self.queue.task_done()
            except:
                traceback.print_exc(file = sys.stderr)
                self.delayed_exceptions.append(sys.exc_info())

    def __iter__(self):
        if self.rvqueue is not None:
            while True:
                try:
                    yield self.rvqueue.get_nowait()
                except Queue.Empty:
                    self.queue.join()
                    try:
                        yield self.rvqueue.get_nowait()
                    except Queue.Empty:
                        raise StopIteration
            
    
class ParallelFilter(ParallelMap):
    class _FILTERED:
        pass
    
    def __filter(self, x):
        if self.filter_condition(x):
            return x
        else:
            return self._FILTERED
    
    def __init__(self, filter_condition, maxthreads = None, maxqueue = None):
        super(ParallelFilter, self).__init__(maxthreads, maxqueue, True)
        self.filter_condition = filter_condition

    def put(self, what):
        super(ParallelFilter, self).put(self.__filter, what)
    
    def put_nowait(self, what):
        super(ParallelFilter, self).put_nowait(self.__filter, what)
        
    def __iter__(self):
        for rv in super(ParallelFilter, self).__iter__():
            if rv is not self._FILTERED:
                yield rv

class ParallelRun(ParallelMap):
    def __run(self, x):
        fn, args, kwargs = x
        return fn(*args, **kwargs)
    
    def __init__(self, maxthreads = None, maxqueue = None):
        super(ParallelRun, self).__init__(maxthreads, maxqueue, True)

    def put(self, what, *args, **kwargs):
        super(ParallelRun, self).put(self.__run, (what, args, kwargs))
    
    def put_nowait(self, what, *args, **kwargs):
        super(ParallelRun, self).put_nowait(self.__filter, (what, args, kwargs))


def pmap(mapping, iterable, maxthreads = None, maxqueue = None):
    mapper = ParallelMap(
        maxthreads = maxthreads,
        maxqueue = maxqueue,
        results = True)
    mapper.start()
    for elem in iterable:
        mapper.put(elem)
    return list(mapper)

def pfilter(condition, iterable, maxthreads = None, maxqueue = None):
    filtrer = ParallelFilter(
        condition,
        maxthreads = maxthreads,
        maxqueue = maxqueue)
    filtrer.start()
    for elem in iterable:
        filtrer.put(elem)
    return list(filtrer)

