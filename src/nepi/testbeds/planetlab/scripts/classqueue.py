import collections
import itertools
import random
import re
import sys
import iovec

dstats = collections.defaultdict(int)
astats = collections.defaultdict(int)
dump_count = [0]

_red = True
_size = 1000
_classes = (
    "igmp.ggp.cbt.egp.igp.idrp.mhrp.narp.ospf.eigrp*p1:"
    "udp.st.nvp.rdp.ddp.pvp.mtp.srp.smp.136:"
    "tcp.icmp*4:"
    "ip.gre.etherip.l2tp:"
    "hopopt.shim6.ipv6.ipv6route.ipv6frag.ipv6icmp.ipv6nonxt.ipv6opts*4:"
    "crtp.crudp*8:"
    "*3"
)

def clsmap(cls):
    global _protomap
    if cls in _protomap:
        return _protomap[cls]
    elif cls == "":
        return None
    else:
        return int(cls)

def _parse_classes(classes):
    """
     Class list structure:
       <CLASSLIST> ::= <CLASS> ":" CLASSLIST
                    |  <CLASS>
       <CLASS>     ::= <PROTOLIST> "*" <PRIORITYSPEC>
                    |  <DFLTCLASS>
       <DFLTCLASS> ::= "*" <PRIORITYSPEC>
       <PROTOLIST> ::= <PROTO> "." <PROTOLIST>
                    |  <PROTO>
       <PROTO>     ::= <NAME> | <NUMBER>
       <NAME>      ::= --see http://en.wikipedia.org/wiki/List_of_IP_protocol_numbers --
                       --only in lowercase, with special characters removed--
                       --or see below--
       <NUMBER>    ::= [0-9]+
       <PRIORITYSPEC> ::= <THOUGHPUT> [ "#" <SIZE> ] [ "p" <PRIORITY> ]
       <THOUGHPUT> ::= NUMBER -- default 1
       <PRIORITY>  ::= NUMBER -- default 0
       <SIZE>      ::= NUMBER -- default 1
    """
    classes = map(lambda x:x.split('*',2),classes.split(':'))
    priorex = re.compile(r"(?P<thoughput>\d+)?(?:#(?P<size>\d+))?(?:p(?P<priority>\d+))?")
    for cls in classes:
        if not cls:
            cls.append("")
        if len(cls) < 2:
            cls.append("")
        prio = priorex.match(cls[1])
        if not prio:
            prio = (1,0,1)
        else:
            prio = (
                int(prio.group("thoughput") or 1),
                int(prio.group("priority") or 0),
                int(prio.group("size") or 1),
            )
        cls[1] = prio
        cls[0] = map(clsmap, cls[0].split('.'))
        if not cls[0]:
            cls[0] = [None]
    
    return classes
    

