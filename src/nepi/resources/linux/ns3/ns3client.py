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
import weakref

from optparse import OptionParser, SUPPRESS_HELP

from nepi.resources.ns3.ns3client import NS3Client
from nepi.resources.ns3.ns3server import NS3WrapperMessage

class LinuxNS3Client(NS3Client):
    def __init__(self, simulation):
        super(LinuxNS3Client, self).__init__()
        self._simulation = weakref.ref(simulation)

        self._socat_proc = None
        self.connect_client()

    @property
    def simulation(self):
        return self._simulation()

    def connect_client(self):
        if self.simulation.node.get("hostname") in ['localhost', '127.0.0.1']:
            return

        (out, err), self._socat_proc = self.simulation.node.socat(
                self.simulation.local_socket,
                self.simulation.remote_socket) 

    def send_msg(self, msg_type, *args, **kwargs):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.simulation.local_socket)

        msg = [msg_type, args, kwargs]

        def encode(item):
            item = cPickle.dumps(item)
            return base64.b64encode(item)

        encoded = "|".join(map(encode, msg))
        sock.send("%s\n" % encoded)
       
        reply = sock.recv(1024)
        return cPickle.loads(base64.b64decode(reply))

    def create(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.CREATE, *args, **kwargs)

    def factory(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.FACTORY, *args, **kwargs)

    def invoke(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.INVOKE, *args, **kwargs)

    def set(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.SET, *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.GET, *args, **kwargs)

    def flush(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.FLUSH, *args, **kwargs)

    def start(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.START, *args, **kwargs)

    def stop(self, *args, **kwargs):
        return self.send_msg(NS3WrapperMessage.STOP, *args, **kwargs)

    def shutdown(self, *args, **kwargs):
        ret = None

        try:
            ret = self.send_msg(NS3WrapperMessage.SHUTDOWN, *args, **kwargs)
        except:
            pass

        try:
            if self._socat_proc:
                self._socat_proc.kill()
        except:
            pass

        try:
            os.remove(self.simulation.local_socket)
        except:
            pass

        return ret

