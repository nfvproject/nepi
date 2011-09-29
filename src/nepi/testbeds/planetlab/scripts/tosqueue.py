import collections
import itertools
import random

_size = 1000

class TOSQueue(object):
    def __init__(self):
        self.size = _size
        self.queues = collections.defaultdict(collections.deque)
        self.retries = collections.deque()
        self.len = 0
        
        # Prepare collection order
        self.order = [
            (precedence << 5) | (thoughput << 3) | (reliability << 2)
            for precedence in xrange(7,-1,-1) 
            for thoughput in (0,1,1)
            for reliability in (0,1)
        ]
        random.shuffle(self.order)
        
        self.cycle = None
        self.cyclelen = None
        self.cycle_update = True
        self.classes = set()
    
    def __nonzero__(self):
        return self.len > 0
    
    def __len__(self):
        return self.len
    
    def clear(self):
        self.classes.clear()
        self.cycle = None
        self.cyclelen = None
        self.cycle_update = True
        self.len = 0
        self.queues.clear()
        self.retries = collections.deque()
    
    def queuefor(self, packet, ord=ord, len=len, classmask=0xEC):
        if len(packet) >= 2:
            tos = ord(packet[1])
            return (tos & classmask, tos & 0x10)
        else:
            return (0,0)
    
    def append(self, packet, len=len):
        qi,urgent = self.queuefor(packet)
        q = self.queues[qi]
        if len(q) < _size:
            classes = self.classes
            if qi not in classes:
                classes.add(qi)
                self.cycle_update = True
            if urgent:
                q.appendleft(packet)
            else:
                q.append(packet)
            self.len += 1

    def appendleft(self, packet):
        self.retries.append(packet)
        self.len += 1
    
    def pop(self, xrange=xrange, len=len, iter=iter, pop=collections.deque.pop):
        return self.popleft(pop=pop)
    
    def popleft(self, xrange=xrange, len=len, iter=iter, pop=collections.deque.popleft):
        if self.retries:
            rv = pop(self.retries)
            self.len -= 1
            return rv
        
        queues = self.queues
        classes = self.classes
        
        if len(classes)==1:
            # shortcut for non-tos traffic
            rv = pop(queues[iter(classes).next()])
            self.len -= 1
            return rv
        
        if self.cycle_update:
            cycle = filter(classes.__contains__, self.order)
            self.cycle = itertools.cycle(cycle)
            self.cyclelen = len(cycle)
            self.cycle_update = False

        cycle = self.cycle.next
        for i in xrange(self.cyclelen):
            qi = cycle()
            if qi in classes:
                q = queues[qi]
                if q:
                    rv = pop(q)
                    self.len -= 1
                    return rv
                else:
                    # Needs to update the cycle
                    classes.remove(qi)
                    self.cycle_update = True
        else:
            raise IndexError, "pop from an empty queue"

queueclass = TOSQueue

def init(size):
    global _size
    _size = size

