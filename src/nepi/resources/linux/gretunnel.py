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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.tunnel import LinuxTunnel
from nepi.util.sshfuncs import ProcStatus
from nepi.util.timefuncs import tnow, tdiffsec

import re
import socket
import time
import os

@clsinit_copy
class LinuxGRETunnel(LinuxTunnel):
    _rtype = "LinuxGRETunnel"
    _help = "Constructs a tunnel between two Linux endpoints using a UDP connection "
    _backend = "linux"

    def log_message(self, msg):
        return " guid %d - GRE tunnel %s - %s - %s " % (self.guid, 
                self.endpoint1.node.get("hostname"), 
                self.endpoint2.node.get("hostname"), 
                msg)

    def get_endpoints(self):
        """ Returns the list of RM that are endpoints to the tunnel 
        """
        connected = []
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if hasattr(rm, "gre_connect"):
                connected.append(rm)
        return connected

    def initiate_connection(self, endpoint, remote_endpoint):
        # Return the command to execute to initiate the connection to the
        # other endpoint
        connection_run_home = self.run_home(endpoint)
        connection_app_home = self.app_home(endpoint)
        data = endpoint.gre_connect(remote_endpoint, connection_run_home, 
                connection_app_home)
        return data

    def establish_connection(self, endpoint, remote_endpoint, data):
        pass

    def verify_connection(self, endpoint, remote_endpoint):
        remote_ip = socket.gethostbyname(remote_endpoint.node.get("hostname"))

        command = "ping -c 4 %s" % remote_ip
        (out, err), proc = endpoint.node.execute(command,
                blocking = True)

        m = re.search("(\d+)% packet loss", str(out))
        if not m or int(m.groups()[0]) == 100:
             msg = " Erroro establishing GRE Tunnel"
             self.error(msg, out, err)
             raise RuntimeError, msg

    def terminate_connection(self, endpoint, remote_endpoint):
        pass

    def check_state_connection(self):
        pass

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

