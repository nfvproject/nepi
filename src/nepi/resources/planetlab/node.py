"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState
from nepi.resources.linux.node import LinuxNode

from nepi.resources.planetlab.plcapi import PLCAPIFactory 

reschedule_delay = "0.5s"

@clsinit_copy
class PlanetlabNode(LinuxNode):
    _rtype = "PlanetLabNode"

    @classmethod
    def _register_attributes(cls):
        cls._remove_attribute("username")

        ip = Attribute("ip", "PlanetLab host public IP address",
                flags = Flags.ReadOnly)

        slicename = Attribute("slice", "PlanetLab slice name",
                flags = Flags.Credential)

        pl_url = Attribute("plcApiUrl", "URL of PlanetLab PLCAPI host (e.g. www.planet-lab.eu or www.planet-lab.org) ",
                default = "www.planet-lab.eu",
                flags = Flags.Credential)

        pl_ptn = Attribute("plcApiPattern", "PLC API service regexp pattern (e.g. https://%(hostname)s:443/PLCAPI/ ) ",
                default = "https://%(hostname)s:443/PLCAPI/",
                flags = Flags.ExecReadOnly)

        city = Attribute("city",
                "Constrain location (city) during resource discovery. May use wildcards.",
                flags = Flags.Filter)

        country = Attribute("country",
                "Constrain location (country) during resource discovery. May use wildcards.",
                flags = Flags.Filter)

        region = Attribute("region",
                "Constrain location (region) during resource discovery. May use wildcards.",
                flags = Flags.Filter)

        architecture = Attribute("architecture",
                "Constrain architecture during resource discovery.",
                type = Types.Enumerate,
                allowed = ["x86_64",
                            "i386"],
                flags = Flags.Filter)

        operating_system = Attribute("operatingSystem",
                "Constrain operating system during resource discovery.",
                type = Types.Enumerate,
                allowed =  ["f8",
                            "f12",
                            "f14",
                            "centos",
                            "other"],
                flags = Flags.Filter)

        site = Attribute("site",
                "Constrain the PlanetLab site this node should reside on.",
                type = Types.Enumerate,
                allowed = ["PLE",
                            "PLC",
                            "PLJ"],
                flags = Flags.Filter)

        min_reliability = Attribute("minReliability",
                "Constrain reliability while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (1, 100),
                flags = Flags.Filter)

        max_reliability = Attribute("maxReliability",
                "Constrain reliability while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (1, 100),
                flags = Flags.Filter)

        min_bandwidth = Attribute("minBandwidth",
                "Constrain available bandwidth while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        max_bandwidth = Attribute("maxBandwidth",
                "Constrain available bandwidth while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        min_load = Attribute("minLoad",
                "Constrain node load average while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        max_load = Attribute("maxLoad",
                "Constrain node load average while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        min_cpu = Attribute("minCpu",
                "Constrain available cpu time while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (0, 100),
                flags = Flags.Filter)

        max_cpu = Attribute("maxCpu",
                "Constrain available cpu time while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (0, 100),
                flags = Flags.Filter)

        timeframe = Attribute("timeframe",
                "Past time period in which to check information about the node. Values are year,month, week, latest",
                default = "week",
                type = Types.Enumerate,
                allowed = ["latest",
                            "week",
                            "month",
                            "year"],
                 flags = Flags.Filter)

        cls._register_attribute(ip)
        cls._register_attribute(slicename)
        cls._register_attribute(pl_url)
        cls._register_attribute(pl_ptn)
        cls._register_attribute(city)
        cls._register_attribute(country)
        cls._register_attribute(region)
        cls._register_attribute(architecture)
        cls._register_attribute(operating_system)
        cls._register_attribute(min_reliability)
        cls._register_attribute(max_reliability)
        cls._register_attribute(min_bandwidth)
        cls._register_attribute(max_bandwidth)
        cls._register_attribute(min_load)
        cls._register_attribute(max_load)
        cls._register_attribute(min_cpu)
        cls._register_attribute(max_cpu)
        cls._register_attribute(timeframe)

    def __init__(self, ec, guid):
        super(PLanetLabNode, self).__init__(ec, guid)

        self._plapi = None
    
    @property
    def plapi(self):
        if not self._plapi:
            slicename = self.get("slice")
            pl_pass = self.get("password")
            pl_url = self.get("plcApiUrl")
            pl_ptn = self.get("plcApiPattern")

            self._plapi =  PLCAPIFactory.get_api(slicename, pl_pass, pl_url,
                    pl_ptn)
            
        return self._plapi

    @property
    def os(self):
        if self._os:
            return self._os

        if (not self.get("hostname") or not self.get("username")):
            msg = "Can't resolve OS, insufficient data "
            self.error(msg)
            raise RuntimeError, msg

        (out, err), proc = self.execute("cat /etc/issue", with_lock = True)

        if err and proc.poll():
            msg = "Error detecting OS "
            self.error(msg, out, err)
            raise RuntimeError, "%s - %s - %s" %( msg, out, err )

        if out.find("Fedora release 12") == 0:
            self._os = "f12"
        elif out.find("Fedora release 14") == 0:
            self._os = "f14"
        else:
            msg = "Unsupported OS"
            self.error(msg, out)
            raise RuntimeError, "%s - %s " %( msg, out )

        return self._os

    @property
    def localhost(self):
        return False

    def discover(self):
        # Get the list of nodes that match the filters


        # find one that 
        if not self.is_alive():
            self._state = ResourceState.FAILED
            msg = "Deploy failed. Unresponsive node %s" % self.get("hostname")
            self.error(msg)
            raise RuntimeError, msg

        if self.get("cleanProcesses"):
            self.clean_processes()

        if self.get("cleanHome"):
            self.clean_home()
       
        self.mkdir(self.node_home)

        super(PlanetlabNode, self).discover()

    def provision(self):
        if not self.is_alive():
            self._state = ResourceState.FAILED
            msg = "Deploy failed. Unresponsive node %s" % self.get("hostname")
            self.error(msg)
            raise RuntimeError, msg

        if self.get("cleanProcesses"):
            self.clean_processes()

        if self.get("cleanHome"):
            self.clean_home()
       
        self.mkdir(self.node_home)

        super(PlanetlabNode, self).provision()

    def deploy(self):
        if self.state == ResourceState.NEW:
            try:
               self.discover()
               if self.state == ResourceState.DISCOVERED:
                   self.provision()
            except:
                self._state = ResourceState.FAILED
                raise

        if self.state != ResourceState.PROVISIONED:
           self.ec.schedule(reschedule_delay, self.deploy)

        super(PlanetlabNode, self).deploy()

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

    def clean_processes(self, killer = False):
        self.info("Cleaning up processes")
    
        # Hardcore kill
        cmd = ("sudo -S killall python tcpdump || /bin/true ; " +
            "sudo -S killall python tcpdump || /bin/true ; " +
            "sudo -S kill $(ps -N -T -o pid --no-heading | grep -v $PPID | sort) || /bin/true ; " +
            "sudo -S killall -u root || /bin/true ; " +
            "sudo -S killall -u root || /bin/true ; ")

        out = err = ""
        (out, err), proc = self.execute(cmd, retry = 1, with_lock = True) 
            
    def is_alive(self):
        if self.localhost:
            return True

        out = err = ""
        try:
            # TODO: FIX NOT ALIVE!!!!
            (out, err), proc = self.execute("echo 'ALIVE' || (echo 'NOTALIVE') >&2", retry = 5, 
                    with_lock = True)
        except:
            import traceback
            trace = traceback.format_exc()
            msg = "Unresponsive host  %s " % err
            self.error(msg, out, trace)
            return False

        if out.strip().startswith('ALIVE'):
            return True
        else:
            msg = "Unresponsive host "
            self.error(msg, out, err)
            return False

    def blacklist(self):
        # TODO!!!!
        self.warn(" Blacklisting malfunctioning node ")
        #import util
        #util.appendBlacklist(self.hostname)

