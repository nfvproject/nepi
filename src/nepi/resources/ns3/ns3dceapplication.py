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
from nepi.execution.resource import clsinit_copy, ResourceState, reschedule_delay
from nepi.resources.ns3.ns3application import NS3BaseApplication

@clsinit_copy
class NS3BaseDceApplication(NS3BaseApplication):
    _rtype = "abstract::ns3::DceApplication"

    @classmethod
    def _register_attributes(cls):
        binary = Attribute("binary", 
                "Name of binary to execute",
                flags = Flags.Design)

        stack_size = Attribute("stackSize", 
                "Stack Size for DCE",
                type = Types.Integer,
                default = 1<<20,                
                flags = Flags.Design)

        arguments = Attribute("arguments", 
                "Semi-colon separated list of arguments for the application",
                flags = Flags.Design)

        cls._register_attribute(binary)
        cls._register_attribute(stack_size)
        cls._register_attribute(arguments)

    @property
    def node(self):
        from nepi.resources.ns3.ns3node import NS3BaseNode
        nodes = self.get_connected(NS3BaseNode.get_rtype())

        if not nodes: 
            msg = "DceApplication not connected to node"
            self.error(msg)
            raise RuntimeError, msg

        if nodes[0].get("enableDCE") == False:
            raise RuntimeError("DceApplication not connected to DCE enabled node")

        return nodes[0]
    
    def _instantiate_object(self):
        pass

    def _connect_object(self):
        node = self.node
        if node.uuid not in self.connected:
            self._connected.add(node.uuid)

            self.simulation.invoke(self.simulation.dce_application_helper_uuid, 
                    "ResetArguments") 

            self.simulation.invoke(self.simulation.dce_application_helper_uuid, 
                    "SetBinary", self.get("binary")) 

            self.simulation.invoke(self.simulation.dce_application_helper_uuid, 
                    "SetStackSize", self.get("stackSize")) 

            arguments = self.get("arguments") or ""
            for arg in map(str.strip, arguments.split(";")):
                self.simulation.invoke(self.simulation.dce_application_helper_uuid, 
                    "AddArgument", arg) 

            apps_uuid = self.simulation.invoke(self.simulation.dce_application_helper_uuid, 
                    "InstallInNode", self.node.uuid)

            app_uuid = self.simulation.invoke(apps_uuid, "Get", 0)

            if self.has_changed("StartTime"):
                self.simulation.ns3_set(app_uuid, "StartTime", self.get("StartTime"))

            if self.has_changed("StopTime"):
                self.simulation.ns3_set(app_uuid, "StopTime", self.get("StopTime"))

            self._uuid = self.simulation.invoke(self.simulation.dce_application_helper_uuid, 
                    "GetDCEApplication", app_uuid)

    def do_stop(self):
        if self.state == ResourceState.STARTED:
            # No need to do anything, simulation.Destroy() will stop every object
            self.info("Stopping command '%s'" % command)
            self.simulation.invoke(self.uuid, "Stop")
            self.set_stopped()

    def do_start(self):
        if self.simulation.state < ResourceState.STARTED:
            self.debug("---- RESCHEDULING START ----" )
            self.ec.schedule(reschedule_delay, self.start)
        else:
            self._configure_traces()
            super(NS3BaseApplication, self).do_start()
            self._start_time = self.simulation.start_time

    def _configure_traces(self):
        pid = self.simulation.invoke(self.uuid, "GetPid")
        node_id = self.simulation.invoke(self.node.uuid, "GetId")
        self._trace_filename["stdout"] = "files-%s/var/log/%s/stdout" % (node_id, pid)
        self._trace_filename["stderr"] = "files-%s/var/log/%s/stderr" % (node_id, pid)
        self._trace_filename["status"] = "files-%s/var/log/%s/status" % (node_id, pid)
        self._trace_filename["cmdline"] = "files-%s/var/log/%s/cmdline" % (node_id, pid)


