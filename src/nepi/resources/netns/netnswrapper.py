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

import logging
import netns
import time
import os
import sys
import uuid

class NetNSWrapper(object):
    def __init__(self, loglevel = logging.INFO, enable_dump = False):
        super(NetNSWrapper, self).__init__()
        # holds reference to all C++ objects and variables in the simulation
        self._objects = dict()

        # Logging
        self._logger = logging.getLogger("netnswrapper")
        self._logger.setLevel(loglevel)

        # Object to dump instructions to reproduce and debug experiment
        from netnswrapper_debug import NetNSWrapperDebuger
        self._debuger = NetNSWrapperDebuger(enabled = enable_dump)

    @property
    def debuger(self):
        return self._debuger

    @property
    def logger(self):
        return self._logger

    def make_uuid(self):
        return "uuid%s" % uuid.uuid4()

    def get_object(self, uuid):
        return self._objects.get(uuid)
 
    def create(self, clazzname, *args):
        """ This method should be used to construct netns objects """

        if clazzname not in ['open'] and not hasattr(netns, clazzname):
            msg = "Type %s not supported" % (clazzname) 
            self.logger.error(msg)

        uuid = self.make_uuid()
        
        ### DEBUG
        self.logger.debug("CREATE %s( %s )" % (clazzname, str(args)))
    
        self.debuger.dump_create(uuid, clazzname, args)
        ########

        if clazzname == "open":
            path = args[0] 
            mode = args[1] 
            obj = open(path, mode)
        else:
            clazz = getattr(netns, clazzname)
     
            # arguments starting with 'uuid' identify ns-3 C++
            # objects and must be replaced by the actual object
            realargs = self.replace_args(args)
           
            obj = clazz(*realargs)
            
        self._objects[uuid] = obj

        ### DEBUG
        self.logger.debug("RET CREATE ( uuid %s ) %s = %s( %s )" % (str(uuid), 
            str(obj), clazzname, str(args)))
        ########

        return uuid

    def invoke(self, uuid, operation, *args, **kwargs):
        newuuid = self.make_uuid()
        
        ### DEBUG
        self.logger.debug("INVOKE %s -> %s( %s, %s ) " % (
            uuid, operation, str(args), str(kwargs)))
            
        self.debuger.dump_invoke(newuuid, uuid, operation, args, kwargs)
        ########

        obj = self.get_object(uuid)
        
        method = getattr(obj, operation)

        # arguments starting with 'uuid' identify netns
        # objects and must be replaced by the actual object
        realargs = self.replace_args(args)
        realkwargs = self.replace_kwargs(kwargs)

        result = method(*realargs, **realkwargs)

        # If the result is an object (not a base value),
        # then keep track of the object a return the object
        # reference (newuuid)
        if not (result is None or type(result) in [
                bool, float, long, str, int]):
            self._objects[newuuid] = result
            result = newuuid

        ### DEBUG
        self.logger.debug("RET INVOKE %s%s = %s -> %s(%s, %s) " % (
            "(uuid %s) " % str(newuuid) if newuuid else "", str(result), uuid, 
            operation, str(args), str(kwargs)))
        ########

        return result

    def set(self, uuid, name, value):
        ### DEBUG
        self.logger.debug("SET %s %s %s" % (uuid, name, str(value)))
    
        self.debuger.dump_set(uuid, name, value)
        ########

        obj = self.get_object(uuid)
        setattr(obj, name, value)

        ### DEBUG
        self.logger.debug("RET SET %s = %s -> set(%s, %s)" % (str(value), uuid, name, 
            str(value)))
        ########

        return value

    def get(self, uuid, name):
        ### DEBUG
        self.logger.debug("GET %s %s" % (uuid, name))
        
        self.debuger.dump_get(uuid, name)
        ########

        obj = self.get_object(uuid)
        result = getattr(obj, name)

        ### DEBUG
        self.logger.debug("RET GET %s = %s -> get(%s)" % (str(result), uuid, name))
        ########

        return result

    def shutdown(self):
        ### DEBUG
        self.debuger.dump_shutdown()
        ########

        ### FLUSH PIPES
        sys.stdout.flush()
        sys.stderr.flush()

        ### RELEASE OBJECTS
        del self._objects 

        ### DEBUG
        self.logger.debug("SHUTDOWN")
        ########

    def replace_args(self, args):
        realargs = [self.get_object(arg) if \
                str(arg).startswith("uuid") else arg for arg in args]
 
        return realargs

    def replace_kwargs(self, kwargs):
        realkwargs = dict([(k, self.get_object(v) \
                if str(v).startswith("uuid") else v) \
                for k,v in kwargs.iteritems()])
 
        return realkwargs

