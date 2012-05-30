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
        t0 = time.time()
        with open(self.outpath, "w+") as outfile:
            outfile.write(",".join(
                ["time"]
                + map("q%02dlen".__mod__, xrange(len(self.queues)))
                + map("q%02ddrops".__mod__, xrange(len(self.queues)))
                + map("q%02daccepts".__mod__, xrange(len(self.queues)))
            ))
            
            while not self._terminate:
                self._event.wait(1)
                if self._terminate:
                    break
                
                self._event.clear()
                
                queuelens = map(len,self.queues)
                
                queuedrops = list(self.drops)
                self.drops[:] = [0] * len(self.drops)
                
                queueaccepts = list(self.accepts)
                self.accepts[:] = [0] * len(self.accepts)
                
                outfile.write(",".join(
                    [str(time.time)]
                    + map(str, queuelens)
                    + map(str, queuedrops)
                    + map(str, queueaccepts)
                ))
                outfile.flush()
            
    def terminate(self):
        self._terminate = True
        self.wakeup()
    
    def wakeup(self):
        self._event.set()

class LoggingClassQueue(classqueue.ClassQueue):
    def __init__(self):
        self.accepts = []
        self.drops = []
        super(LoggingClassQueue, self).__init__()
        
        # Prepare logger thread
        self.logger = QueueLogger(self.queues, self.drops, self.accepts, _outpath)
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
        
        return dropped

queueclass = LoggingClassQueue

def init(outpath="output", **kw):
    global _outpath
    _outpath = outpath
    classqueue.init(**kw)
