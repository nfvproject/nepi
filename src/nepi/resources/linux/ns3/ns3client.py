#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2014 INRIA
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

import base64
import cPickle
import errno
import socket
from optparse import OptionParser, SUPPRESS_HELP

from nepi.resources.ns3.ns3client import NS3Client
from nepi.resources.ns3.ns3server import NS3WrapperMessage

class LinuxNS3Client(NS3Client):
    def __init__(self, socket_name):
        super(LinuxNS3Client, self).__init__()
        self._socket_name = socket_name

    @property
    def socket_name(self):
        return self._socket_name

    def send_msg(self, msg, *args):
        args = list(args)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_name)

        args.insert(0, msg)
        def encode(arg):
            arg = cPickle.dumps(arg)
            return base64.b64encode(arg) 

        encoded = "|".join(map(encode, args))
        sock.send("%s\n" % encoded)
        
        reply = sock.recv(1024)
        return cPickle.loads(base64.b64decode(reply))

    def create(self, clazzname, *args):
        args = list(args)
        args.insert(0, clazzname)
        
        return self.send_msg(NS3WrapperMessage.CREATE, *args)

    def invoke(self, uuid, operation, *args):
        args = list(args)
        args.insert(0, operation)
        args.insert(0, uuid)

        return self.send_msg(NS3WrapperMessage.INVOKE, *args)

    def set(self, uuid, name, value):
        args = [uuid, name, value]

        return self.send_msg(NS3WrapperMessage.SET, *args)

    def get(self, uuid, name):
        args = [uuid, name]

        return self.send_msg(NS3WrapperMessage.GET, *args)

    def trace(self, *args):
        return self.send_msg(NS3WrapperMessage.TRACE, *args)

    def start(self):
        return self.send_msg(NS3WrapperMessage.START, [])

    def stop(self, time = None):
        args = None
        if time:
            args = [time]

        return self.send_msg(NS3WrapperMessage.STOP, *args)

    def shutdown(self):
        return self.send_msg(NS3WrapperMessage.SHUTDOWN, [])

