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
from nepi.resources.ns3.ns3ccndceapplication import NS3BaseCCNDceApplication

@clsinit_copy
class LinuxNS3CCNDceApplication(NS3BaseCCNDceApplication):
    _rtype = "ns3::LinuxCCNDceApplication"

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

        depends = Attribute("depends", 
                "Space-separated list of packages required to run the application",
                flags = Flags.Design)

        files = Attribute("files", 
                "Semi-colon separated list of 'key=value' pairs to set as "
                "DCE files (AddFile). The key should be a path to a local file "
                "and the key is the path to be set in DCE for that file" ,
                flags = Flags.Design)

        stdinfile = Attribute("stdinFile", 
                "File to set as StdinFile. The value shoudl be either an empty "
                "or a path to a local file ",
                flags = Flags.Design)
        
        cls._register_attribute(sources)
        cls._register_attribute(build)
        cls._register_attribute(depends)
        cls._register_attribute(files)
        cls._register_attribute(stdinfile)

    def _instantiate_object(self):
        command = []

        # Install package dependencies required to run the binary 
        depends = self.get("depends")
        if depends:
            dcmd = self.simulation.install_dependencies(depends = depends)
            if dcmd:
                command.append(dcmd)
       
        # Upload sources to generate the binary
        sources = self.get("sources")
        if sources:
            scmd = self.simulation.upload_extra_sources(sources = sources)
            if scmd:
                command.append(scmd)
                
        # Upload instructions to build the binary
        build = self.get("build")
        if build:
            bcmd = self.simulation.build(build = build)
            if bcmd:
                command.append(bcmd)

        # Upload CCN files (e.g. repo)
        files = self.get("files")
        if files:
            upload = []
            for file in map(str.strip, files.split(";")):
                localpath, dcepath = files.split("=")
                upload.append(localpath)

            sources = ";".join(upload)
            fcmd = self.simulation.upload_extra_sources(sources = sources,
                    src_dir = self.simulation.app_home)

            if fcmd:
                command.append(fcmd)

        if command:
            deploy_command = ";".join(command)
            prefix = "%d_deploy" % self.guid 
            self.simulation.execute_deploy_command(deploy_command, prefix=prefix)

