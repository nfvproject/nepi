import itertools
import collections

def disjoint_sets(*sets):
    """
    Given a series of sets S1..SN, computes disjoint clusters C1..CM
    such that C1=U Sc1..Sc1', C2=U Sc2..Sc2', ... CM=ScM..ScM'
    and any component of Ci is disjoint against any component of Cj
    for i!=j
    
    The result is given in terms of the component sets, so C1 is given
    as the sequence Sc1..Sc1', etc.
    
    Example:
    
    >>> disjoint_sets( set([1,2,4]), set([2,3,4,5]), set([4,5]), set([6,7]), set([7,8]) )
    [[set([1, 2, 4]), set([4, 5]), set([2, 3, 4, 5])], [set([6, 7]), set([8, 7])]]

    >>> disjoint_sets( set([1]), set([2]), set([3]) )
    [[set([1])], [set([2])], [set([3])]]

    """
    
    # Pseudo:
    #
    # While progress is made:
    #   - Join intersecting clusters
    #   - Track their components
    #   - Replace sets with the new clusters, restart
    cluster_components = [ [s] for s in sets ]
    clusters = [s.copy() for s in sets]
    
    changed = True
    while changed:
        changed = False
        
        for i,s in enumerate(clusters):
            for j in xrange(len(clusters)-1,i,-1):
                cluster = clusters[j]
                if cluster & s:
                    changed = True
                    cluster.update(s)
                    cluster_components[i].extend(cluster_components[j])
                    del cluster_components[j]
                    del clusters[j]
        
    return cluster_components

def disjoint_partition(*sets):
    """
    Given a series of sets S1..SN, computes a disjoint partition of
    the population maintaining set boundaries. 
    
    That is, it computes a disjoint partition P1..PM where 
    Pn is the equivalence relation given by 
    
    R<a,b>  <==>  a in Sn <--> b in Sn  for all n
    
    NOTE: Given the current implementation, the contents of the
    sets must be hashable.
    
    Examples:
    
        >>> disjoint_partition( set([1,2,4]), set([2,3,4,5]), set([4,5]), set([6,7]), set([7,8]) )
        [set([2]), set([5]), set([1]), set([3]), set([4]), set([6]), set([8]), set([7])]
        
        >>> disjoint_partition( set([1,2,4]), set([2,3,4,5,10]), set([4,5]), set([6,7]), set([7,8]) )
        [set([2]), set([5]), set([1]), set([10, 3]), set([4]), set([6]), set([8]), set([7])]
    
    """
    reverse_items = collections.defaultdict(list)
    
    for i,s in enumerate(sets):
        for item in s:
            reverse_items[item].append(i)
    
    partitions = collections.defaultdict(set)
    for item, cats in reverse_items.iteritems():
        partitions[tuple(cats)].add(item)
    
    return partitions.values()

