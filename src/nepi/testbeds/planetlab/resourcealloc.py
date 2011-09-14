#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import functools
import operator
import random
import collections
import heapq

from nepi.util.settools import setclusters
from nepi.util.settools import classify

class ResourceAllocationError(Exception):
    pass

def multicardinal(multiset):
    return sum(quant for c,quant in multiset.iteritems())

def avail(cls, partition):
    contains = classify.classContains
    return reduce(operator.or_, 
        classify.classComponents(cls, partition))

def _log(logstream, message, *args, **kwargs):
    if logstream:
        if args:
            logstream.write(message % args)
        elif kwargs:
            logstream.write(message % kwargs)
        else:
            logstream.write(message)
        logstream.write('\n')

def alloc(requests, logstream = None, nonseparable = False, saveinteresting = None, backtracklim = 100000000, verbose = True, sample = random.sample):
    """
    Takes an iterable over requests, which are iterables of candidate node ids,
    and returns a specific node id for each request (if successful).
    
    If it cannot, it will raise an ResourceAllocationError.
    """
    
    # First, materialize the request iterable
    requests = map(set,requests)
    
    # Classify all candidates
    universe = reduce(operator.or_, requests)
    partition = setclusters.disjoint_partition(*requests)
    
    # Classify requests
    c_reqlist = classify.classify(requests, partition)
    c_req = dict(
        (c,len(r))
        for c,r in c_reqlist.iteritems()
    )
    
    # Classify universe
    c_uni = map(len, partition)
    
    # Perform invariant sanity checks
    if multicardinal(c_req) > sum(c_uni):
        raise ResourceAllocationError, "Insufficient resources to grant request"
    
    for c,nreq in c_req.iteritems():
        if nreq > len(avail(c, partition)):
            raise ResourceAllocationError, "Insufficient resources to grant request, empty categories %s" % (
                filter(lambda i : classify.classContains(c,i), xrange(len(c))),
            )

    # Test for separability
    if nonseparable:
        components = clusters = []
    else:
        components = [
            classify.classMembers(c, partition)
            for c in c_req
        ]
        clusters = setclusters.disjoint_sets(*components)
    
    if len(clusters) > 1:
        if verbose:
            _log(logstream, "\nDetected %d clusters", len(clusters))
        
        # Requests are separable
        # Solve each part separately, then rejoin them
        
        # Build a class for each cluster
        clustermaps = []
        compmap = dict([(pid,idx) for idx,pid in enumerate(map(id,components))])
        for cluster in clusters:
            cluster_class = classify.getClass(
                reduce(operator.or_, cluster),
                partition )
            clustermaps.append(cluster_class)
        
        # Build a plan: assign a cluster to each request
        plan = []
        for cluster_class in clustermaps:
            plan_reqs = []
            for c, c_requests in c_reqlist.iteritems():
                if classify.isSubclass(cluster_class, c):
                    plan_reqs.extend(c_requests)
            plan.append(plan_reqs)
        
        # Execute the plan
        partial_results = []
        for i,plan_req in enumerate(plan):
            if verbose:
                _log(logstream, "Solving cluster %d/%d", i+1, len(plan))
            partial_results.append(alloc(plan_req, 
                logstream, 
                nonseparable = True,
                saveinteresting = saveinteresting,
                backtracklim = backtracklim,
                verbose = verbose))
        
        # Join results
        if verbose:
            _log(logstream, "Joining partial results")
        reqmap = dict([(pid,idx) for idx,pid in enumerate(map(id,requests))])
        joint = [None] * len(requests)
        for partial_result, partial_requests in zip(partial_results, plan):
                for assignment, partial_request in zip(partial_result, partial_requests):
                    joint[reqmap[id(partial_request)]] = assignment
        
        return joint
    else:
        # Non-separable request, solve
        #_log(logstream, "Non-separable request")
        
        # Solve
        partial = collections.defaultdict(list)
        Pavail = list(c_uni)
        Gavail = dict([
            (c, len(avail(c, partition)))
            for c in c_req
        ])
        req = dict(c_req)
        
        # build a cardinality map
        cardinality = dict([
            (c, [classify.classCardinality(c,partition), -nreq])
            for c,nreq in req.iteritems()
        ])
        
        classContains = classify.classContains
        isSubclass = classify.isSubclass
        
        stats = [
            0, # ops
            0, # back tracks
            0, # skipped branches
        ]
        
        def recursive_alloc():
            # Successful termination condition: all requests satisfied
            if not req:
                return True
            
            # Try in cardinality order
            if quickstage:
                order = heapq.nsmallest(2, req, key=Gavail.__getitem__)
            else:
                order = sorted(req, key=Gavail.__getitem__)
            
            # Do backtracking on those whose cardinality leaves a choice
            # Force a pick when it does not
            if order and (Gavail[order[0]] <= 1
                          or classify.classCardinality(order[0]) <= 1):
                order = order[:1]
            
            for c in order:
                nreq = req[c]
                #carditem = cardinality[c]
                for i,bit in enumerate(c):
                    if bit == "1" and Pavail[i]:
                        stats[0] += 1 # ops+1
                        
                        subreq = min(Pavail[i], nreq)
                        
                        # branch sanity check
                        skip = False
                        for c2,navail in Gavail.iteritems():
                            if c2 != c and classContains(c2, i) and (navail - subreq) < req.get(c2,0):
                                # Fail branch, don't even try
                                skip = True
                                break
                        if skip:
                            stats[2] += 1 # skipped branches + 1
                            continue
                        
                        # forward track
                        partial[c].append((i,subreq))
                        Pavail[i] -= subreq
                        #carditem[1] -= subreq
                        
                        for c2 in Gavail:
                            if classContains(c2, i):
                                Gavail[c2] -= subreq
                        
                        if subreq < nreq:
                            req[c] -= subreq
                        else:
                            del req[c]
                        
                        # Try to solve recursively
                        success = recursive_alloc()
                        
                        if success:
                            return success
                        
                        # Back track
                        del partial[c][-1]
                        Pavail[i] += subreq
                        #carditem[1] += subreq
                        
                        for c2 in Gavail:
                            if classContains(c2, i):
                                Gavail[c2] += subreq
                        
                        if subreq < nreq:
                            req[c] += subreq
                        else:
                            req[c] = subreq
                        
                        stats[1] += 1 # backtracks + 1
                        
                        if (logstream or (saveinteresting is not None)) and (stats[1] & 0xffff) == 0:
                            _log(logstream, "%r\n%r\n... stats: ops=%d, backtracks=%d, skipped=%d", Gavail, req,
                                *stats)
                            
                            if stats[1] == 0x1400000:
                                # Interesting case, log it out
                                _log(logstream, "... interesting case: %r", requests)
                                
                                if saveinteresting is not None:
                                    saveinteresting.append(requests)
                if stats[1] > backtracklim:
                    break
                            
            
            # We tried and tried... and failed
            return False
        
        # First try quickly (assign most selective first exclusively)
        quickstage = True
        success = recursive_alloc()
        if not success:
            # If it fails, retry exhaustively (try all assignment orders)
            quickstage = False
            success = recursive_alloc()
        
        if verbose or (not success or stats[1] or stats[2]):
            _log(logstream, "%s with stats: ops=%d, backtracks=%d, skipped=%d",
                ("Succeeded" if success else "Failed"),
                *stats)
        
        if not success:
            raise ResourceAllocationError, "Insufficient resources to grant request"
        
        # Perform actual assignment
        Pavail = map(set, partition)
        solution = {}
        for c, partial_assignments in partial.iteritems():
            psol = set()
            for i, nreq in partial_assignments:
                part = Pavail[i]
                if len(part) < nreq:
                    raise AssertionError, "Cannot allocate resources for supposedly valid solution!"
                assigned = set(sample(part, nreq))
                psol |= assigned
                part -= assigned
            solution[c] = psol
        
        # Format solution for the caller (return a node id for each request)
        reqmap = {}
        for c,reqs in c_reqlist.iteritems():
            for req in reqs:
                reqmap[id(req)] = c
        
        req_solution = []
        for req in requests:
            c = reqmap[id(req)]
            req_solution.append(solution[c].pop())
        
        return req_solution


