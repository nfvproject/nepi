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
# Author: Claudio Freire <claudio-daniel.freire@inria.fr>
#

# A.Q. TODO: BUG FIX THREADCACHE. Not needed!! remove it completely!

import threading
import Queue
import traceback
import sys
import os

N_PROCS = None

#THREADCACHE = []
#THREADCACHEPID = None

class WorkerThread(threading.Thread):
    class QUIT:
        pass
    class REASSIGNED:
        pass
    
    def run(self):
        while True:
            task = self.queue.get()
            if task is None:
                self.done = True
                self.queue.task_done()
                continue
            elif task is self.QUIT:
                self.done = True
                self.queue.task_done()
                break
            elif task is self.REASSIGNED:
                continue
            else:
                self.done = False
            
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
    
    def waitdone(self):
        while not self.queue.empty() and not self.done:
            self.queue.join()
    
    def attach(self, queue, rvqueue, delayed_exceptions):
        if self.isAlive():
            self.waitdone()
            oldqueue = self.queue
        self.queue = queue
        self.rvqueue = rvqueue
        self.delayed_exceptions = delayed_exceptions
        if self.isAlive():
            oldqueue.put(self.REASSIGNED)
    
    def detach(self):
        if self.isAlive():
            self.waitdone()
            self.oldqueue = self.queue
        self.queue = Queue.Queue()
        self.rvqueue = None
        self.delayed_exceptions = []
    
    def detach_signal(self):
        if self.isAlive():
            self.oldqueue.put(self.REASSIGNED)
            del self.oldqueue
        
    def quit(self):
        self.queue.put(self.QUIT)
        self.join()

class ParallelMap(object):
    def __init__(self, maxthreads = None, maxqueue = None, results = True):
        global N_PROCS
        #global THREADCACHE
        #global THREADCACHEPID
        
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

        self.delayed_exceptions = []
        
        if results:
            self.rvqueue = Queue.Queue()
        else:
            self.rvqueue = None
        
        # Check threadcache
        #if THREADCACHEPID is None or THREADCACHEPID != os.getpid():
        #    del THREADCACHE[:]
        #    THREADCACHEPID = os.getpid()
    
        self.workers = []
        for x in xrange(maxthreads):
            t = None
            #if THREADCACHE:
            #    try:
            #        t = THREADCACHE.pop()
            #    except:
            #        pass
            if t is None:
                t = WorkerThread()
                t.setDaemon(True)
            else:
                t.waitdone()
            t.attach(self.queue, self.rvqueue, self.delayed_exceptions)
            self.workers.append(t)
    
    def __del__(self):
        self.destroy()
    
    def destroy(self):
        # Check threadcache
        #global THREADCACHE
        #global THREADCACHEPID
        #if THREADCACHEPID is None or THREADCACHEPID != os.getpid():
        #    del THREADCACHE[:]
        #    THREADCACHEPID = os.getpid()

        for worker in self.workers:
            worker.waitdone()
        for worker in self.workers:
            worker.detach()
        for worker in self.workers:
            worker.detach_signal()
        for worker in self.workers:
            worker.quit()

        # TO FIX:
        # THREADCACHE.extend(self.workers)

        del self.workers[:]
        
    def put(self, callable, *args, **kwargs):
        self.queue.put((callable, args, kwargs))
    
    def put_nowait(self, callable, *args, **kwargs):
        self.queue.put_nowait((callable, args, kwargs))

    def start(self):
        for thread in self.workers:
            if not thread.isAlive():
                thread.start()
    
    def join(self):
        for thread in self.workers:
            # That's the sync signal
            self.queue.put(None)
            
        self.queue.join()
        for thread in self.workers:
            thread.waitdone()
        
        if self.delayed_exceptions:
            typ,val,loc = self.delayed_exceptions[0]
            del self.delayed_exceptions[:]
            raise typ,val,loc
        
        self.destroy()
    
    def sync(self):
        self.queue.join()
        if self.delayed_exceptions:
            typ,val,loc = self.delayed_exceptions[0]
            del self.delayed_exceptions[:]
            raise typ,val,loc
        
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
    rv = list(mapper)
    mapper.join()
    return rv

def pfilter(condition, iterable, maxthreads = None, maxqueue = None):
    filtrer = ParallelFilter(
        condition,
        maxthreads = maxthreads,
        maxqueue = maxqueue)
    filtrer.start()
    for elem in iterable:
        filtrer.put(elem)
    rv = list(filtrer)
    filtrer.join()
    return rv

