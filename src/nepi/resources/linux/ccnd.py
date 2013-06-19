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
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.node import OSType

from nepi.util.sshfuncs import ProcStatus
from nepi.util.timefuncs import strfnow, strfdiff
import os

@clsinit_copy
class LinuxCCND(LinuxApplication):
    _rtype = "LinuxCCND"

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
            flags = Flags.ExecReadOnly)

        port = Attribute("port", "Sets the CCN_LOCAL_PORT environmental variable. "
            "Defaults to 9695 ", 
            flags = Flags.ExecReadOnly)
 
        sockname = Attribute("sockname",
            "Sets the CCN_LOCAL_SCOKNAME environmental variable. "
            "Defaults to /tmp/.ccnd.sock", 
            flags = Flags.ExecReadOnly)

        capacity = Attribute("capacity",
            "Sets the CCND_CAP environmental variable. "
            "Capacity limit in terms of ContentObjects",
            flags = Flags.ExecReadOnly)

        mtu = Attribute("mtu", "Sets the CCND_MTU environmental variable. ",
            flags = Flags.ExecReadOnly)
  
        data_pause = Attribute("dataPauseMicrosec",
            "Sets the CCND_DATA_PAUSE_MICROSEC environmental variable. ",
            flags = Flags.ExecReadOnly)

        default_stale = Attribute("defaultTimeToStale",
             "Sets the CCND_DEFAULT_TIME_TO_STALE environmental variable. ",
            flags = Flags.ExecReadOnly)

        max_stale = Attribute("maxTimeToStale",
            "Sets the CCND_MAX_TIME_TO_STALE environmental variable. ",
            flags = Flags.ExecReadOnly)

        max_rte = Attribute("maxRteMicrosec",
            "Sets the CCND_MAX_RTE_MICROSEC environmental variable. ",
            flags = Flags.ExecReadOnly)

        keystore = Attribute("keyStoreDirectory",
            "Sets the CCND_KEYSTORE_DIRECTORY environmental variable. ",
            flags = Flags.ExecReadOnly)

        listen_on = Attribute("listenOn",
            "Sets the CCND_LISTEN_ON environmental variable. ",
            flags = Flags.ExecReadOnly)

        autoreg = Attribute("autoreg",
            "Sets the CCND_AUTOREG environmental variable. ",
            flags = Flags.ExecReadOnly)

        prefix = Attribute("prefix",
            "Sets the CCND_PREFIX environmental variable. ",
            flags = Flags.ExecReadOnly)

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

    @classmethod
    def _register_traces(cls):
        log = Trace("log", "CCND log output")
        status = Trace("status", "ccndstatus output")

        cls._register_trace(log)
        cls._register_trace(status)

    def __init__(self, ec, guid):
        super(LinuxCCND, self).__init__(ec, guid)

    def deploy(self):
        if not self.get("command"):
            self.set("command", self._default_command)
        
        if not self.get("depends"):
            self.set("depends", self._default_dependencies)

        if not self.get("sources"):
            self.set("sources", self._default_sources)

        if not self.get("build"):
            self.set("build", self._default_build)

        if not self.get("install"):
            self.set("install", self._default_install)

        if not self.get("env"):
            self.set("env", self._default_environment)

        super(LinuxCCND, self).deploy()

    def stop(self):
        command = self.get('command') or ''
        state = self.state
        
        if state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = "ccndstop"
            env = self.get("env") 

            # replace application specific paths in the command
            command = self.replace_paths(command)
            env = env and self.replace_paths(env)

            # Upload the command to a file, and execute asynchronously
            self.node.run_and_wait(command, self.app_home,
                        shfile = "ccndstop.sh",
                        env = env,
                        pidfile = "ccndstop_pidfile", 
                        ecodefile = "ccndstop_exitcode", 
                        stdout = "ccndstop_stdout", 
                        stderr = "ccndstop_stderr")


            super(LinuxCCND, self).stop()

    @property
    def state(self):
        if self._state == ResourceState.STARTED:
            # we executed the ccndstart command. This should have started
            # a remote ccnd daemon. The way we can query wheather ccnd is
            # still running is by executing the ccndstatus command.
            state_check_delay = 0.5
            if strfdiff(strfnow(), self._last_state_check) > state_check_delay:
                env = self.get('env') or ""
                environ = self.node.format_environment(env, inline = True)
                command = environ + "; ccndstatus"
                command = self.replace_paths(command)
            
                (out, err), proc = self.node.execute(command)

                retcode = proc.poll()

                if retcode == 1 and err.find("No such file or directory") > -1:
                    # ccnd is not running (socket not found)
                    self._state = ResourceState.FINISHED
                elif retcode:
                    # other error
                    msg = " Failed to execute command '%s'" % command
                    self.error(msg, out, err)
                    self._state = ResourceState.FAILED

                self._last_state_check = strfnow()

        return self._state

    @property
    def _default_command(self):
        return "ccndstart"

    @property
    def _default_dependencies(self):
        if self.node.os in [ OSType.FEDORA_12 , OSType.FEDORA_14 ]:
            return ( " autoconf openssl-devel  expat-devel libpcap-devel "
                " ecryptfs-utils-devel libxml2-devel automake gawk " 
                " gcc gcc-c++ git pcre-devel make ")
        elif self.node.os in [ OSType.UBUNTU , OSType.DEBIAN]:
            return ( " autoconf libssl-dev libexpat-dev libpcap-dev "
                " libecryptfs0 libxml2-utils automake gawk gcc g++ "
                " git-core pkg-config libpcre3-dev make ")
        return ""

    @property
    def _default_sources(self):
        return "http://www.ccnx.org/releases/ccnx-0.7.1.tar.gz"

    @property
    def _default_build(self):
        sources = self.get("sources").split(" ")[0]
        sources = os.path.basename(sources)

        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${EXP_HOME}/ccnx/bin/ccnd && "
                " echo 'sources found, nothing to do' "
            " ) || ( "
            # If not, untar and build
                " ( "
                    " mkdir -p ${SOURCES}/ccnx && "
                    " tar xf ${SOURCES}/%(sources)s --strip-components=1 -C ${SOURCES}/ccnx "
                 " ) && "
                    "cd ${SOURCES}/ccnx && "
                    # Just execute and silence warnings...
                    " ( ./configure && make ) "
             " )") % ({ 'sources': sources })

    @property
    def _default_install(self):
        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${EXP_HOME}/ccnx/bin/ccnd && "
                " echo 'sources found, nothing to do' "
            " ) || ( "
            # If not, install
                "  mkdir -p ${EXP_HOME}/ccnx/bin && "
                "  cp -r ${SOURCES}/ccnx ${EXP_HOME}"
            " )"
            )

    @property
    def _default_environment(self):
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

        env = "PATH=$PATH:${EXP_HOME}/ccnx/bin "
        env += " ".join(map(lambda k: "%s=%s" % (envs.get(k), self.get(k)) \
            if self.get(k) else "", envs.keys()))
        
        return env            
        
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

