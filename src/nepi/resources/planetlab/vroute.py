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
from nepi.resources.planetlab.node import PlanetlabNode
from nepi.resources.planetlab.tap import PlanetlabTap
from nepi.util.timefuncs import tnow, tdiffsec

import os
import time

PYTHON_VSYS_VERSION = "1.0"

@clsinit_copy
class PlanetlabVroute(LinuxApplication):
    _rtype = "PlanetlabVroute"
    _help = "Creates a Vroute on a PlanetLab host"
    _backend = "planetlab"

    @classmethod
    def _register_attributes(cls):
        action = Attribute("action", "Either add or del",
              allowed = ["add", "del"],
              flags = Flags.Design)

        network = Attribute("network", "IPv4 Network Address",
              flags = Flags.Design)

        cls._register_attribute(action)
        cls._register_attribute(network)

    def __init__(self, ec, guid):
        super(PlanetlabVroute, self).__init__(ec, guid)
        self._home = "vroute-%s" % self.guid

    @property
    def tap(self):
        tap = self.get_connected(PlanetlabTap.get_rtype())
        if tap: return tap[0]
        return None

    @property
    def node(self):
        node = self.tap.get_connected(PlanetlabNode.get_rtype())
        if node: return node[0]
        return None

    def upload_sources(self):
        # upload vif-creation python script
        pl_vroute = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-vroute.py")

        self.node.upload(pl_vroute,
                os.path.join(self.node.src_dir, "pl-vroute.py"),
                overwrite = False)

        # upload stop.sh script
        stop_command = self.replace_paths(self._stop_command)
        self.node.upload(stop_command,
                os.path.join(self.app_home, "stop.sh"),
                text = True,
                # Overwrite file every time. 
                # The stop.sh has the path to the socket, wich should change
                # on every experiment run.
                overwrite = True)

    def upload_start_command(self):
        # Overwrite file every time. 
        # The stop.sh has the path to the socket, wich should change
        # on every experiment run.
        super(PlanetlabVroute, self).upload_start_command(overwrite = True)

        (out, err), proc = self.execute_command(self.get("command"), blocking = True)
 
    def do_deploy(self):
        if not self.tap or self.tap.state < ResourceState.PROVISIONED:
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("command"):
                self.set("command", self._start_command)

            self.do_discover()
            self.do_provision()

            self.debug("----- READY ---- ")
            self.set_ready()

    def do_start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            # Vroute started during deployment
            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):

        command = self.get('command') or ''

        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % self._stop_command)

            command = "bash %s" % os.path.join(self.app_home, "stop.sh")
            (out, err), proc = self.execute_command(command,
                    blocking = True)

            self.set_stopped()

    def do_release(self):
        # Node needs to wait until all associated RMs are released
        # to be released
        if not self.get("tearDown"):
            self.set("tearDown", self._tear_down_command())

        super(PlanetlabVroute, self).do_release()

    def _tear_down_command(self):
        if self.get("action") == "del":
            return

        return self._stop_command

    @property
    def _start_command(self):
        command = ["sudo -S python ${SRC}/pl-vroute.py"]
        command.append("-a %s" % self.get("action"))
        command.append("-n %s" % self.get("network"))
        command.append("-p %d" % self.tap.get("prefix4"))
        command.append("-g %s" % self.tap.get("pointopoint"))
        command.append("-f %s" % self.tap.get("deviceName"))
        return " ".join(command)

    @property
    def _stop_command(self):
        command = ["sudo -S python ${SRC}/pl-vroute.py"]
        command.append("-a %s" % "del")
        command.append("-n %s" % self.get("network"))
        command.append("-p %d" % self.tap.get("prefix4"))
        command.append("-g %s" % self.tap.get("pointopoint"))
        command.append("-f %s" % self.tap.get("deviceName"))
        return " ".join(command)

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

