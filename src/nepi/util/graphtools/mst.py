import random
import bisect

def mst(nodes, connected, 
        maxsoftbranching = None,
        maxbranching = None, 
        root = None,
        untie = lambda l : iter(l).next()):
    """
    Returns an iterator over pairs (Node, Parent)
    which form the spanning tree.
    
    Params:
    
        nodes: a list of nodes (can be anything)
        
        connected: a callable that takes two nodes
            and returns either an edge weight (one
            that can be compared with '<' with other
            edge weights) or None if they're not
            connected.
        
        maxbranching: the maximum number of branches
            (children) allowed for a node. None for
            no limit.
            When maxbranching is used, the algorithm
            implemented here gives no guarantee
            of optimality (the spanning tree may not
            be the minimum), as that problem becomes
            NP-hard and we want a quick answer.
        
        maxsoftbranching: soft branching limit.
            The algorithm is allowed to break it
            if it has no other choice. Trees build with
            soft branching limits are usually less
            balanced than when using hard limits,
            but the computation takes a lot less time.
        
        root: the desired root of the spanning tree,
            or None to pick a random one.
        
        untie: a callable that, given an iterable
            of candidate entries of equal weight for
            the selection to be made, picks one to
            be added to the spanning tree. The default
            picks arbitrarily.
            Entries are of the form (<weight>,<from>,<to>)
            with <from> and <to> being indices in the
            nodes array
    """
    
    if not nodes:
        return
        
    if root is None:
        root = random.sample(nodes, 1)[0]
    
    # We want the root's index
    root = nodes.index(root)
    
    # Unpicked nodes, nodes we still have to add.
    unpicked = set(xrange(len(nodes)))
    
    # Distance maps
    #   We need:
    #       min distance to picked node
    #       which picked node
    #   Or None if it was a picked or unconnected node
    
    N = len(nodes)
    distance = [None] * N
    which    = [None] * N
    
    # Count branches
    branching = [0] * N
    
    # Initialize with distances to root
    def update_distance_map(fornode):
        ref = nodes[fornode]
        for other, prevdistance in enumerate(distance):
            other_node = nodes[other]
            d = connected(ref, other_node)
            if d is not None:
                if prevdistance is None or prevdistance > d:
                    distance[other] = d
                    which[other] = fornode
        distance[fornode] = None
        which[fornode] = None
    
    update_distance_map(root)
    unpicked.remove(root)
    
    # Add remaining nodes, yield edges
    def minrange(dsorted):
        return dsorted[:bisect.bisect(dsorted, (dsorted[0][0], N, N))]
        
    needsrebuild = False
    while unpicked:
        # Rebuild the distance map if needed
        # (ie, when a node in the partial MST is no longer
        # a candidate for adjoining because of saturation)
        if needsrebuild:
            print "Rebuilding distance map..."
            distance = [None] * N
            which    = [None] * N
            for n in xrange(N):
                if n not in unpicked and branching[n] < maxbranching:
                    update_distance_map(n)
        
        # Pick the closest unpicked node
        dsorted = [(d,i,w) for i,(d,w) in enumerate(zip(distance, which)) 
                   if d is not None 
                      and i in unpicked
                      and (maxbranching is None or branching[w] < maxbranching)
                      and (maxsoftbranching is None or branching[w] < maxsoftbranching)]
        if not dsorted and maxsoftbranching is not None:
            dsorted = [(d,i,w) for i,(d,w) in enumerate(zip(distance, which)) 
                       if d is not None 
                          and i in unpicked
                          and (maxbranching is None or branching[w] < maxbranching)]
        if not dsorted:
            raise AssertionError, "Unconnected graph"
        
        dsorted.sort()
        dsorted = minrange(dsorted)
        
        if len(dsorted) > 1:
            winner = untie(dsorted)
        elif dsorted:
            winner = dsorted[0]
        else:
            raise AssertionError, "Unconnected graph"
        
        weight, edgefrom, edgeto = winner
        
        branching[edgeto] += 1
        
        if maxbranching is not None and branching[edgeto] == maxbranching:
            needsrebuild = True
        
        # Yield edge, update distance map to account
        # for the picked node
        yield (nodes[edgefrom], nodes[edgeto])
        
        update_distance_map(edgefrom)
        unpicked.remove(edgefrom)


