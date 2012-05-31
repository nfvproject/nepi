import collections
import itertools
import random
import re
import sys
import iovec
import threading
import time
import classqueue

_outpath = "output"
_interval = 0

class QueueLogger(threading.Thread):
    def __init__(self, queues, drops, accepts, outpath):
        super(QueueLogger,self).__init__()
        self.queues = queues
        self.drops = drops
        self.accepts = accepts
        self.outpath = outpath
        self.setDaemon(True)
        self._event = threading.Event()
        self._terminate = False
    
    def run(self):
        if _interval > 0:
            interval = _interval
        else:
            interval = 1
        
        t0 = time.time()
        with open(self.outpath, "w") as outfile:
            outfile.writelines((",".join(
                ["time"]
                + map("q%02dlen".__mod__, xrange(len(self.queues)))
                + map("q%02ddrops".__mod__, xrange(len(self.queues)))
                + map("q%02daccepts".__mod__, xrange(len(self.queues)))
            ), "\n"))
            
            while not self._terminate:
                self._event.wait(interval)
                if self._terminate:
                    break
                
                self._event.clear()
                
                queuelens = map(len,self.queues)
                
                queuedrops = list(self.drops)
                self.drops[:] = [0] * len(self.drops)
                
                queueaccepts = list(self.accepts)
                self.accepts[:] = [0] * len(self.accepts)
                
                outfile.writelines((",".join(
                    [str(time.time()-t0)]
                    + map(str, queuelens)
                    + map(str, queuedrops)
                    + map(str, queueaccepts)
                ), "\n"))
                outfile.flush()
            
    def terminate(self):
        self._terminate = True
        self.wakeup()
    
    def wakeup(self):
        self._event.set()

class LoggingClassQueue(classqueue.ClassQueue):
    outpath_suffix = itertools.cycle(('_f','_b'))
    
    def __init__(self):
        self.accepts = []
        self.drops = []
        super(LoggingClassQueue, self).__init__()
        
        # Prepare logger thread
        self.logger = QueueLogger(self.queues, self.drops, self.accepts, _outpath+self.outpath_suffix.next())
        self.logger.start()
    
    def __del__(self):
        self.logger.terminate()

    def clear(self):
        super(LoggingClassQueue, self).clear()
        self.accepts[:] = [0] * len(self.queues)
        self.drops[:] = [0] * len(self.queues)
    
    def append(self, packet):
        proto,qi,size = self.queuefor(packet)
        dropped = super(LoggingClassQueue, self).append(packet)
        
        if dropped:
            self.drops[qi] += 1
        else:
            self.accepts[qi] += 1
        
        if _interval == 0:
            self.logger.wakeup()
        
        return dropped

queueclass = LoggingClassQueue

def init(outpath="output", interval=0, **kw):
    global _outpath, _interval
    _outpath = outpath
    _interval = interval
    classqueue.init(**kw)
