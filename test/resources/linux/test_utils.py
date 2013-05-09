from neco.resources.linux.node import LinuxNode

import os

class DummyEC(object):
    @property
    def exp_id(self):
        return "nepi-1"

def create_node(hostname, username):
    ec = DummyEC()
    node = LinuxNode(ec, 1)
    node.set("hostname", hostname)
    node.set("username", username)

    # If we don't return the reference to the EC
    # it will be released by the garbage collector since 
    # the resources only save a weak refernce to it.
    return node, ec

def skipIfNotAlive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        node, ec = create_node(args[1], args[2])

        if not node.is_alive():
            print "*** WARNING: Skipping test %s: Node %s is not alive\n" % (
                name, node.get("hostname"))
            return

        return func(*args, **kwargs)
    
    return wrapped

def skipInteractive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        mode = os.environ.get("NEPI_INTERACTIVE", False)
        mode = mode and  mode.lower() in ['true', 'yes']
        if not mode:
            print "*** WARNING: Skipping test %s: Interactive mode off \n" % name
            return

        return func(*args, **kwargs)
    
    return wrapped


