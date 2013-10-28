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
from nepi.execution.resource import clsinit_copy, failtrap 
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow

import os

@clsinit_copy
class LinuxTcpdump(LinuxApplication):
    _rtype = "LinuxTcpdump"

    @classmethod
    def _register_attributes(cls):
        A = Attribute("A",
            "Sets tcpdump -A option. "
            "Prints each packet (minus its link level header) in ASCII.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        b = Attribute("b",
            "Sets tcpdump -b option. "
            "Prints the AS number in BGP packets in ASDOT notation. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        B = Attribute("B",
            "Sets tcpdump -B option. "
            "Sets the operaing system capture buffer size in untils of "
            "KiB (1024 bytes).",
            flags = Flags.ExecReadOnly)

        c = Attribute("c",
            "Sets tcpdump -c option. "
            "Exists after receiving count packets.",
            flags = Flags.ExecReadOnly)

        C = Attribute("C",
            "Sets tcpdump -C option. "
            "Before writing a raw packet to a savefile, check whether the "
            "file is currently larger than file_size and, if so, close the "
            "current  savefile  and  open a new one. "
            "Savefiles after the first savefile will have the name specified "
            "with the -w with a number after it, starting at 1 and continuing "
            "upward. ",
            flags = Flags.ExecReadOnly)

        d = Attribute("d",
            "Sets tcpdump -d option. "
            "Dump the compiled packet-matching code in a human readable form "
            "to standard output and stop.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        dd = Attribute("dd",
            "Sets tcpdump -dd option. "
            "Dump packet-matching code as a C program fragment. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        ddd = Attribute("ddd",
            "Sets tcpdump -ddd option. "
            "Dump packet-matching code as decimal numbers "
            "(preceded with a count).",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        D = Attribute("D",
            "Sets tcpdump -D option. "
            "Print the list of the network interfaces available on the system "
            "and on which tcpdump can capture packets. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        e = Attribute("e",
            "Sets tcpdump -e option. "
            "Print the link-level header on each dump line.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        F =  Attribute("F",
            "Sets tcpdump -F option. "
            "Use file as input for the filter expression.",
            flags = Flags.ExecReadOnly)

        G =  Attribute("G",
            "Sets tcpdump -G option. "
            "If specified, rotates the dump file specified with the -w "
            "option every rotate_seconds seconds. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        i =  Attribute("i",
            "Sets tcpdump -i option. "
            "Listen on interface.  If unspecified, tcpdump searches the "
            "system interface list for the lowest  numbered, configured "
            "up interface (excluding loopback). ",
            flags = Flags.ExecReadOnly)

        I =  Attribute("I",
            "Sets tcpdump -I option. "
            "Put the interface in 'monitor mode'; this is supported only "
            "on IEEE 802.11 Wi-Fi interfaces, and supported only on some "
            "operating systems. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        j = Attribute("j",
            "Sets tcpdump -j option. "
            "Sets the time stamp type for the capture to tstamp_type. "
            "The names to use for the time stamp types are given in "
            "pcap-tstamp-type(7); not all the types listed there will "
            "necessarily be valid for any given interface.",
            flags = Flags.ExecReadOnly)

        K = Attribute("K",
            "Sets tcpdump -K option. "
            "Don't attempt to verify IP, TCP, or UDP checksums. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        l = Attribute("l",
            "Sets tcpdump -l option. "
            "Make stdout line buffered. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        U = Attribute("U",
            "Sets tcpdump -U option. "
            "Similar to -l in its behavior, but it will cause output to be "
            "``packet-buffered'', so that the output is written to stdout "
            "at the end of each packet. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        n = Attribute("n",
            "Sets tcpdump -n option. "
            "Don't convert addresses (i.e., host addresses, port numbers, "
            "etc.) to names.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        N = Attribute("N",
            "Sets tcpdump -N option. "
            "Don't  print domain name qualification of host names. "
            "E.g., if you give this flag then tcpdump will print ``nic'' " 
            "instead of ``nic.ddn.mil''.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        S = Attribute("S",
            "Sets tcpdump -S option. "
            "Print absolute, rather than relative, TCP sequence numbers.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        s = Attribute("s",
            "Sets tcpdump -s option. "
            "Snarf  snaplen bytes of data from each packet rather than "
            "the default of 65535 bytes. ",
            flags = Flags.ExecReadOnly)

        T = Attribute("T",
            "Sets tcpdump -T option. "
             "Force packets selected by 'expression' to be interpreted the "
             "specified type.  Currently known types are aodv  (Ad-hoc "
             "On-demand  Distance Vector protocol), cnfp (Cisco NetFlow "
             "protocol), rpc (Remote Procedure Call), rtp (Real-Time "
             "Applications protocol), rtcp (Real-Time Applications control "
             "protocol), snmp (Simple Network Management Protocol), tftp "
             "(Trivial  File Transfer Protocol), vat (Visual Audio Tool), "
             "and wb (distributed White Board).",
            flags = Flags.ExecReadOnly)

        t = Attribute("t",
            "Sets tcpdump -t option. "
            "Don't print a timestamp on each dump line.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        tt = Attribute("tt",
            "Sets tcpdump -tt option. "
            "Print an unformatted timestamp on each dump line. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        ttt = Attribute("ttt",
            "Sets tcpdump -ttt option. "
            "Print a delta (micro-second resolution) between current "
            "and previous line on each dump line.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        tttt = Attribute("tttt",
            "Sets tcpdump -tttt option. "
            "Print a timestamp in default format proceeded by date on "
            "each dump line. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        ttttt = Attribute("ttttt",
            "Sets tcpdump -ttttt option. "
            "Print a delta (micro-second resolution) between current and "
            "first line on each dump line.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        v = Attribute("v",
            "Sets tcpdump -v option. "
            "When  parsing  and printing, produce (slightly more) "
            "verbose output. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        vv = Attribute("vv",
            "Sets tcpdump -vv option. "
            "Even  more  verbose  output. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        vvv = Attribute("vvv",
            "Sets tcpdump -vv option. "
            "Even  more  verbose  output. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        w = Attribute("w",
            "Sets tcpdump -w option. "
            "Write  the  raw  packets to file rather than parsing "
            "and printing them out.",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        expression = Attribute("expression",
            "selects  which packets will be dumped.",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(A)
        cls._register_attribute(b)
        cls._register_attribute(B)
        cls._register_attribute(c)
        cls._register_attribute(C)
        cls._register_attribute(d)
        cls._register_attribute(dd)
        cls._register_attribute(ddd)
        cls._register_attribute(D)
        cls._register_attribute(e)
        cls._register_attribute(F)
        cls._register_attribute(G)
        cls._register_attribute(i)
        cls._register_attribute(I)
        cls._register_attribute(j)
        cls._register_attribute(K)
        cls._register_attribute(l)
        cls._register_attribute(U)
        cls._register_attribute(n)
        cls._register_attribute(N)
        cls._register_attribute(S)
        cls._register_attribute(s)
        cls._register_attribute(T)
        cls._register_attribute(t)
        cls._register_attribute(tt)
        cls._register_attribute(ttt)
        cls._register_attribute(tttt)
        cls._register_attribute(ttttt)
        cls._register_attribute(v)
        cls._register_attribute(vv)
        cls._register_attribute(vvv)
        cls._register_attribute(w)
        cls._register_attribute(expression)

    def __init__(self, ec, guid):
        super(LinuxTcpdump, self).__init__(ec, guid)
        self._home = "tcpdump-%s" % self.guid
        self._sudo_kill = True

    @failtrap
    def deploy(self):
        if not self.get("command"):
            self.set("command", self._start_command)

        if not self.get("env"):
            self.set("env", "PATH=$PATH:/usr/sbin/")

        if not self.get("depends"):
            self.set("depends", "tcpdump")

        super(LinuxTcpdump, self).deploy()

    @property
    def _start_command(self):
        args = []
        args.append("sudo -S tcpdump")
        if self.get("A") == True:
            args.append("-A")
        if self.get("b") == True:
            args.append("-b")
        if self.get("B"):
            args.append("-B %s" % self.get("B"))
        if self.get("c"):
            args.append("-c %s" % self.get("c"))
        if self.get("C"):
            args.append("-C %s" % self.get("C"))
        if self.get("d") == True:
            args.append("-d")
        if self.get("dd") == True:
            args.append("-dd")
        if self.get("ddd") == True:
            args.append("-ddd")
        if self.get("D") == True:
            args.append("-D")
        if self.get("e") == True:
            args.append("-e")
        if self.get("F"):
            args.append("-F %s" % self.get("F"))
        if self.get("G") == True:
            args.append("-G")
        if self.get("i"):
            args.append("-i %s" % self.get("i"))
        if self.get("I") == True:
            args.append("-I")
        if self.get("j"):
            args.append("-j %s" % self.get("j"))
        if self.get("K") == True:
            args.append("-K")
        if self.get("l") == True:
            args.append("-l")
        if self.get("U") == True:
            args.append("-U")
        if self.get("n") == True:
            args.append("-n")
        if self.get("N") == True:
            args.append("-N")
        if self.get("S") == True:
            args.append("-S")
        if self.get("s"):
            args.append("-s %s" % self.get("s"))
        if self.get("T"):
            args.append("-T %s" % self.get("T"))
        if self.get("t") == True:
            args.append("-t")
        if self.get("tt") == True:
            args.append("-tt")
        if self.get("ttt") == True:
            args.append("-ttt")
        if self.get("tttt") == True:
            args.append("-tttt")
        if self.get("ttttt") == True:
            args.append("-ttttt")
        if self.get("v") == True:
            args.append("-v")
        if self.get("vv") == True:
            args.append("-vv")
        if self.get("vvv") == True:
            args.append("-vvv")
        if self.get("w"):
            args.append("-w %s" % self.get("w"))
        if self.get("expression"):
            args.append(self.get("expression"))

        command = " ".join(args)

        return command

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