if __name__ == '__main__':
    def test():
        import random
        import sys
        
        toughcases = [
          (False,
            [[9, 11, 12, 14, 16, 17, 18, 20, 21], 
             [2], 
             [2], 
             [4, 5, 6, 7, 8, 11, 12, 13, 18, 22], 
             [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], 
             [6, 10, 11, 13, 14, 15, 16, 18, 20], 
             [3, 7, 8, 9, 10, 12, 14, 17, 22], 
             [0, 1, 3, 4, 5, 6, 7, 8, 10, 13, 14, 17, 19, 21, 22], 
             [16, 22]]),
          (False,
            [[2, 10, 0, 3, 4, 8], 
             [4, 1, 6, 10, 2, 0, 5, 9, 8, 7], 
             [8, 3, 0, 2, 1, 4, 10, 7, 5], 
             [8], 
             [2], 
             [2, 8], 
             [2, 7, 8, 3, 1, 0, 9, 10, 5, 4, 6], 
             [2, 4, 8, 10, 1, 3, 9], 
             [3, 0, 5]]),
          (True,
            [[2, 10, 0, 3, 4, 8], 
             [4, 1, 6, 10, 2, 0, 5, 9, 8, 7], 
             [8, 3, 0, 2, 1, 4, 10, 7, 5], 
             [8], 
             [2, 8], 
             [2, 7, 8, 3, 1, 0, 9, 10, 5, 4, 6], 
             [2, 4, 8, 10, 1, 3, 9], 
             [3, 0, 5]]),
        ]
        
        # Test tough cases
        for n,(solvable,req) in enumerate(toughcases):
            print "Trying #R = %4d, #S = %4d (tough case %d)" % (len(req), len(reduce(operator.or_, map(set,req))), n)
            try:
                solution = alloc(req, sys.stdout, verbose=False)
                if solvable:
                    print "  OK - allocation successful"
                else:
                    raise AssertionError, "Case %r had no solution, but got %r" % (req, solution)
            except ResourceAllocationError: 
                if not solvable:
                    print "  OK - allocation not possible"
                else:
                    raise AssertionError, "Case %r had a solution, but got none" % (req,)
        
        interesting = []
        
        suc_mostlypossible = mostlypossible = 0
        suc_mostlyimpossible = mostlyimpossible = 0
        suc_huge = huge = 0
        
        try:
            # Fuzzer - mostly impossible cases
            for i in xrange(10000):
                nreq = random.randint(1,20)
                nsrv = random.randint(max(1,nreq-5),50)
                srv = range(nsrv)
                req = [
                    random.sample(srv, random.randint(1,nsrv))
                    for j in xrange(nreq)
                ]
                print "Trying %5d: #R = %4d, #S = %4d... " % (i, nreq, nsrv),
                sys.stdout.flush()
                mostlyimpossible += 1
                try:
                    solution = alloc(req, sys.stdout, saveinteresting = interesting, verbose=False)
                    suc_mostlyimpossible += 1
                    print "  OK - allocation successful  \r",
                except ResourceAllocationError: 
                    print "  OK - allocation not possible  \r",
                except KeyboardInterrupt:
                    print "ABORTING CASE %r" % (req,)
                    raise
                sys.stdout.flush()

            # Fuzzer - mostly possible cases
            for i in xrange(10000):
                nreq = random.randint(1,10)
                nsrv = random.randint(nreq,100)
                srv = range(nsrv)
                req = [
                    random.sample(srv, random.randint(min(nreq,nsrv),nsrv))
                    for j in xrange(nreq)
                ]
                print "Trying %5d: #R = %4d, #S = %4d... " % (i, nreq, nsrv),
                sys.stdout.flush()
                mostlypossible += 1
                try:
                    solution = alloc(req, sys.stdout, saveinteresting = interesting, verbose=False)
                    suc_mostlypossible += 1
                    print "  OK - allocation successful  \r",
                except ResourceAllocationError: 
                    print "  OK - allocation not possible  \r",
                except KeyboardInterrupt:
                    print "ABORTING CASE %r" % (req,)
                    raise
                sys.stdout.flush()

            # Fuzzer - biiig cases
            for i in xrange(10):
                nreq = random.randint(1,500)
                nsrv = random.randint(1,8000)
                srv = range(nsrv)
                req = [
                    random.sample(srv, random.randint(min(nreq,nsrv),nsrv))
                    for j in xrange(nreq)
                ]
                print "Trying %4d: #R = %4d, #S = %4d... " % (i, nreq, nsrv),
                sys.stdout.flush()
                huge += 1
                try:
                    solution = alloc(req, sys.stdout, saveinteresting = interesting, verbose=False)
                    suc_huge += 1
                    print "  OK - allocation successful  \r",
                except ResourceAllocationError: 
                    print "  OK - allocation not possible  \r",
                except KeyboardInterrupt:
                    print "ABORTING CASE %r" % (req,)
                    raise
                sys.stdout.flush()
        except:
            print "ABORTING TEST"
        
        print "\nSuccess rates:"
        print "  Mostly possible: %d/%d (%.2f%%)" % (suc_mostlypossible, mostlypossible, 100.0 * suc_mostlypossible / max(1,mostlypossible))
        print "  Mostly impossible: %d/%d (%.2f%%)" % (suc_mostlyimpossible, mostlyimpossible, 100.0 * suc_mostlyimpossible / max(1,mostlyimpossible))
        print "  Huge: %d/%d (%.2f%%)" % (suc_huge, huge, 100.0 * suc_huge / max(1,huge))
        
        if interesting:
            print "%d interesting requests:" % (len(interesting),)
            for n,req in enumerate(interesting):
                print "Interesting request %d/%d: %r", (n,len(interesting),req,)
    test()

