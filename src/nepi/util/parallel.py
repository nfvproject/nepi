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
            
    
    
