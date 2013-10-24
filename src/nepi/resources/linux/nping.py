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
class LinuxNPing(LinuxApplication):
    _rtype = "LinuxNPing"

    @classmethod
    def _register_attributes(cls):
        c = Attribute("c",
            "Sets nping -c option. "
            "Stop after a given number of rounds. ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        e = Attribute("e",
            "Sets nping -e option. "
            "Set the network interface to be used.",
            flags = Flags.ExecReadOnly)

        delay = Attribute("delay",
            "Sets nping --delay option. "
            "Delay between probes ",
            flags = Flags.ExecReadOnly)

        rate = Attribute("rate",
            "Sets nping --rate option. "
            "Send probes at a given rate ",
            flags = Flags.ExecReadOnly)

        ttl = Attribute("ttl",
            "Sets nping --ttl option. "
            "Time To Live. ",
            flags = Flags.ExecReadOnly)

        p = Attribute("p",
            "Sets nping -p option. "
            "Target ports. ",
            type = Types.Integer,
            flags = Flags.ExecReadOnly)

        tcp = Attribute("tcp",
            "Sets nping --tcp option. "
            "TCP mode. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        udp = Attribute("udp",
            "Sets nping --udp option. "
            "UDP mode. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        icmp = Attribute("icmp",
            "Sets nping --icmp option. "
            "ICMP mode. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        arp = Attribute("arp",
            "Sets nping --arp option. "
            "ARP mode. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        traceroute = Attribute("traceroute",
            "Sets nping --traceroute option. "
            "Traceroute mode. ",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        countinuous = Attribute("continuous",
            "Run nping in a while loop",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        print_timestamp = Attribute("printTimestamp",
            "Print timestamp before running nping",
            type = Types.Bool,
            default = False,
            flags = Flags.ExecReadOnly)

        target = Attribute("target",
            "nping target host (host that will be pinged)",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(c)
        cls._register_attribute(e)
        cls._register_attribute(delay)
        cls._register_attribute(rate)
        cls._register_attribute(ttl)
        cls._register_attribute(p)
        cls._register_attribute(tcp)
        cls._register_attribute(udp)
        cls._register_attribute(icmp)
        cls._register_attribute(arp)
        cls._register_attribute(traceroute)
        cls._register_attribute(countinuous)
        cls._register_attribute(print_timestamp)
        cls._register_attribute(target)

    def __init__(self, ec, guid):
        super(LinuxNPing, self).__init__(ec, guid)
        self._home = "nping-%s" % self.guid
        self._sudo_kill = True

    @failtrap
    def deploy(self):
        if not self.get("command"):
            self.set("command", self._start_command)

        if not self.get("install"):
            self.set("install", self._install)

        if not self.get("env"):
            self.set("env", "PATH=$PATH:/usr/sbin/")

        if not self.get("depends"):
            self.set("depends", "nmap")

        super(LinuxNPing, self).deploy()

    @property
    def _start_command(self):
        args = []
        if self.get("continuous") == True:
            args.append("while true; do ")
        if self.get("printTimestamp") == True:
            args.append("""echo "`date +'%Y%m%d%H%M%S'`";""")
        args.append("sudo -S nping ")
        if self.get("c"):
            args.append("-c %s" % self.get("c"))
        if self.get("e"):
            args.append("-e %s" % self.get("e"))
        if self.get("delay"):
            args.append("--delay %s" % self.get("delay"))
        if self.get("rate"):
            args.append("--rate %s" % self.get("rate"))
        if self.get("ttl"):
            args.append("--ttl %s" % self.get("ttl"))
        if self.get("p"):
            args.append("-p %s" % self.get("p"))
        if self.get("tcp") == True:
            args.append("--tcp")
        if self.get("udp") == True:
            args.append("--udp")
        if self.get("icmp") == True:
            args.append("--icmp")
        if self.get("arp") == True:
            args.append("--arp")
        if self.get("traceroute") == True:
            args.append("--traceroute")

        args.append(self.get("target"))

        if self.get("continuous") == True:
            args.append("; done ")

        command = " ".join(args)

        return command

    @property
    def _install(self):
        install  = "echo 'nothing to do'"
        if self.node.use_rpm:
            install = (
                " ( "
                "  ( "
                "   if [ `uname -m` == 'x86_64' ]; then "
                "     wget -O nping.rpm http://nmap.org/dist/nping-0.6.25-1.x86_64.rpm ;"
                "   else wget -O nping.rpm http://nmap.org/dist/nping-0.6.25-1.i386.rpm ;"
                "   fi "
                " )"
                " && sudo -S rpm -vhU nping.rpm ) ")
        elif self.node.use_deb:
            from nepi.resources.linux import debfuncs 
            install_alien = debfuncs.install_packages_command(self.node.os, "alien gcc")
            install = (
                " ( "
                "  ( "
                "   if [ `uname -m` == 'x86_64' ]; then "
                "     wget -O nping.rpm http://nmap.org/dist/nping-0.6.25-1.x86_64.rpm ;"
                "   else wget -O nping.rpm http://nmap.org/dist/nping-0.6.25-1.i386.rpm ;"
                "   fi "
                " )"
                " && %s && sudo alien -i nping.rpm ) " % install_alien)

        return ("( nping --version || %s )" % install)

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