class ClassQueue(object):
    def __init__(self):
        self.size = _size
        self.len = 0

        # Prepare classes
        self.classspec = _parse_classes(_classes)

        self.queues = [ collections.deque() for cls in xrange(len(self.classspec)) ]
        
        self.classmap = dict(
            (proto, cls)
            for cls, (protos, (thoughput, prio, size)) in enumerate(self.classspec)
            for proto in protos
        )

        self.priomap = [
            prio
            for cls in xrange(len(self.classspec))
            for protos, (thoughput, prio, size) in ( self.classspec[cls], )
        ]
        
        self.sizemap = [
            size * _size
            for cls in xrange(len(self.classspec))
            for protos, (thoughput, prio, size) in ( self.classspec[cls], )
        ]
        
        order = [ 
            cls
            for cls, (protos, (thoughput, prio, size)) in enumerate(self.classspec)
            for i in xrange(thoughput)
        ]
        self.order = [
            filter(lambda x : self.priomap[x] == prio, order)
            for prio in reversed(sorted(set(self.priomap)))
        ]
        for order in self.order:
            random.shuffle(order)
        
        if None not in self.classmap:
            raise RuntimeError, "No default class: a default class must be present"
        
        # add retries
        self.queues.append(collections.deque())
        self.priomap.append(-1)
        self.sizemap.append(_size)
        self.order.insert(0, [len(self.queues)-1])
        
        self.classes = set()
        self.clear()
    
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
        self.queues = [ collections.deque() for cls in xrange(len(self.classspec)) ]
    
    def queuefor(self, packet, ord=ord, len=len, classmask=0xEC):
        if len(packet) >= 10:
            proto = ord(packet[9])
            rv = self.classmap.get(proto)
            if rv is None:
                rv = self.classmap.get(None)
        else:
            proto = 0
            rv = self.classmap.get(None)
        return proto, rv, self.sizemap[rv]
    
    def get_packetdrop_p(self, qlen, qsize, packet):
        pdrop = ((qlen * 1.0 / qsize) - 0.5) * 2.0
        pdrop *= pdrop
        return pdrop
    
    def append(self, packet, len=len, dstats=dstats, astats=astats, rng=random.random):
        proto,qi,size = self.queuefor(packet)
        q = self.queues[qi]
        lq = len(q)
        if lq < size:
            dropped = 0
            if lq > (size/2) and _red:
                pdrop = self.get_packetdrop_p(lq, size, packet)
                if rng() < pdrop:
                    dropped = 1
            if not dropped:
                classes = self.classes
                if qi not in classes:
                    classes.add(qi)
                    self.cycle_update = True
                q.append(packet)
                self.len += 1
        # packet dropped
        else:
            dropped = 1
        if _logdropped:
            if dropped:
                dstats[proto] += 1
            else:
                astats[proto] += 1
            self.dump_stats()

    def appendleft(self, packet):
        self.queues[-1].append(packet)
        self.len += 1
    
    def pop(self, xrange=xrange, len=len, iter=iter, pop=collections.deque.pop):
        return self.popleft(pop=pop)
    
    def popleft(self, xrange=xrange, len=len, iter=iter, enumerate=enumerate, zip=zip, pop=collections.deque.popleft):
        queues = self.queues
        classes = self.classes

        if len(classes)==1:
            # shortcut for non-tos traffic
            rv = pop(queues[iter(classes).next()])
            self.len -= 1
            return rv

        if self.cycle_update:
            cycle = [
                filter(classes.__contains__, order)
                for order in self.order
            ]
            self.cycle = map(itertools.cycle, cycle)
            self.cyclelen = map(len,cycle)
            self.cycle_update = False
        
        for prio, (cycle, cyclelen) in enumerate(zip(self.cycle, self.cyclelen)):
            cycle = cycle.next
            for i in xrange(cyclelen):
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

    def dump_stats(self, astats=astats, dstats=dstats, dump_count=dump_count):
        if dump_count[0] >= 10000:
            dstatsstr = "".join(['%s:%s\n' % (key, value) for key, value in dstats.items()])
            astatsstr = "".join(['%s:%s\n' % (key, value) for key, value in astats.items()])
            fd = open('dropped_stats', 'w')
            iovec.writev(fd.fileno(), "Dropped:\n", dstatsstr, "Accepted:\n", astatsstr)
            fd.close()
            dump_count[0] = 0
        else:
            dump_count[0] += 1

queueclass = ClassQueue

def init(size = 1000, classes = _classes, logdropped = 'False', red = True):
    global _size, _classes, _logdropped
    _size = int(size)
    _classes = classes
    _red = red
    _logdropped = logdropped.lower() in ('true','1','on')
    
    if _logdropped:
        # Truncate stats
        open('dropped_stats', 'w').close()

