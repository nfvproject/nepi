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
from nepi.resources.ns3.ns3dceapplication import NS3BaseDceApplication

import os
import threading

@clsinit_copy
class NS3BaseCCNDceApplication(NS3BaseDceApplication):
    _rtype = "abstract::ns3::CCNDceApplication"

    # Lock used to synchronize usage of CcnClientHelper 
    ccn_client_lock = threading.Lock()
    _ccn_client_helper_uuid = None

    @property
    def ccn_client_helper_uuid(self):
        if not self._ccn_client_helper_uuid:
            self._ccn_client_helper_uuid = self.simulation.create("CcnClientHelper")
        return self._ccn_client_helper_uuid

    def _instantiate_object(self):
        pass

    def _connect_object(self):
        node = self.node
        if node.uuid not in self.connected:
            self._connected.add(node.uuid)

            # Preventing concurrent access to the DceApplicationHelper
            # from different DceApplication RMs
            with self.ccn_client_lock:
                self.simulation.invoke(
                        self.ccn_client_helper_uuid, 
                        "ResetArguments") 

                self.simulation.invoke(
                        self.ccn_client_helper_uuid, 
                        "ResetEnvironment") 

                self.simulation.invoke(
                        self.ccn_client_helper_uuid, 
                        "SetBinary", self.get("binary")) 

                self.simulation.invoke(
                        self.ccn_client_helper_uuid, 
                        "SetStackSize", self.get("stackSize")) 

                arguments = self.get("arguments")
                if arguments:
                    for arg in map(str.strip, arguments.split(";")):
                        self.simulation.invoke(
                                 self.ccn_client_helper_uuid, 
                                "AddArgument", arg)

                environment = self.get("environment")
                if environment:
                    for env in map(str.strip, environment.split(";")):
                        key, val = env.split("=")
                        self.simulation.invoke(
                                self.ccn_client_helper_uuid, 
                               "AddEnvironment", key, val)

                if self.has_attribute("files"):
                    files = self.get("files")
                    if files:
                        for file in map(str.strip, files.split(";")):
                            remotepath, dcepath = file.split("=")
                            localpath =  os.path.join(self.simulation.app_home, 
                                    os.path.basename(remotepath))
                            self.simulation.invoke(
                                    self.ccn_client_helper_uuid, 
                                    "AddFile", localpath, dcepath)

                if self.has_attribute("stdinFile"):
                    stdinfile = self.get("stdinFile")
                    if stdinfile:
                        # stdinfile might be an empty text that should be set as
                        # stdin
                        if stdinfile != "":
                            stdinfile = os.path.join(self.simulation.app_home, 
                                os.path.basename(stdinfile))
       
                        self.simulation.invoke(
                                self.ccn_client_helper_uuid, 
                                "SetStdinFile", stdinfile)

                apps_uuid = self.simulation.invoke(
                        self.ccn_client_helper_uuid, 
                        "InstallInNode", self.node.uuid)

                """
                container_uuid = self.simulation.create("NodeContainer")
                self.simulation.invoke(container_uuid, "Add", self.node.uuid)
                apps_uuid = self.simulation.invoke(
                        self.ccn_client_helper_uuid, 
                        "Install", container_uuid)
                """

            self._uuid = self.simulation.invoke(apps_uuid, "Get", 0)

            if self.has_changed("StartTime"):
                self.simulation.ns3_set(self.uuid, "StartTime", self.get("StartTime"))

            if self.has_changed("StopTime"):
                self.simulation.ns3_set(self.uuid, "StopTime", self.get("StopTime"))


