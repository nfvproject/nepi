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
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.planetlab.node import PlanetlabNode
from nepi.util.timefuncs import tnow, tdiffsec

import os
import time

# TODO: - routes!!!
#       - Instead of doing an infinite loop, open a port for communication allowing
#           to pass the fd to another process

PYTHON_VSYS_VERSION = "1.0"

@clsinit_copy
class PlanetlabTap(LinuxApplication):
    _rtype = "PlanetlabTap"

    @classmethod
    def _register_attributes(cls):
        ip4 = Attribute("ip4", "IPv4 Address",
              flags = Flags.ExecReadOnly)

        mac = Attribute("mac", "MAC Address",
                flags = Flags.ExecReadOnly)

        prefix4 = Attribute("prefix4", "IPv4 network prefix",
                type = Types.Integer,
                flags = Flags.ExecReadOnly)

        mtu = Attribute("mtu", "Maximum transmition unit for device",
                type = Types.Integer)

        devname = Attribute("deviceName", 
                "Name of the network interface (e.g. eth0, wlan0, etc)",
                flags = Flags.ReadOnly)

        up = Attribute("up", "Link up", type = Types.Bool)
        
        snat = Attribute("snat", "Set SNAT=1", type = Types.Bool,
                flags = Flags.ReadOnly)
        
        pointopoint = Attribute("pointopoint", "Peer IP address", 
                flags = Flags.ReadOnly)

        tear_down = Attribute("tearDown", "Bash script to be executed before " + \
                "releasing the resource",
                flags = Flags.ExecReadOnly)

        cls._register_attribute(ip4)
        cls._register_attribute(mac)
        cls._register_attribute(prefix4)
        cls._register_attribute(mtu)
        cls._register_attribute(devname)
        cls._register_attribute(up)
        cls._register_attribute(snat)
        cls._register_attribute(pointopoint)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(PlanetlabTap, self).__init__(ec, guid)
        self._home = "tap-%s" % self.guid

    @property
    def node(self):
        node = self.get_connected(PlanetlabNode.rtype())
        if node: return node[0]
        return None

    def upload_sources(self):
        depends = "mercurial make gcc"
        self.set("depends", depends)

        install = ( " ( "
                    "   python -c 'import vsys, os;  vsys.__version__ == \"%(version)s\" or os._exit(1)' "
                    " ) "
                    " ||"
                    " ( "
                    "   cd ${SRC} ; "
                    "   hg clone http://nepi.inria.fr/code/python-vsys ; "
                    "   cd python-vsys ; "
                    "   make all ; "
                    "   sudo -S make install "
                    " )" ) % ({
                        "version": PYTHON_VSYS_VERSION
                        })

        self.set("install", install)

    def upload_start_command(self):
        # upload tap-creation python script
        pl_tap_create = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-tap-create.py")
        self.node.upload(pl_tap_create,
                os.path.join(self.app_home, "pl-vif-create.py"),
                overwrite = False)

        # upload start.sh
        start_command = self.replace_paths(self._start_command)
        
        self.info("Uploading command '%s'" % start_command)
        
        self.set("command", start_command)

        self.node.upload(start_command,
                os.path.join(self.app_home, "start.sh"),
                text = True, 
                overwrite = False)

        # upload tap-stop python script
        pl_tap_stop = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-tap-stop.py")
        self.node.upload(pl_tap_stop,
                os.path.join(self.app_home, "pl-vif-stop.py"),
                overwrite = False)

        # upload stop.sh script
        stop_command = self.replace_paths(self._stop_command)
        self.node.upload(stop_command,
                os.path.join(self.app_home, "stop.sh"),
                text = True, 
                overwrite = False)

        # We want to make sure the device is up and running
        # before the deploy finishes (so things will be ready
        # before other stuff starts running).
        # Run the command as a bash script in background,
        # in the host ( but wait until the command has
        # finished to continue )
        self._run_in_background()
        
        # Retrive if_name
        if_name = self.wait_if_name()
        self.set("deviceName", if_name) 

    def deploy(self):
        if not self.node or self.node.state < ResourceState.PROVISIONED:
            self.ec.schedule(reschedule_delay, self.deploy)
        else:

            try:
                self.discover()
                self.provision()
            except:
                self.fail()
                raise
 
            self.debug("----- READY ---- ")
            self._ready_time = tnow()
            self._state = ResourceState.READY

    def start(self):
        if self._state == ResourceState.READY:
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
        command = self.get('command') or ''
        state = self.state
        
        if state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = "bash %s" % os.path.join(self.app_home, "stop.sh")
            (out, err), proc = self.execute_command(command,
                    blocking = True)

            self._stop_time = tnow()
            self._state = ResourceState.STOPPED

    @property
    def state(self):
        # First check if the ccnd has failed
        state_check_delay = 0.5
        if self._state == ResourceState.STARTED and \
                tdiffsec(tnow(), self._last_state_check) > state_check_delay:

            if self.get("deviceName"):
                (out, err), proc = self.node.execute("ifconfig")

                if out.strip().find(self.get("deviceName")) == -1: 
                    # tap is not running is not running (socket not found)
                    self._state = ResourceState.FINISHED

            self._last_state_check = tnow()

        return self._state

    def wait_if_name(self):
        """ Waits until the if_name file for the command is generated, 
            and returns the if_name for the devide """
        if_name = None
        delay = 1.0

        for i in xrange(4):
            (out, err), proc = self.node.check_output(self.run_home, "if_name")

            if out:
                if_name = out.strip()
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = "Couldn't retrieve if_name"
            self.error(msg, out, err)
            self.fail()
            raise RuntimeError, msg

        return if_name

    @property
    def _start_command(self):
        command = ["sudo -S python ${APP_HOME}/pl-vif-create.py"]
        
        command.append("-t %s" % self.vif_type)
        command.append("-a %s" % self.get("ip4"))
        command.append("-n %d" % self.get("prefix4"))
        command.append("-f %s " % self.if_name_file)
        command.append("-S %s " % self.sock_name)
        if self.get("snat") == True:
            command.append("-s")
        if self.get("pointopoint"):
            command.append("-p %s" % self.get("pointopoint"))

        return " ".join(command)

    @property
    def _stop_command(self):
        command = ["sudo -S python ${APP_HOME}/pl-vif-stop.py"]
        
        command.append("-S %s " % self.sock_name)
        return " ".join(command)

    @property
    def vif_type(self):
        return "IFF_TAP"

    @property
    def if_name_file(self):
        return os.path.join(self.run_home, "if_name")

    @property
    def sock_name(self):
        return os.path.join(self.run_home, "tap.sock")

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

