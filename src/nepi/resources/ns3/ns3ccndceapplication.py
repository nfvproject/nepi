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

@clsinit_copy
class NS3BaseCCNDceApplication(NS3BaseDceApplication):
    _rtype = "abstract::ns3::CCNDceApplication"

    @classmethod
    def _register_attributes(cls):
        files = Attribute("files", 
                "Semi-colon separated list of 'key=value' pairs to set as "
                "DCE files (AddFile). The key should be a path to a local file "
                "and the key is the path to be set in DCE for that file" ,
                flags = Flags.Design)

        stdinfile = Attribute("stdinFile", 
                "File to set as StdinFile. The value shoudl be either an empty "
                "or a path to a local file ",
                flags = Flags.Design)

        cls._register_attribute(files)
        cls._register_attribute(stdinfile)

    def _instantiate_object(self):
        pass

    def _connect_object(self):
        node = self.node
        if node.uuid not in self.connected:
            self._connected.add(node.uuid)

            # Preventing concurrent access to the DceApplicationHelper
            # from different DceApplication RMs
            with self.simulation.dce_application_lock:
                self.simulation.invoke(
                        self.simulation.ccn_client_helper_uuid, 
                        "ResetArguments") 

                self.simulation.invoke(
                        self.simulation.ccn_client_helper_uuid, 
                        "ResetEnvironment") 

                self.simulation.invoke(
                        self.simulation.ccn_client_helper_uuid, 
                        "SetBinary", self.get("binary")) 

                self.simulation.invoke(
                        self.simulation.ccn_client_helper_uuid, 
                        "SetStackSize", self.get("stackSize")) 

                arguments = self.get("arguments")
                if arguments:
                    for arg in map(str.strip, arguments.split(";")):
                        self.simulation.invoke(
                                self.simulation.ccn_client_helper_uuid, 
                            "AddArgument", arg)

                environment = self.get("environment")
                if environment:
                    for env in map(str.strip, environment.split(";")):
                        key, val = env.split("=")
                        self.simulation.invoke(
                                self.simulation.ccn_client_helper_uuid, 
                            "AddEnvironment", key, val)

                if self.has_attribute("files"):
                    files = self.get("files")
                    if files:
                        for files in map(str.strip, files.split(";")):
                            remotepath, dcepath = files.split("=")
                            localpath = "${SHARE}/" + os.path.basename(remotepath)
                            self.simulation.invoke(
                                    self.simulation.ccn_client_helper_uuid, 
                                "AddFile", localpath, dcepath)

                if self.has_attribute("stdinFile"):
                    stdinfile = self.get("stdinFile")
                    if stdinfile:
                        if stdinfile != "":
                            stdinfile = "${SHARE}/" + os.path.basename(stdinfile)
        
                        self.simulation.invoke(
                                self.simulation.ccn_client_helper_uuid, 
                                "SetStdinFile", stdinfile)

                apps_uuid = self.simulation.invoke(
                        self.simulation.ccn_client_helper_uuid, 
                        "InstallInNode", self.node.uuid)

            self._uuid = self.simulation.invoke(apps_uuid, "Get", 0)

            if self.has_changed("StartTime"):
                self.simulation.ns3_set(self.uuid, "StartTime", self.get("StartTime"))

            if self.has_changed("StopTime"):
                self.simulation.ns3_set(self.uuid, "StopTime", self.get("StopTime"))


