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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow, tdiffsec
from nepi.resources.ns3.ns3simulator import NS3Simulator
from nepi.resources.linux.ns3.ns3client import LinuxNS3Client

import os

@clsinit_copy
class LinuxNS3Simulator(LinuxApplication, NS3Simulator):
    _rtype = "LinuxNS3Simulator"

    @classmethod
    def _register_attributes(cls):
        socket_name = Attribute("socketName",
            "Local socket name to communicate with the ns-3 server ",
            flags = Flags.Design)

        cls._register_attribute(socket_name)

    def __init__(self, ec, guid):
        super(LinuxApplication, self).__init__(ec, guid)
        super(NS3Simulator, self).__init__()

        self._client = None
        self._home = "ns3-simu-%s" % self.guid

    def do_deploy(self):
        if not self.node or self.node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            
            # ccnd needs to wait until node is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            
            # TODO: Create socket!!
            socket_name = self.get("socketName")
            self._client = LinuxNS3Client(socket_name)

            #self.do_discover()
            #self.do_provision()

            self.debug("----- READY ---- ")
            self.set_ready()

