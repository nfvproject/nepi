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
from nepi.resources.linux.ns3.ccn.ns3ccndceapplication import LinuxNS3CCNDceApplication

import os

@clsinit_copy
class LinuxNS3DceCCND(LinuxNS3CCNDceApplication):
    _rtype = "ns3::LinuxDceCCND"

    @classmethod
    def _register_attributes(cls):
        debug = Attribute("debug", "Sets the CCND_DEBUG environmental variable. "
            " Allowed values are : \n"
            "  0 - no messages \n"
            "  1 - basic messages (any non-zero value gets these) \n"
            "  2 - interest messages \n"
            "  4 - content messages \n"
            "  8 - matching details \n"
            "  16 - interest details \n"
            "  32 - gory interest details \n"
            "  64 - log occasional human-readable timestamps \n"
            "  128 - face registration debugging \n"
            "  -1 - max logging \n"
            "  Or apply bitwise OR to these values to get combinations of them",
            type = Types.Integer,
            flags = Flags.Design)

        port = Attribute("port", "Sets the CCN_LOCAL_PORT environmental variable. "
            "Defaults to 9695 ", 
            flags = Flags.Design)
 
        sockname = Attribute("sockname",
            "Sets the CCN_LOCAL_SCOKNAME environmental variable. "
            "Defaults to /tmp/.ccnd.sock", 
            flags = Flags.Design)

        capacity = Attribute("capacity",
            "Sets the CCND_CAP environmental variable. "
            "Capacity limit in terms of ContentObjects",
            flags = Flags.Design)

        mtu = Attribute("mtu", "Sets the CCND_MTU environmental variable. ",
            flags = Flags.Design)
  
        data_pause = Attribute("dataPauseMicrosec",
            "Sets the CCND_DATA_PAUSE_MICROSEC environmental variable. ",
            flags = Flags.Design)

        default_stale = Attribute("defaultTimeToStale",
             "Sets the CCND_DEFAULT_TIME_TO_STALE environmental variable. ",
            flags = Flags.Design)

        max_stale = Attribute("maxTimeToStale",
            "Sets the CCND_MAX_TIME_TO_STALE environmental variable. ",
            flags = Flags.Design)

        max_rte = Attribute("maxRteMicrosec",
            "Sets the CCND_MAX_RTE_MICROSEC environmental variable. ",
            flags = Flags.Design)

        keystore = Attribute("keyStoreDirectory",
            "Sets the CCND_KEYSTORE_DIRECTORY environmental variable. ",
            flags = Flags.Design)

        listen_on = Attribute("listenOn",
            "Sets the CCND_LISTEN_ON environmental variable. ",
            flags = Flags.Design)

        autoreg = Attribute("autoreg",
            "Sets the CCND_AUTOREG environmental variable. ",
            flags = Flags.Design)

        prefix = Attribute("prefix",
            "Sets the CCND_PREFIX environmental variable. ",
            flags = Flags.Design)

        cls._register_attribute(debug)
        cls._register_attribute(port)
        cls._register_attribute(sockname)
        cls._register_attribute(capacity)
        cls._register_attribute(mtu)
        cls._register_attribute(data_pause)
        cls._register_attribute(default_stale)
        cls._register_attribute(max_stale)
        cls._register_attribute(max_rte)
        cls._register_attribute(keystore)
        cls._register_attribute(listen_on)
        cls._register_attribute(autoreg)
        cls._register_attribute(prefix)

    @property
    def version(self):
        return self._version

    def _instantiate_object(self):
        if not self.get("depends"):
            self.set("depends", self._dependencies)

        if not self.get("sources"):
            self.set("sources", self._sources)

        sources = self.get("sources")
        source = sources.split(" ")[0]
        basename = os.path.basename(source)
        self._version = ( basename.strip().replace(".tar.gz", "")
                .replace(".tar","")
                .replace(".gz","")
                .replace(".zip","") )

        if not self.get("build"):
            self.set("build", self._build)

        if not self.get("binary"):
            self.set("binary", "ccnd")

        if not self.get("environment"):
            self.set("environment", self._environment)
        
        super(LinuxNS3DceCCND, self)._instantiate_object()

    @property
    def _dependencies(self):
        if self.simulation.node.use_rpm:
            return ( " autoconf openssl-devel  expat-devel libpcap-devel "
                " ecryptfs-utils-devel libxml2-devel automake gawk " 
                " gcc gcc-c++ git pcre-devel make ")
        elif self.simulation.node.use_deb:
            return ( " autoconf libssl-dev libexpat-dev libpcap-dev "
                " libecryptfs0 libxml2-utils automake gawk gcc g++ "
                " git-core pkg-config libpcre3-dev make ")
        return ""


    @property
    def _sources(self):
        return "http://www.ccnx.org/releases/ccnx-0.8.1.tar.gz"

    @property
    def _build(self):
        sources = self.get("sources")
        source = sources.split(" ")[0]
        tar = os.path.basename(source)

        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${SRC}/%(tar)s && "
                " echo 'binaries found, nothing to do' "
            " ) || "
            # If not, untar and build
            " ( "
                " tar zxf ${SRC}/%(tar)s  && "
                " cd %(version)s && "
                " INSTALL_BASE=${BIN_DCE}/.. ./configure && "
                " make MORE_LDLIBS=-pie && "
                " make install && "
                " cp ${BIN_DCE}/../bin/ccn* ${BIN_DCE} && "
                " cd -"
             " )") % ({ 'tar': tar,
                        'version': self.version
                 })

    @property
    def _environment(self):
        envs = dict({
            "debug": "CCND_DEBUG",
            "port": "CCN_LOCAL_PORT",
            "sockname" : "CCN_LOCAL_SOCKNAME",
            "capacity" : "CCND_CAP",
            "mtu" : "CCND_MTU",
            "dataPauseMicrosec" : "CCND_DATA_PAUSE_MICROSEC",
            "defaultTimeToStale" : "CCND_DEFAULT_TIME_TO_STALE",
            "maxTimeToStale" : "CCND_MAX_TIME_TO_STALE",
            "maxRteMicrosec" : "CCND_MAX_RTE_MICROSEC",
            "keyStoreDirectory" : "CCND_KEYSTORE_DIRECTORY",
            "listenOn" : "CCND_LISTEN_ON",
            "autoreg" : "CCND_AUTOREG",
            "prefix" : "CCND_PREFIX",
            })

        env = ";".join(map(lambda k: "%s=%s" % (envs.get(k), str(self.get(k))), 
            [k for k in envs.keys() if self.get(k)]))

        return env

