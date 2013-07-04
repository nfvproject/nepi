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
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import clsinit_copy, ResourceState, \
    ResourceAction, reschedule_delay
from nepi.resources.linux.ccn.ccnapplication import LinuxCCNApplication
from nepi.util.timefuncs import tnow

import os


# TODO: Add rest of options for ccndc!!!
#       Implement ENTRY DELETE!!

@clsinit_copy
class LinuxFIBEntry(LinuxCCNApplication):
    _rtype = "LinuxFIBEntry"

    @classmethod
    def _register_attributes(cls):
        uri = Attribute("uri",
                "URI prefix to match and route for this FIB entry",
                default = "ccnx:/",
                flags = Flags.ExecReadOnly)

        protocol = Attribute("protocol",
                "Transport protocol used in network connection to peer "
                "for this FIB entry. One of 'udp' or 'tcp'.",
                type = Types.Enumerate, 
                default = "udp",
                allowed = ["udp", "tcp"],
                flags = Flags.ExecReadOnly)

        host = Attribute("host",
                "Peer host used in network connection for this FIB entry. ",
                flags = Flags.ExecReadOnly)

        port = Attribute("port",
                "Peer port address used in network connection to peer "
                "for this FIB entry.",
                flags = Flags.ExecReadOnly)

        cls._register_attribute(uri)
        cls._register_attribute(protocol)
        cls._register_attribute(host)
        cls._register_attribute(port)

    def __init__(self, ec, guid):
        super(LinuxFIBEntry, self).__init__(ec, guid)
        self._home = "fib-%s" % self.guid

    def deploy(self):
        # Wait until associated ccnd is provisioned
        if not self.ccnd or self.ccnd.state < ResourceState.READY:
            # ccnr needs to wait until ccnd is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            command = self._start_command
            env = self._environment

            self.set("command", command)
            self.set("env", env)

            self.info("Deploying command '%s' " % command)

            self.node.mkdir(self.app_home)
            (out, err), proc = self.execute_command(command, env)

            if proc.poll():
                self._state = ResourceState.FAILED
                msg = "Failed to execute command"
                self.error(msg, out, err)
                raise RuntimeError, msg


            self.debug("----- READY ---- ")
            self._ready_time = tnow()
            self._state = ResourceState.READY

    def start(self):
        if self._state in [ResourceState.READY, ResourceState.STARTED]:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            self._start_time = tnow()
            self._state = ResourceState.STARTED
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            self._state = ResourceState.FAILED
            raise RuntimeError, msg

    def stop(self):
        command = self.get('command')
        env = self.get('env')
        
        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = self._stop_command
            (out, err), proc = self.execute_command(command, env)

            if proc.poll():
                pass

            self._stop_time = tnow()
            self._state = ResourceState.STOPPED

    @property
    def state(self):
        return self._state

    @property
    def _start_command(self):
        uri = self.get("uri") or ""
        protocol = self.get("protocol") or ""
        host = self.get("host") or ""
        port = self.get("port") or ""

        # add ccnx:/example.com/ udp 224.0.0.204 52428
        return "ccndc add %(uri)s %(protocol)s %(host)s %(port)s" % ({
            "uri" : uri,
            "protocol": protocol,
            "host": host,
            "port": port
            })

    @property
    def _stop_command(self):
        uri = self.get("uri") or ""
        protocol = self.get("protocol") or ""
        host = self.get("host") or ""
        port = self.get("port") or ""

        # add ccnx:/example.com/ udp 224.0.0.204 52428
        return "ccndc del %(uri)s %(protocol)s %(host)s %(port)s" % ({
            "uri" : uri,
            "protocol": protocol,
            "host": host,
            "port": port
            })

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

