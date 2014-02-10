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

from nepi.execution.resource import clsinit_copy, ResourceState
from nepi.resources.ns3.ns3base import NS3Base

@clsinit_copy
class NS3BaseApplication(NS3Base):
    _rtype = "abstract::ns3::Application"

    @property
    def node(self):
        from nepi.resources.ns3.ns3node import NS3BaseNode
        nodes = self.get_connected(NS3BaseNode.get_rtype())

        if not nodes: 
            msg = "Application not connected to node"
            self.error(msg)
            raise RuntimeError, msg

        return nodes[0]

    @property
    def _rms_to_wait(self):
        rms = set()
        rms.add(self.node)
        return rms

    def _connect_object(self):
        node = self.node
        if node.uuid not in self.connected:
            self.simulation.invoke(node.uuid, "AddApplication", self.uuid)
            self._connected.add(node.uuid)

    def do_stop(self):
        if self.state == ResourceState.STARTED:
            # No need to do anything, simulation.Destroy() will stop every object
            self.info("Stopping command '%s'" % command)
            self.simulation.invoke(self.uuid, "Stop")
            self.set_stopped()

    @property
    def state(self):
        if self._state == ResourceState.STARTED:
            is_running = self.simulation.invoke(self.uuid, "isAppRunning")

            if not is_running:
                self.set_stopped()

        return self._state

