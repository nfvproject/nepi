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
        reschedule_delay, failtrap 
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow

import os

@clsinit_copy
class LinuxUdpTest(LinuxApplication):
    """ Uses the hpcbench udptest tool to gather UDP measurements.
    Measurements require two ends, a server and a client RM.

    http://hpcbench.sourceforge.net/
    """
    _rtype = "LinuxUdpTest"

    @classmethod
    def _register_attributes(cls):
        s = Attribute("s",
            "Runs in server mode. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        p = Attribute("p",
            "Port to listen to in server mode, or to connect to in client mode. "
            "Defaults to 5678. ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        a = Attribute("a",
            "Client option. Perform UDP Round Trip Time (latency) ",
            type = Types.Bool,
            flags = Flags.ExecReadOnly)

        A = Attribute("A",
            "Client option. "
            "Message size for UDP RTT test. "
            "UDP RTT (latency) test with specified message size.",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        b = Attribute("b",
            "Client option. "
            "Client UDP buffer size in bytes. Using system default "
            "value if not defined.",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        B = Attribute("B",
            "Client option. "
            "Server UDP buffer size in bytes. The same as cleint's by default.",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        c = Attribute("c",
            "Client option. "
            "CPU log option. Tracing system info during the test. "
            "Only available when output is defined. ",
            type = Types.Bool,
            flags = Flags.ExecReadOnly)

        d = Attribute("d",
            "Client option. "
            "Data size of each read/write in bytes. The same as packet size "
            "by default.",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        e = Attribute("e",
            "Client option. "
            "Exponential test (data size of each sending increasing from 1 "
            "byte to packet size). ",
            type = Types.Bool,
            flags = Flags.ExecReadOnly)

        g = Attribute("g",
            "Client option. "
            "UDP traffic generator (Keep sending data to a host). "
            "Work without server's support.",
            type = Types.Bool,
            flags = Flags.ExecReadOnly)

        target = Attribute("target",
            "Client option. "
            "Hostname or IP address of UDP server. Must be specified.",
            flags = Flags.ExecReadOnly)

        i = Attribute("i",
            "Client option. "
            "Bidirectional UDP throuhgput test. Default is unidirection "
            "stream test. ",
            type = Types.Bool,
            flags = Flags.ExecReadOnly)

        l = Attribute("l",
            "Client option. "
            "UDP datagram (packet) size in bytes ( < udp-buffer-szie ). "
            "1460 by default.",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        m = Attribute("m",
            "Client option. "
            "Total message size in bytes. 1048576 by default.",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        o = Attribute("o",
            "Client option. "
            "Output file name. ",
            flags = Flags.ExecReadOnly)

        P = Attribute("P",
            "Client option. "
            "Write the plot file for gnuplot. Only enable when the output "
            "is specified. ",
            type = Types.Bool,
            flags = Flags.ExecReadOnly)

        q = Attribute("q",
            "Client option. "
            "Define the TOS field of IP packets. "
            "Six values can be used for this setting:\n"
            " 1:(IPTOS)-Minimize delay\n"
            " 2:(IPTOS)-Maximize throughput\n"
            " 3:(DiffServ)-Class1 with low drop probability\n"
            " 4:(DiffServ)-class1 with high drop probability\n"
            " 5:(DiffServ)-Class4 with low drop probabiltiy\n"
            " 6:(DiffServ)-Class4 with high drop probabiltiy\n"
            "Write the plot file for gnuplot. Only enable when the output "
            "is specified. ",
            type = Types.Enumerate,
            allowed = ["1", "2", "3", "4", "5", "6"],
            flags = Flags.ExecReadOnly)

        r = Attribute("r",
            "Client option. "
            "Repetition of tests. 10 by default. ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        t = Attribute("t",
            "Client option. "
            "Test time constraint in seconds. 5 by default. ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        T = Attribute("T",
            "Client option. "
            "Throughput constraint for UDP generator or throughput "
            "test. Unlimited by default. ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        continuous = Attribute("continuous",
            "Run nping in a while loop",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        print_timestamp = Attribute("printTimestamp",
            "Print timestamp before running nping",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        cls._register_attribute(s)
        cls._register_attribute(p)
        cls._register_attribute(a)
        cls._register_attribute(A)
        cls._register_attribute(b)
        cls._register_attribute(B)
        cls._register_attribute(c)
        cls._register_attribute(d)
        cls._register_attribute(e)
        cls._register_attribute(g)
        cls._register_attribute(target)
        cls._register_attribute(g)
        cls._register_attribute(i)
        cls._register_attribute(l)
        cls._register_attribute(m)
        cls._register_attribute(o)
        cls._register_attribute(P)
        cls._register_attribute(q)
        cls._register_attribute(r)
        cls._register_attribute(t)
        cls._register_attribute(T)
        cls._register_attribute(continuous)
        cls._register_attribute(print_timestamp)

    def __init__(self, ec, guid):
        super(LinuxUdpTest, self).__init__(ec, guid)
        self._home = "udptest-%s" % self.guid

    @failtrap
    def deploy(self):
        if not self.get("command"):
            self.set("command", self._start_command)

        if not self.get("sources"):
            self.set("sources", self._sources)

        if not self.get("install"):
            self.set("install", self._install)

        if not self.get("build"):
            self.set("build", self._build)

        if not self.get("env"):
            self.set("env", self._environment)

        if not self.get("depends"):
            self.set("depends", self._depends)

        super(LinuxUdpTest, self).deploy()

    def upload_start_command(self):

        super(LinuxUdpTest, self).upload_start_command()

        if self.get("s") == True:
            # We want to make sure the server is running
            # before the client starts.
            # Run the command as a bash script in background,
            # in the host ( but wait until the command has
            # finished to continue )
            self._run_in_background()
    
    @failtrap
    def start(self):
        if self.get("s") == True:
            # Server is already running
            if self.state == ResourceState.READY:
                command = self.get("command")
                self.info("Starting command '%s'" % command)

                self.set_started()
            else:
                msg = " Failed to execute command '%s'" % command
                self.error(msg, out, err)
                raise RuntimeError, err
        else:
            super(LinuxUdpTest, self).start()
 
    @property
    def _start_command(self):
        args = []
        if self.get("continuous") == True:
            args.append("while true; do ")

        if self.get("printTimestamp") == True:
            args.append("""echo "`date +'%Y%m%d%H%M%S'`";""")

        if self.get("s") == True:
            args.append("udpserver")
        else:
            args.append("udptest")

        if self.get("p"):
            args.append("-p %d" % self.get("p"))
        if self.get("a") == True:
            args.append("-a")
        if self.get("A"):
            args.append("-A %d" % self.get("A"))
        if self.get("b"):
            args.append("-b %d" % self.get("b"))
        if self.get("B"):
            args.append("-B %d" % self.get("B"))
        if self.get("c") == True:
            args.append("-c")
        if self.get("d"):
            args.append("-d %d" % self.get("d"))
        if self.get("e") == True:
            args.append("-e")
        if self.get("g") == True:
            args.append("-g")
        if self.get("target"):
            args.append("-h %s" % self.get("target"))
        if self.get("i") == True:
            args.append("-i")
        if self.get("l"):
            args.append("-l %d" % self.get("l"))
        if self.get("m"):
            args.append("-m %d" % self.get("m"))
        if self.get("o"):
            args.append("-o %d" % self.get("o"))
        if self.get("P"):
            args.append("-P %d" % self.get("P"))
        if self.get("q"):
            args.append("-q %s" % self.get("q"))
        if self.get("r"):
            args.append("-r %d" % self.get("r"))
        if self.get("t"):
            args.append("-t %d" % self.get("t"))
        if self.get("T"):
            args.append("-T %d" % self.get("T"))

        if self.get("continuous") == True:
            args.append("; done ")

        command = " ".join(args)

        return command

    @property
    def _sources(self):
        return "http://hpcbench.sourceforge.net/udp.tar.gz"

    @property
    def _depends(self):
        return "gcc make"

    @property
    def _build(self):
        sources = self.get("sources").split(" ")[0]
        sources = os.path.basename(sources)

        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${BIN}/udptest && "
                " echo 'binaries found, nothing to do' "
            " ) || ( "
            # If not, untar and build
                " ( "
                    " mkdir -p ${SRC}/udptest && "
                    " tar xf ${SRC}/%(sources)s --strip-components=1 -C ${SRC}/udptest "
                 " ) && "
                    "cd ${SRC}/udptest && "
                    # Just execute and silence warnings...
                    " ( make ) "
             " )") % ({ 'sources': sources,
                 })

    @property
    def _install(self):
        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${BIN}/udptest && "
                " echo 'binaries found, nothing to do' "
            " ) || ( "
            # If not, install
                "  mv ${SRC}/udptest ${BIN} "
            " )")

    @property
    def _environment(self):
        return "PATH=$PATH:${BIN}/udptest"

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

