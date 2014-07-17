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
import os
import socket
import time
import weakref

from optparse import OptionParser, SUPPRESS_HELP

from nepi.resources.netns.netnsclient import NetNSClient
from nepi.resources.netns.netnsserver import NetNSWrapperMessage

class LinuxNetNSClient(NetNSClient):
    def __init__(self, emulation):
        super(LinuxNetNSClient, self).__init__()
        self._emulation = weakref.ref(emulation)

        self._socat_proc = None

    @property
    def emulation(self):
        return self._emulation()

    def send_msg(self, msg_type, *args, **kwargs):
        msg = [msg_type, args, kwargs]

        def encode(item):
            item = cPickle.dumps(item)
            return base64.b64encode(item)

        encoded = "|".join(map(encode, msg))

        if self.emulation.node.get("hostname") in ['localhost', '127.0.0.1']:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.emulation.remote_socket)
            sock.send("%s\n" % encoded)
            reply = sock.recv(1024)
            sock.close()
        else:
            command = ( "python -c 'import socket;"
                "sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);"
                "sock.connect(\"%(socket_addr)s\");"
                "msg = \"%(encoded_message)s\\n\";"
                "sock.send(msg);"
                "reply = sock.recv(1024);"
                "sock.close();"
                "print reply'") % {
                    "encoded_message": encoded,
                    "socket_addr": self.emulation.remote_socket,
                    }

            (reply, err), proc = self.emulation.node.execute(command, 
                    with_lock = True) 

            if (err and proc.poll()) or reply.strip() == "":
                msg = (" Couldn't connect to remote socket %s - REPLY: %s "
                      "- ERROR: %s ") % (
                        self.emulation.remote_socket, reply, err)
                self.emulation.error(msg, reply, err)
                raise RuntimeError(msg)
                   
        reply = cPickle.loads(base64.b64decode(reply))

        return reply

    def create(self, *args, **kwargs):
        return self.send_msg(NetNSWrapperMessage.CREATE, *args, **kwargs)

    def invoke(self, *args, **kwargs):
        return self.send_msg(NetNSWrapperMessage.INVOKE, *args, **kwargs)

    def set(self, *args, **kwargs):
        return self.send_msg(NetNSWrapperMessage.SET, *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.send_msg(NetNSWrapperMessage.GET, *args, **kwargs)

    def flush(self, *args, **kwargs):
        return self.send_msg(NetNSWrapperMessage.FLUSH, *args, **kwargs)

    def shutdown(self, *args, **kwargs):
        try:
            return self.send_msg(NetNSWrapperMessage.SHUTDOWN, *args, **kwargs)
        except:
            pass

        return None

