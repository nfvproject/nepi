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
#         Alina Quereilhac <alina.quereilhac@inria.fr>
#

import threading
import Queue
import traceback
import sys
import os

N_PROCS = None

class WorkerThread(threading.Thread):
    class QUIT:
        pass

    def run(self):
        while True:
            task = self.queue.get()

            if task is self.QUIT:
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

    def attach(self, queue, rvqueue, delayed_exceptions):
        self.queue = queue
        self.rvqueue = rvqueue
        self.delayed_exceptions = delayed_exceptions
   
    def quit(self):
        self.queue.put(self.QUIT)

class ParallelRun(object):
    def __init__(self, maxthreads = None, maxqueue = None, results = True):
        self.maxqueue = maxqueue
        self.maxthreads = maxthreads
        
        self.queue = Queue.Queue(self.maxqueue or 0)
        
        self.delayed_exceptions = []
        
        if results:
            self.rvqueue = Queue.Queue()
        else:
            self.rvqueue = None
    
        self.initialize_workers()

    def initialize_workers(self):
        global N_PROCS

        maxthreads = self.maxthreads
       
        # Compute maximum number of threads allowed by the system
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
 
        self.workers = []

        # initialize workers
        for x in xrange(maxthreads):
            worker = WorkerThread()
            worker.attach(self.queue, self.rvqueue, self.delayed_exceptions)
            worker.setDaemon(True)

            self.workers.append(worker)
    
    def __del__(self):
        self.destroy()

    def empty(self):
        while True:
            try:
                self.queue.get(block = False)
                self.queue.task_done()
            except Queue.Empty:
                break
  
    def destroy(self):
        self.join()

        del self.workers[:]
        
    def put(self, callable, *args, **kwargs):
        self.queue.put((callable, args, kwargs))
    
    def put_nowait(self, callable, *args, **kwargs):
        self.queue.put_nowait((callable, args, kwargs))

    def start(self):
        for worker in self.workers:
            if not worker.isAlive():
                worker.start()
    
    def join(self):
        # Wait until all queued tasks have been processed
        self.queue.join()

        for worker in self.workers:
            worker.quit()

        for worker in self.workers:
            worker.join()
    
    def sync(self):
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
            
