#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

from nepi.resources.linux.node import LinuxNode

import os
import sys

class DummyEC(object):
    @property
    def exp_id(self):
        return "nepi-1"

def create_node(hostname, username = None, identity = None):
    ec = DummyEC()
    node = LinuxNode(ec, 1)
    node.set("hostname", hostname)
    if username:
        node.set("username", username)
    if identity:
        node.set("identity", identity)

    # If we don't return the reference to the EC
    # it will be released by the garbage collector since 
    # the resources only save a weak refernce to it.
    return node, ec

def skipIfNotAlive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        host = args[1]
        if host != "localhost":
            user = None
            identity = None

            if len(args) >= 3:
                user = args[2]

            if len(args) >= 4:
                identity = args[3]

            node, ec = create_node(host, user, identity)

            if not node.is_alive():
                print "*** WARNING: Skipping test %s: Node %s is not alive\n" % (
                    name, node.get("hostname"))
                return

        return func(*args, **kwargs)
    
    return wrapped

def skipIfAnyNotAlive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        argss = list(args)
        argss.pop(0)
        for i in xrange(len(argss)/2):
            username = argss[i*2]
            hostname = argss[i*2+1]
            node, ec = create_node(hostname, username)

            if not node.is_alive():
                print "*** WARNING: Skipping test %s: Node %s is not alive\n" % (
                    name, node.get("hostname"))
                return

        return func(*args, **kwargs)
    
    return wrapped

def skipInteractive(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        mode = os.environ.get("NEPI_INTERACTIVE_TEST", False)
        mode = mode and  mode.lower() in ['true', 'yes']
        if not mode:
            print "*** WARNING: Skipping test %s: Interactive mode off \n" % name
            return

        return func(*args, **kwargs)
    
    return wrapped

def skipIfNotPLCredentials(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        pl_user = os.environ.get("PL_USER")
        pl_pass = os.environ.get("PL_PASS")
        if not (pl_user and pl_pass):
            print "*** WARNING: Skipping test %s: Planetlab user, password and slicename not defined\n" % name
            return

        return func(*args, **kwargs)

    return wrapped

def skipIfNotPythonVersion(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        if sys.version_info < 2.7:
            print "*** WARNING: Skipping test %s: total_seconds() method doesn't exist\n" % name
            return

        return func(*args, **kwargs)

    return wrapped

def skipIfNotSfaCredentials(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        sfa_user = os.environ.get("SFA_USER")
        sfa_pk = os.environ.get("SFA_PK")
        
        if not (sfa_user and os.path.exists(os.path.expanduser(sfa_pk))):
            print "*** WARNING: Skipping test %s: SFA path to private key doesn't exist\n" % name
            return

        return func(*args, **kwargs)

    return wrapped

def skipIfNotSfi(func):
    name = func.__name__
    def wrapped(*args, **kwargs):
        try:
            from sfa.client.sfi import Sfi
            from sfa.util.xrn import hrn_to_urn
        except ImportError:
            print "*** WARNING: Skipping test %s: sfi-client or sfi-common not installed\n" % name
            return

        return func(*args, **kwargs)

    return wrapped

def skipIf(cond, text):
    def wrapped(func, text):
        name = func.__name__

        def banner(*args, **kwargs):
            sys.stderr.write("*** WARNING: Skipping test %s: `%s'\n" %
                    (name, text))
            return None
        return banner

    return (lambda func: wrapped(func, text)) if cond else lambda func: func



