import setclusters
import collections
import itertools
import operator

def classify(requests, partition):
    """
    Takes an iterable over requests and a classification, and classifies the requests
    returning a mapping from their classification (bitmap of applicable partitions) to
    lists of requests.
    
    Params:
    
        requests: iterable over sets of viable candidates for a request
        
        partition: sequence of sets of candidates that forms a partition
            over all available candidates.
    
    Returns:
        
        { str : [requests] }
    """
    rv = collections.defaultdict(list)
    
    for request in requests:
        rv[getClass(request, partition)].append(request)
    
    return dict(rv)

def getClass(set, partition):
    return "".join(
        map("01".__getitem__, [
            bool(set & part)
            for part in partition
        ])
    )
    

def isSubclass(superclass, subclass):
    """
    Returns True iff 'superclass' includes all elements of 'subclass'
    
    >>> isSubclass("1100","1000")
    True
    >>> isSubclass("1100","1100")
    True
    >>> isSubclass("0000","0001")
    False
    """
    for superbit, subbit in itertools.izip(superclass, subclass):
        if subbit and not superbit:
            return False
    else:
        return True

def classContains(clz, partIndex):
    return clz[partIndex] == "1"

def classCardinality(clz, partition = None):
    if not partition:
        return sum(itertools.imap("1".__eq__, clz))
    else:
        return sum(len(part) for bit,part in zip(clz,partition) 
                   if bit == "1" )

def classMembers(clz, partition):
    return reduce(operator.or_, classComponents(clz, partition), set())

def classComponents(clz, partition):
    return [
        partition[i]
        for i,bit in enumerate(clz)
        if bit == "1"
    ]