_protomap = {
    '3pc'	:	34,
    'an'	:	107,
    'ah'	:	51,
    'argus'	:	13,
    'aris'	:	104,
    'ax25'	:	93,
    'bbn-rcc-mon'	:	10,
    'bna'	:	49,
    'brsatmon'	:	76,
    'cbt'	:	7,
    'cftp'	:	62,
    'chaos'	:	16,
    'compaqpeer'	:	110,
    'cphb'	:	73,
    'cpnx'	:	72,
    'crtp'	:	126,
    'crudp'	:	127,
    'dccp'	:	33,
    'dcn-meas'	:	19,
    'ddp'	:	37,
    'ddx'	:	116,
    'dgp'	:	86,
    'egp'	:	8,
    'eigrp'	:	88,
    'emcon'	:	14,
    'encap'	:	98,
    'esp'	:	50,
    'etherip'	:	97,
    'fc'	:	133,
    'fire'	:	125,
    'ggp'	:	3,
    'gmtp'	:	100,
    'gre'	:	47,
    'hip'	:	139,
    'hmp'	:	20,
    'hopopt'	:	0,
    'iatp'	:	117,
    'icmp'	:	1,
    'idpr'	:	35,
    'idprcmtp'	:	38,
    'idrp'	:	45,
    'ifmp'	:	101,
    'igmp'	:	2,
    'igp'	:	9,
    'il'	:	40,
    'inlsp'	:	52,
    'ip'	:	4,
    'ipcomp'	:	108,
    'ipcv'	:	71,
    'ipip'	:	94,
    'iplt'	:	129,
    'ippc'	:	67,
    'iptm'	:	84,
    'ipv6'	:	41,
    'ipv6frag'	:	44,
    'ipv6icmp'	:	58,
    'ipv6nonxt'	:	59,
    'ipv6opts'	:	60,
    'ipv6route'	:	43,
    'ipxinip'	:	111,
    'irtp'	:	28,
    'isoip'	:	80,
    'isotp4'	:	29,
    'kryptolan'	:	65,
    'l2tp'	:	115,
    'larp'	:	91,
    'leaf1'	:	25,
    'leaf2'	:	26,
    'manet'	:	138,
    'meritinp'	:	32,
    'mfensp'	:	31,
    'mhrp'	:	48,
    'micp'	:	95,
    'mobile'	:	55,
    'mtp'	:	92,
    'mux'	:	18,
    'narp'	:	54,
    'netblt'	:	30,
    'nsfnetigp'	:	85,
    'nvp'	:	11,
    'ospf'	:	89,
    'pgm'	:	113,
    'pim'	:	103,
    'pipe'	:	131,
    'pnni'	:	102,
    'prm'	:	21,
    'ptp'	:	123,
    'pup'	:	12,
    'pvp'	:	75,
    'qnx'	:	106,
    'rdp'	:	27,
    'rsvp'	:	46,
    'rvd'	:	66,
    'satexpak'	:	64,
    'satmon'	:	69,
    'sccsp'	:	96,
    'scps'	:	105,
    'sctp'	:	132,
    'sdrp'	:	42,
    'securevmtp'	:	82,
    'shim6'	:	140,
    'skip'	:	57,
    'sm'	:	122,
    'smp'	:	121,
    'snp'	:	109,
    'spriterpc'	:	90,
    'sps'	:	130,
    'srp'	:	119,
    'sscopmce'	:	128,
    'st'	:	5,
    'stp'	:	118,
    'sunnd'	:	77,
    'swipe'	:	53,
    'tcf'	:	87,
    'tcp'	:	6,
    'tlsp'	:	56,
    'tp'	:	39,
    'trunk1'	:	23,
    'trunk2'	:	24,
    'ttp'	:	84,
    'udp'	:	17,
    'uti'	:	120,
    'vines'	:	83,
    'visa'	:	70,
    'vmtp'	:	81,
    'vrrp'	:	112,
    'wbexpak'	:	79,
    'wbmon'	:	78,
    'wsn'	:	74,
    'xnet'	:	15,
    'xnsidp'	:	22,
    'xtp'	:	36
}

