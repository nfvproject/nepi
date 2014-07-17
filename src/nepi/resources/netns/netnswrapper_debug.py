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


############ METHODS DEBUG NETNSWRAPPER EXECUTION
##
## The netnswrapper works in ditributed mode, receiving instructions from
## a remote client. This makes it very hard to debug scripting errors 
## in the client side. To simplify error debugging, when set to debug mode,
## the ns3wrapper dumps every executed line to a script that can be then
## executed locally to reproduce and debug the experiment.
##
###########################################################################

import logging

class NetNSWrapperDebuger(object):
    def __init__(self, enabled):
        super(NetNSWrapperDebuger, self).__init__()
        self._enabled = enabled
        self._script_path = "debug.py"

        self.dump_header()

    @property
    def enabled(self):
        return self._enabled

    @property
    def script_path(self):
        return self._script_path

    def dump_to_script(self, command):
        f = open(self.script_path, "a")
        f.write("%s" % command)
        f.close()

    def dump_header(self):
        if not self.enabled:
            return

        header = """
from netnswrapper import NetNSWrapper

wrapper = NS3Wrapper()

"""
        self.dump_to_script(header)

    def dump_factory(self, uuid, type_name, kwargs):
        if not self.enabled:
            return

        command = ("kwargs = %(kwargs)s\n"
                "%(uuid)s = wrapper.factory(%(type_name)s, **kwargs)\n\n" 
                ) % dict({
                 "uuid": self.format_value(uuid),
                 "type_name": self.format_value(type_name),
                 "kwargs": self.format_kwargs(kwargs)
                })

        self.dump_to_script(command)

    def dump_create(self, uuid, clazzname, args):
        if not self.enabled:
            return

        command = ("args = %(args)s\n"
                "%(uuid)s = wrapper.create(%(clazzname)s, *args)\n\n" 
                ) % dict({
                 "uuid": self.format_value(uuid),
                 "clazzname": self.format_value(clazzname),
                 "args": self.format_args(args),
                })

        self.dump_to_script(command)

    def dump_invoke(self, newuuid, uuid, operation, args, kwargs):
        if not self.enabled:
            return

        command = ("args = %(args)s\n"
                   "kwargs = %(kwargs)s\n"
                   "%(newuuid)s = wrapper.invoke(%(uuid)s, %(operation)s, *args, **kwargs)\n\n" 
                ) % dict({
                 "newuuid": self.format_value(newuuid) if newuuid else "nothing",
                 "uuid": self.format_value(uuid),
                 "operation": self.format_value(operation),
                 "args": self.format_args(args),
                 "kwargs": self.format_kwargs(kwargs),
                })

        self.dump_to_script(command)

    def dump_set(self, uuid, name, value):
        if not self.enabled:
            return

        command = ("wrapper.set(%(uuid)s, %(name)s, %(value)s)\n\n" 
                ) % dict({
                 "uuid": self.format_value(uuid),
                 "name": self.format_value(name),
                 "value": self.format_value(value),
                })

        self.dump_to_script(command)

    def dump_get(self, uuid, name):
        if not self.enabled:
            return

        command = ("wrapper.get(%(uuid)s, %(name)s)\n\n" 
                ) % dict({
                 "uuid": self.format_value(uuid),
                 "name": self.format_value(name),
                })
        
        self.dump_to_script(command)

    def dump_shutdown(self):
        if not self.enabled:
            return

        command = "wrapper.shutdown()\n\n"
        self.dump_to_script(command)

    def format_value(self, value):
        if isinstance(value, str) and value.startswith("uuid"):
            return value.replace("-", "")

        import pprint 
        return pprint.pformat(value)

    def format_args(self, args):
        fargs = map(self.format_value, args)
        return "[%s]" % ",".join(fargs)

    def format_kwargs(self, kwargs):
        fkwargs = map(lambda (k,w): 
               "%s: %s" % (self.format_value(k), self.format_value(w)), 
            kwargs.iteritems())
        
        return  "dict({%s})" % ",".join(fkwargs)
        
