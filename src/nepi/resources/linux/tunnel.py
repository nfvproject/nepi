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

from nepi.execution.resource import clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow, tdiffsec

import os
import time

state_check_delay = 0.5

@clsinit_copy
class LinuxTunnel(LinuxApplication):
    _rtype = "abstract::LinuxTunnel"
    _help = "Constructs a tunnel between two Linux endpoints"
    _backend = "linux"

    def __init__(self, ec, guid):
        super(LinuxTunnel, self).__init__(ec, guid)
        self._home = "tunnel-%s" % self.guid

    def log_message(self, msg):
        return " guid %d - tunnel %s - %s - %s " % (self.guid, 
                self.endpoint1.node.get("hostname"), 
                self.endpoint2.node.get("hostname"), 
                msg)

    def get_endpoints(self):
        """ Returns the list of RM that are endpoints to the tunnel 
        """
        connected = []
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if hasattr(rm, "udp_connect_command"):
                connected.append(rm)
        return connected

    @property
    def endpoint1(self):
        endpoints = self.get_endpoints()
        if endpoints: return endpoints[0]
        return None

    @property
    def endpoint2(self):
        endpoints = self.get_endpoints()
        if endpoints and len(endpoints) > 1: return endpoints[1]
        return None

    def app_home(self, endpoint):
        return os.path.join(endpoint.node.exp_home, self._home)

    def run_home(self, endpoint):
        return os.path.join(self.app_home(endpoint), self.ec.run_id)

    def initiate_connection(self, endpoint, remote_endpoint):
        raise NotImplementedError

    def establish_connection(self, endpoint, remote_endpoint, data):
        raise NotImplementedError

    def verify_connection(self, endpoint, remote_endpoint):
        raise NotImplementedError

    def terminate_connection(self, endpoint, remote_endpoint):
        raise NotImplementedError

    def check_state_connection(self, endpoint, remote_endpoint):
        raise NotImplementedError

    def do_provision(self):
        # create run dir for tunnel on each node 
        self.endpoint1.node.mkdir(self.run_home(self.endpoint1))
        self.endpoint2.node.mkdir(self.run_home(self.endpoint2))

        # Start 2 step connection
        # Initiate connection from endpoint 1 to endpoint 2
        data1 = self.initiate_connection(self.endpoint1, self.endpoint2)

        # Initiate connection from endpoint 2 to endpoint 1
        data2 = self.initiate_connection(self.endpoint2, self.endpoint1)

        # Establish connection from endpoint 1 to endpoint 2
        self.establish_connection(self.endpoint1, self.endpoint2, data2)
        
        # Establish connection from endpoint 2 to endpoint 1
        self.establish_connection(self.endpoint2, self.endpoint1, data1)

        # check if connection was successful on both sides
        self.verify_connection(self.endpoint1, self.endpoint2)
        self.verify_connection(self.endpoint2, self.endpoint1)
       
        self.info("Provisioning finished")
 
        self.set_provisioned()

    def do_deploy(self):
        if (not self.endpoint1 or self.endpoint1.state < ResourceState.READY) or \
            (not self.endpoint2 or self.endpoint2.state < ResourceState.READY):
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            self.do_discover()
            self.do_provision()
 
            self.set_ready()

    def do_start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)
            
            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        """ Stops application execution
        """
        if self.state == ResourceState.STARTED:
            self.info("Stopping tunnel")

            self.terminate_connection(self.endpoint1, self.endpoint2)
            self.terminate_connection(self.endpoint2, self.endpoint1)

            self.set_stopped()

    @property
    def state(self):
        """ Returns the state of the application
        """
        if self._state == ResourceState.STARTED:
            # In order to avoid overwhelming the remote host and
            # the local processor with too many ssh queries, the state is only
            # requested every 'state_check_delay' seconds.
            if tdiffsec(tnow(), self._last_state_check) > state_check_delay:
                
                self.check_state_connection()

                self._last_state_check = tnow()

        return self._state


    def valid_connection(self, guid):
        # TODO: Validate!
        return True

