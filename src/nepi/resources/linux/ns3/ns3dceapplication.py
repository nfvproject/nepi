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

@clsinit_copy
class NS3LinuxDceApplication(NS3BaseDceApplication):
    _rtype = "ns3::LinuxDceApplication"

    @classmethod
    def _register_attributes(cls):
        sources = Attribute("sources",
                "Path to tar.gz file with sources for the application execute in DCE. "
                "Sources will be uploaded to ${SRC} and it is the responsibility of "
                "the build instructions (in the build attribute) to copy the compiled "
                "binaries to the ${BIN_DCE} directory",
                flags = Flags.Design)

        build = Attribute("build",
                "Instructions to compile sources DCE-compatible way. "
                "Note that sources will be uploaded to ${SRC} and the "
                "build instructions are responsible for copying the "
                "binaries to the ${BIN_DCE} directory. ",
                flags = Flags.Design)

        starttime = Attribute("StartTime",
            "Time at which the application will start",
            default = "+0.0ns",  
            flags = Flags.Reserved | Flags.Construct)


        stoptime = Attribute("StopTime",
            "Time at which the application will stop",
            default = "+0.0ns",  
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(sources)
        cls._register_attribute(build)
        cls._register_attribute(stoptime)
        cls._register_attribute(starttime)

    def _instantiate_object(self):
        command = []
        
        sources = self.get("sources")
        if sources:
            self.info("Uploading sources %s " % sources)
            scmd = self.simulation.upload_extra_sources(sources = sources)
            if scmd:
                command.append(scmd)
                
        build = self.get("build")
        if build:
            bcmd = self.simulation.build(build = build)
            if bcmd:
                command.append(bcmd)

        if command:
            deploy_command = ";".join(command)
            prefix = "%d_deploy" % self.guid 
            self.simulation.execute_deploy_command(deploy_command, prefix=prefix)

