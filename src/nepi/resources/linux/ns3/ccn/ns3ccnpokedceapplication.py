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
from nepi.execution.resource import clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.ns3.ccn.ns3ccndceapplication \
        import LinuxNS3CCNDceApplication

import os
import tempfile

@clsinit_copy
class LinuxNS3DceCCNPoke(LinuxNS3CCNDceApplication):
    _rtype = "ns3::LinuxDceCCNPoke"

    @classmethod
    def _register_attributes(cls):
        content_name = Attribute("contentName",
                "Content name for the requested content object. ",
                flags = Flags.Design)
        content = Attribute("content",
                "Content to poke (as a text string). ",
                flags = Flags.Design)

        cls._register_attribute(content_name)
        cls._register_attribute(content)

    def _instantiate_object(self):
        if not self.get("binary"):
            self.set("binary", "ccnpoke")
            
        if self.get("contentName"):
            self.set("arguments", self.get("contentName"))

        # Create temporary local file to store content
        content = self.get("content")
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(content)
        f.close()

        localpath = f.name
        dcepath = os.path.join("/tmp", os.path.basename(localpath))

        self.set("environment", "HOME=/root")
        self.set("files", "%s=%s" % (localpath, dcepath))
        self.set("stdinFile", dcepath)

        super(LinuxNS3DceCCNPoke, self)._instantiate_object()

