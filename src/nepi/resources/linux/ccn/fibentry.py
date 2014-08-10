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
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.ccn.ccnd import LinuxCCND
from nepi.util.timefuncs import tnow

import os
import socket
import time


# TODO: Add rest of options for ccndc!!!
#       Implement ENTRY DELETE!!

@clsinit_copy
class LinuxFIBEntry(LinuxApplication):
    _rtype = "LinuxFIBEntry"

    @classmethod
    def _register_attributes(cls):
        uri = Attribute("uri",
                "URI prefix to match and route for this FIB entry",
                default = "ccnx:/",
                flags = Flags.Design)

        protocol = Attribute("protocol",
                "Transport protocol used in network connection to peer "
                "for this FIB entry. One of 'udp' or 'tcp'.",
                type = Types.Enumerate, 
                default = "udp",
                allowed = ["udp", "tcp"],
                flags = Flags.Design)

        host = Attribute("host",
                "Peer hostname used in network connection for this FIB entry. ",
                flags = Flags.Design)

        port = Attribute("port",
                "Peer port address used in network connection to peer "
                "for this FIB entry.",
                flags = Flags.Design)

        ip = Attribute("ip",
                "Peer host public IP used in network connection for this FIB entry. ",
                flags = Flags.Design)

        cls._register_attribute(uri)
        cls._register_attribute(protocol)
        cls._register_attribute(host)
        cls._register_attribute(port)
        cls._register_attribute(ip)

    @classmethod
    def _register_traces(cls):
        ping = Trace("ping", "Ping to the peer end")
        mtr = Trace("mtr", "Mtr to the peer end")
        traceroute = Trace("traceroute", "Tracerout to the peer end")

        cls._register_trace(ping)
        cls._register_trace(mtr)
        cls._register_trace(traceroute)

    def __init__(self, ec, guid):
        super(LinuxFIBEntry, self).__init__(ec, guid)
        self._home = "fib-%s" % self.guid
        self._ping = None
        self._traceroute = None
        self._ccnd = None

    @property
    def ccnd(self):
        if not self._ccnd:
            ccnd = self.get_connected(LinuxCCND.get_rtype())
            if ccnd: 
                self._ccnd = ccnd[0]
            
        return self._ccnd

    @property
    def ping(self):
        if not self._ping:
            from nepi.resources.linux.ping import LinuxPing
            ping = self.get_connected(LinuxPing.get_rtype())
            if ping: 
                self._ping = ping[0]
            
        return self._ping

    @property
    def traceroute(self):
        if not self._traceroute:
            from nepi.resources.linux.traceroute import LinuxTraceroute
            traceroute = self.get_connected(LinuxTraceroute.get_rtype())
            if traceroute: 
                self._traceroute = traceroute[0]
            
        return self._traceroute

    @property
    def node(self):
        if self.ccnd: return self.ccnd.node
        return None

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        if name == "ping":
            if not self.ping:
                return None
            return self.ec.trace(self.ping.guid, "stdout", attr, block, offset)

        if name == "traceroute":
            if not self.traceroute:
                return None
            return self.ec.trace(self.traceroute.guid, "stdout", attr, block, offset)

        return super(LinuxFIBEntry, self).trace(name, attr, block, offset)
    
    def do_deploy(self):
        # Wait until associated ccnd is provisioned
        if not self.ccnd or self.ccnd.state < ResourceState.READY:
            # ccnr needs to wait until ccnd is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("ip"):
                host = self.get("host")
                ip = socket.gethostbyname(host)
                self.set("ip", ip)

            if not self.get("command"):
                self.set("command", self._start_command)

            if not self.get("env"):
                self.set("env", self._environment)

            command = self.get("command")

            self.info("Deploying command '%s' " % command)

            self.do_discover()
            self.do_provision()
            self.configure()

            self.set_ready()

    def upload_start_command(self):
        command = self.get("command")
        env = self.get("env")

        # We want to make sure the FIB entries are created
        # before the experiment starts.
        # Run the command as a bash script in the background, 
        # in the host ( but wait until the command has
        # finished to continue )
        env = env and self.replace_paths(env)
        command = self.replace_paths(command)

        # ccndc seems to return exitcode OK even if a (dns) error
        # occurred, so we need to account for this case here. 
        (out, err), proc = self.execute_command(command, 
                env, blocking = True)

        if proc.poll():
            msg = "Failed to execute command"
            self.error(msg, out, err)
            raise RuntimeError, msg
        
    def configure(self):
        if self.trace_enabled("ping") and not self.ping:
            self.info("Configuring PING trace")
            ping = self.ec.register_resource("LinuxPing")
            self.ec.set(ping, "printTimestamp", True)
            self.ec.set(ping, "target", self.get("host"))
            self.ec.set(ping, "earlyStart", True)
            self.ec.register_connection(ping, self.node.guid)
            self.ec.register_connection(ping, self.guid)
            # schedule ping deploy
            self.ec.deploy(guids=[ping], group = self.deployment_group)

        if self.trace_enabled("traceroute") and not self.traceroute:
            self.info("Configuring TRACEROUTE trace")
            traceroute = self.ec.register_resource("LinuxTraceroute")
            self.ec.set(traceroute, "printTimestamp", True)
            self.ec.set(traceroute, "continuous", True)
            self.ec.set(traceroute, "target", self.get("host"))
            self.ec.set(traceroute, "earlyStart", True)
            self.ec.register_connection(traceroute, self.node.guid)
            self.ec.register_connection(traceroute, self.guid)
            # schedule mtr deploy
            self.ec.deploy(guids=[traceroute], group = self.deployment_group)

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
        command = self.get('command')
        env = self.get('env')
        
        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = self._stop_command
            (out, err), proc = self.execute_command(command, env,
                    blocking = True)

            self.set_stopped()

            if err:
                msg = " Failed to execute command '%s'" % command
                self.error(msg, out, err)
                raise RuntimeError, msg

    @property
    def _start_command(self):
        uri = self.get("uri") or ""
        protocol = self.get("protocol") or ""
        ip = self.get("ip") or "" 
        port = self.get("port") or ""

        # add ccnx:/example.com/ udp 224.0.0.204 52428
        return "ccndc add %(uri)s %(protocol)s %(host)s %(port)s" % ({
            "uri" : uri,
            "protocol": protocol,
            "host": ip,
            "port": port
            })

    @property
    def _stop_command(self):
        uri = self.get("uri") or ""
        protocol = self.get("protocol") or ""
        ip = self.get("ip") or ""
        port = self.get("port") or ""

        # add ccnx:/example.com/ udp 224.0.0.204 52428
        return "ccndc del %(uri)s %(protocol)s %(host)s %(port)s" % ({
            "uri" : uri,
            "protocol": protocol,
            "host": ip,
            "port": port
            })

    @property
    def _environment(self):
        return self.ccnd.path
       
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

