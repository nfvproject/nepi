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
from nepi.resources.linux.ns3.ns3dceapplication import LinuxNS3DceApplication

@clsinit_copy
class LinuxDcePing(LinuxNS3DceApplication):
    _rtype = "ns3::LinuxDcePing"

    @classmethod
    def _register_attributes(cls):
        count = Attribute("count",
            "Sets ping -c option. Determines the number of ECHO_REQUEST "
            "packates to send before stopping.",
            type = Types.Integer,
            flags = Flags.Design)

        mark = Attribute("mark",
            "Sets ping -m option. Uses 'mark' to tag outgoing packets. ",
            flags = Flags.Design)

        interval = Attribute("interval",
            "Sets ping -i option. Leaves interval seconds between "
            "successive ECHO_REUQEST packets. ",
            flags = Flags.Design)

        address = Attribute("address",
            "Sets ping -I option. Sets ECHO_REQUEST packets souce address "
            "to the specified interface address ",
            flags = Flags.Design)

        preload = Attribute("preload",
            "Sets ping -l option. Sends preload amount of packets "
            "without waiting for a reply ",
            flags = Flags.Design)

        numeric = Attribute("numeric",
            "Sets ping -n option. Disables resolution of host addresses into "
            "symbolic names. ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        pattern = Attribute("pattern",
            "Sets ping -p option. Species a up to 16 ''pad'' bytes to fill "
            "out sent packets. ",
            flags = Flags.Design)

        printtmp = Attribute("printTimestamp",
            "Sets ping -D option. Prints timestamp befor each line as: "
            "unix time + microseconds as in gettimeofday ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        tos = Attribute("tos",
            "Sets ping -Q option. Sets Quality of Service related bits in ICMP "
            "datagrams. tos can be either a decimal or hexadecime number ",
            flags = Flags.Design)

        quiet = Attribute("quiet",
            "Sets ping -q option. Disables ping standard output ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        rec_route = Attribute("recordRoute",
            "Sets ping -R option. Includes the RECORD_ROUTE option in the "
            "ECHO REQUEST packet and displays route buffer on the Disables "
            "ping standard output.",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        route_bypass = Attribute("routeBypass",
            "Sets ping -r option. Bypasses normal routing tables and sends "
            "ECHO REQUEST packets directly yo a host on an attached interface. ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        packetsize = Attribute("packetSize",
            "Sets ping -s option. Specifies the number of data bytes to be "
            "sent. Defaults to 56. ",
            flags = Flags.Design)

        sendbuff = Attribute("sendBuff",
            "Sets ping -S option. Specifies the number of packets to buffer. "
            "Defaults to one. ",
            flags = Flags.Design)

        ttl = Attribute("ttl",
            "Sets ping -t option. Specifies the IP Time to Live for the "
            "packets. ",
            flags = Flags.Design)

        timestamp = Attribute("timestamp",
            "Sets ping -T option. Sets special IP timestamp options. ",
            flags = Flags.Design)

        hint = Attribute("hint",
            "Sets ping -M option. Selects Path MTU Discovery strategy. ",
            flags = Flags.Design)

        full_latency = Attribute("fullLatency",
            "Sets ping -U option. Calculates round trip time taking into "
            "account the full user-to-user latency instead of only the "
            "network round trip time. ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        verbose = Attribute("verbose",
            "Sets ping -v option. Verbose output. ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        flood = Attribute("flood",
            "Sets ping -f option. Flood ping. ",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        deadline = Attribute("deadline",
            "Sets ping -w option. Specify a timeout, in seconds, before ping "
            "exits regardless of how many packets have been sent or received.",
            flags = Flags.Design)

        timeout = Attribute("timeout",
            "Sets ping -W option. Time to wait for a respone in seconds .",
            flags = Flags.Design)

        target = Attribute("target",
            "The host to ping .",
            flags = Flags.Design)

        cls._register_attribute(count)
        cls._register_attribute(mark)
        cls._register_attribute(interval)
        cls._register_attribute(address)
        cls._register_attribute(preload)
        cls._register_attribute(numeric)
        cls._register_attribute(pattern)
        cls._register_attribute(printtmp)
        cls._register_attribute(tos)
        cls._register_attribute(quiet)
        cls._register_attribute(rec_route)
        cls._register_attribute(route_bypass)
        cls._register_attribute(packetsize)
        cls._register_attribute(sendbuff)
        cls._register_attribute(ttl)
        cls._register_attribute(timestamp)
        cls._register_attribute(hint)
        cls._register_attribute(full_latency)
        cls._register_attribute(verbose)
        cls._register_attribute(flood)
        cls._register_attribute(deadline)
        cls._register_attribute(timeout)
        cls._register_attribute(target)

    def _instantiate_object(self):
        self.set("sources", self._sources)
        self.set("build", self._build)
        self.set("binary", "ping")
        self.set("arguments", self._arguments)
        
        super(LinuxDcePing, self)._instantiate_object()

    @property
    def _sources(self):
        return "http://www.skbuff.net/iputils/iputils-s20101006.tar.bz2"

    @property
    def _build(self):
        return  (" ( "
                " test -f ${BIN_DCE}/ping && "
                " echo 'binaries found, nothing to do' "
                " ) || ( "
                "tar xvjf ${SRC}/iputils-s20101006.tar.bz2 && "
                "cd iputils-s20101006/ && "
                "sed -i 's/CFLAGS=/CFLAGS+=/g' Makefile && "
                "make CFLAGS=-fPIC LDFLAGS='-pie -rdynamic' ping && "
                "cp ping ${BIN_DCE} && cd - "
                " )"   
                )

    @property
    def _arguments(self):
        args = []

        if self.get("count"):
            args.append("-c %s" % self.get("count"))
        if self.get("mark"):
            args.append("-m %s" % self.get("mark"))
        if self.get("interval"):
            args.append("-i %s" % self.get("interval"))
        if self.get("address"):
            args.append("-I %s" % self.get("address"))
        if self.get("preload"):
            args.append("-l %s" % self.get("preload"))
        if self.get("numeric") == True:
            args.append("-n")
        if self.get("pattern"):
            args.append("-p %s" % self.get("pattern"))
        if self.get("tos"):
            args.append("-Q %s" % self.get("tos"))
        if self.get("quiet"):
            args.append("-q %s" % self.get("quiet"))
        if self.get("recordRoute") == True:
            args.append("-R")
        if self.get("routeBypass") == True:
            args.append("-r")
        if self.get("packetSize"):
            args.append("-s %s" % self.get("packetSize"))
        if self.get("sendBuff"):
            args.append("-S %s" % self.get("sendBuff"))
        if self.get("ttl"):
            args.append("-t %s" % self.get("ttl"))
        if self.get("timestamp"):
            args.append("-T %s" % self.get("timestamp"))
        if self.get("hint"):
            args.append("-M %s" % self.get("hint"))
        if self.get("fullLatency") == True:
            args.append("-U")
        if self.get("verbose") == True:
            args.append("-v")
        if self.get("flood") == True:
            args.append("-f")
        if self.get("deadline"):
            args.append("-w %s" % self.get("deadline"))
        if self.get("timeout"):
            args.append("-W %s" % self.get("timeout"))
        args.append(self.get("target"))

        return ";".join(args) 

