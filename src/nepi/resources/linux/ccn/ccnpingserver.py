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
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.linux.ccn.ccnapplication import LinuxCCNApplication
from nepi.util.timefuncs import tnow, tdiffsec

import os

@clsinit_copy
class LinuxCCNPingServer(LinuxCCNApplication):
    _rtype = "LinuxCCNPingServer"

    @classmethod
    def _register_attributes(cls):
        daemon = Attribute("d",
            "Run ccnping server as a daemon in background",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        freshness = Attribute("x",
            "Set FreshnessSeconds",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        prefix = Attribute("prefix",
            "Prefix to serve content (e.g. ccnx:/name/prefix)",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(daemon)
        cls._register_attribute(freshness)
        cls._register_attribute(prefix)

    def __init__(self, ec, guid):
        super(LinuxCCNPingServer, self).__init__(ec, guid)
        self._home = "ccnping-serv-%s" % self.guid

    def do_deploy(self):
        if not self.get("command"):
            self.set("command", self._start_command)

        if not self.get("env"):
            self.set("env", self._environment)

        if not self.get("depends"):
            self.set("depends", self._dependencies)

        if not self.get("build"):
            self.set("build", self._build)

        if not self.get("install"):
            self.set("install", self._install)

        super(LinuxCCNPingServer, self).do_deploy()

    @property
    def _start_command(self):
        args = []
        args.append("ccnpingserver")
        args.append(self.get("prefix"))
        if self.get("d") == True:
            args.append("-d")
        if self.get("x"):
            args.append("-x %d" % self.get("x"))

        command = " ".join(args)

        return command

    @property
    def _dependencies(self):
        return "git"

    @property
    def _build(self):
        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${BIN}/ccnping && "
                " echo 'binaries found, nothing to do' "
            " ) || ( "
            # If not, untar and build
                " ( "
                    " git clone git://github.com/NDN-Routing/ccnping ${SRC}/ccnping "
                 " ) && "
                    # build
                    "cd ${SRC}/ccnping && "
                    " ( "
                    " ./configure LDFLAGS=-L${SRC}/ccnx-0.7.2/lib CFLAGS=-I${SRC}/ccnx-0.7.2/include "
                    " --prefix=${BIN}/ccnping && make "
                    " ) "
             " )") 

    @property
    def _install(self):
        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${BIN}/ccnping && "
                " echo 'binaries found, nothing to do' "
            " ) || ( "
            # If not, install
                "  mkdir -p ${BIN}/ccnping && "
                "  mv ${SRC}/ccnping/ccnping ${BIN}/ccnping/ && "
                "  mv ${SRC}/ccnping/ccnpingserver ${BIN}/ccnping/ "
            " )"
            )

    @property
    def _environment(self):
        return "%s:%s" % (self.ccnd.path, "${BIN}/ccnping")
       
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

