import logging
import weakref

def match_tags(box, all_tags, exact_tags):
    """ returns True if box has required tags """
    tall = set(all_tags)
    texact = set(exact_tags)

    if texact and box.connections == texact:
        return True

    if tall and tall.issubset(box.connections):
        return True

    return False

def find_boxes(box, all_tags = None, exact_tags = None, max_depth = 1):
    """ Look for the connected boxes with the required tags, doing breath-first
    search, until max_depth ( max_depth = None will traverse the entire graph ).
    """
    if not all_tags and not exact_tags:
        msg = "No matching criteria for resources."
        raise RuntimeError(msg)

    queue = set()
    # enqueue (depth, box) 
    queue.add((0, box))
    
    traversed = set()
    traversed.add(box)

    depth = 0

    result = set()

    while len(q) > 0: 
        (depth, a) = queue.pop()
        if match_tags(a, all_tags, exact_tags):
            result.add(a)

        if not max_depth or depth <= max_depth:
            depth += 1
            for b in sorted(a.connections):
                if b not in traversed:
                    traversed.add(b)
                    queue.add((depth, b))
    
    return result

class Resource(object):
    def __init__(self, box, ec):
        self._box = weakref.ref(box)
        self._ec = weakref.ref(ec)

        # Logging
        loglevel = "debug"
        self._logger = logging.getLogger("neco.execution.Resource.%s" % 
            self.box.guid)
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    @property
    def box(self):
        return self._box()

    @property
    def ec(self):
        return self._ec()

    def find_resources(self, all_tags = None, exact_tags = None, 
        max_depth = 1):
        resources = set()

        boxes = find_boxes(self.box, all_tags, exact_tags, max_depth)
        for b in boxes:
            r = self.ec.resource(b.guid)
            resources.add(r)

        return resources

class ResourceResolver(object):
    def __init__(self):
        pass  


