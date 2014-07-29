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
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.node import LinuxNode
from nepi.util.timefuncs import tnow, tdiffsec

import os
import socket
import time

PYTHON_VSYS_VERSION = "1.0"

@clsinit_copy
class LinuxTap(LinuxApplication):
    _rtype = "LinuxTap"
    _help = "Creates a TAP device on a Linux host"
    _backend = "linux"

    @classmethod
    def _register_attributes(cls):
        ip4 = Attribute("ip4", "IPv4 Address",
              flags = Flags.Design)

        mac = Attribute("mac", "MAC Address",
                flags = Flags.Design)

        prefix4 = Attribute("prefix4", "IPv4 network prefix",
                type = Types.Integer,
                flags = Flags.Design)

        mtu = Attribute("mtu", "Maximum transmition unit for device",
                type = Types.Integer)

        devname = Attribute("deviceName", 
                "Name of the network interface (e.g. eth0, wlan0, etc)",
                flags = Flags.NoWrite)

        up = Attribute("up", "Link up", 
                type = Types.Bool)
        
        pointopoint = Attribute("pointopoint", "Peer IP address", 
                flags = Flags.Design)

        txqueuelen = Attribute("txqueuelen", "Length of transmission queue", 
                flags = Flags.Design)

        txqueuelen = Attribute("txqueuelen", "Length of transmission queue", 
                flags = Flags.Design)

        gre_key = Attribute("greKey", 
                "GRE key to be used to configure GRE tunnel", 
                default = "1",
                flags = Flags.Design)

        gre_remote = Attribute("greRemote", 
                "Public IP of remote endpoint for GRE tunnel", 
                flags = Flags.Design)

        tear_down = Attribute("tearDown", 
                "Bash script to be executed before releasing the resource",
                flags = Flags.Design)

        cls._register_attribute(ip4)
        cls._register_attribute(mac)
        cls._register_attribute(prefix4)
        cls._register_attribute(mtu)
        cls._register_attribute(devname)
        cls._register_attribute(up)
        cls._register_attribute(pointopoint)
        cls._register_attribute(txqueuelen)
        cls._register_attribute(gre_key)
        cls._register_attribute(gre_remote)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(LinuxTap, self).__init__(ec, guid)
        self._home = "tap-%s" % self.guid
        self._gre_enabled = False

    @property
    def node(self):
        node = self.get_connected(LinuxNode.get_rtype())
        if node: return node[0]
        return None

    @property
    def gre_enabled(self):
        if not self._gre_enabled:
            from nepi.resources.linux.gretunnel import LinuxGRETunnel
            gre = self.get_connected(LinuxGRETunnel.get_rtype())
            if gre: self._gre_enabled = True

        return self._gre_enabled

    def upload_sources(self):
        # upload stop.sh script
        stop_command = self.replace_paths(self._stop_command)

        self.node.upload(stop_command,
                os.path.join(self.app_home, "stop.sh"),
                text = True,
                # Overwrite file every time. 
                # The stop.sh has the path to the socket, which should change
                # on every experiment run.
                overwrite = True)

    def upload_start_command(self):
        # If GRE mode is enabled, TAP creation is delayed until the
        # tunnel is established
        if not self.gre_enabled:
            # We want to make sure the device is up and running
            # before the deploy is over, so we execute the 
            # start script now and wait until it finishes. 
            command = self.get("command")
            command = self.replace_paths(command)

            shfile = os.path.join(self.app_home, "start.sh")
            self.node.run_and_wait(command, self.run_home,
                shfile = shfile,
                overwrite = True)

    def do_deploy(self):
        if not self.node or self.node.state < ResourceState.PROVISIONED:
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("deviceName"):
                self.set("deviceName", "%s%d" % (self.vif_prefix, self.guid)) 

            if not self.get("command"):
                self.set("command", self._start_command)

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
        command = self.get('command') or ''
        
        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = "bash %s" % os.path.join(self.app_home, "stop.sh")
            (out, err), proc = self.execute_command(command,
                    blocking = True)

            if err:
                msg = " Failed to stop command '%s' " % command
                self.error(msg, out, err)

            self.set_stopped()

    @property
    def state(self):
        state_check_delay = 0.5
        if self._state == ResourceState.STARTED and \
                tdiffsec(tnow(), self._last_state_check) > state_check_delay:

            if self.get("deviceName"):
                (out, err), proc = self.node.execute("ifconfig")

                if out.strip().find(self.get("deviceName")) == -1: 
                    # tap is not running is not running (socket not found)
                    self.set_stopped()

            self._last_state_check = tnow()

        return self._state

    def do_release(self):
        # Node needs to wait until all associated RMs are released
        # to be released
        from nepi.resources.linux.tunnel import LinuxTunnel
        rms = self.get_connected(LinuxTunnel.get_rtype())

        for rm in rms:
            if rm.state < ResourceState.STOPPED:
                self.ec.schedule(reschedule_delay, self.release)
                return 

        super(LinuxTap, self).do_release()

    def gre_connect(self, remote_endpoint, connection_app_home,
            connection_run_home):
        gre_connect_command = self._gre_connect_command(
                remote_endpoint, connection_run_home)

        # upload command to connect.sh script
        shfile = os.path.join(connection_app_home, "gre-connect.sh")
        endpoint.node.upload(gre_connect_command,
                shfile,
                text = True, 
                overwrite = False)

        # invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node.run(cmd, connection_run_home) 
             
        # check if execution errors occurred
        msg = " Failed to connect endpoints "
        
        if proc.poll() or err:
            self.error(msg, out, err)
            raise RuntimeError, msg
    
        # Wait for pid file to be generated
        pid, ppid = self.node.wait_pid(connection_run_home)
        
        # If the process is not running, check for error information
        # on the remote machine
        if not pid or not ppid:
            (out, err), proc = self.node.check_errors(connection_run_home)
            # Out is what was written in the stderr file
            if err:
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg
        
        return True

    def _gre_connect_command(self, remote_endpoint, connection_run_home): 
        # Set the remote endpoint
        self.set("pointopoint", remote_endpoint.get("ip4"))
        self.set("greRemote", socket.gethostbyname(
            remote_endpoint.node.get("hostname")))

        # Generate GRE connect command
        command = ["("]
        command.append(self._stop_command)
        command.append(") ; (")
        command.append(self._start_gre_command)
        command.append(")")

        command = " ".join(command)
        command = self.replace_paths(command)

        return command

    @property
    def _start_command(self):
        command = []
        command.append("sudo -S ip tuntap add %s mode tap" % self.get("deviceName"))
        command.append("sudo -S ip link set %s up" % self.get("deviceName"))
        command.append("sudo -S ip addr add %s/%d dev %s" % (
            self.get("ip4"),
            self.get("prefix4"),
            self.get("deviceName"),
            ))
        return ";".join(command)

    @property
    def _stop_command(self):
        command = []
        command.append("sudo -S ip link set %s down" % self.get("deviceName"))
        command.append("sudo -S ip link del %s" % self.get("deviceName"))
        
        return ";".join(command)

    @property
    def _start_gre_command(self):
        command = []
        command.append("sudo -S modprobe ip_gre")
        command.append("sudo -S ip link add %s type gre remote %s local %s ttl 64 csum key %s" % (
                self.get("deviceName"),
                self.get("greRemote"),
                socket.gethostbyname(self.node.get("hostname")),
                self.get("greKey")
            ))
        command.append("sudo -S addr add dev %s %s/%d peer %s/%d" % (
                self.get("deviceName"),
                self.get("ip4"),
                self.get("prefix4"),
                self.get("pointopoint"),
                self.get("prefix4"),
                ))
        command.append("sudo -S ip link set %s up " % self.get("deviceName"))

        return ";".join(command)

    @property
    def vif_type(self):
        return "IFF_TAP"

    @property
    def vif_prefix(self):
        return "tap"

    def sock_name(self):
        return os.path.join(self.run_home, "tap.sock")

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

