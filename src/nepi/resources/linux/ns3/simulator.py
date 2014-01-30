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
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.node import OSType
from nepi.util.timefuncs import tnow, tdiffsec
from nepi.resources.ns3.simulator import NS3Simulator

import os

@clsinit_copy
class LinuxNS3Simulator(LinuxApplication, NS3Simulator):
    _rtype = "LinuxSimulator"

    @classmethod
    def _register_attributes(cls):
        max_rte = Attribute("maxRteMicrosec",
            "Sets the CCND_MAX_RTE_MICROSEC environmental variable. ",
            flags = Flags.ExecReadOnly)

        keystore = Attribute("keyStoreDirectory",
            "Sets the CCND_KEYSTORE_DIRECTORY environmental variable. ",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(debug)
        cls._register_attribute(port)

    @classmethod
    def _register_traces(cls):
        log = Trace("log", "CCND log output")
        status = Trace("status", "ccndstatus output")

        cls._register_trace(log)
        cls._register_trace(status)

    def __init__(self, ec, guid):
        super(LinuxCCND, self).__init__(ec, guid)
        self._home = "ccnd-%s" % self.guid
        self._version = "ccnx"

    @property
    def version(self):
        return self._version

    @property
    def path(self):
        return "PATH=$PATH:${BIN}/%s/" % self.version 

    def do_deploy(self):
        if not self.node or self.node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            
            # ccnd needs to wait until node is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("command"):
                self.set("command", self._start_command)
            
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

            if not self.get("install"):
                self.set("install", self._install)

            if not self.get("env"):
                self.set("env", self._environment)

            command = self.get("command")

            self.info("Deploying command '%s' " % command)

            self.do_discover()
            self.do_provision()

            self.debug("----- READY ---- ")
            self.set_ready()

    def upload_start_command(self):
        command = self.get("command")
        env = self.get("env")

        # We want to make sure the ccnd is running
        # before the experiment starts.
        # Run the command as a bash script in background,
        # in the host ( but wait until the command has
        # finished to continue )
        env = self.replace_paths(env)
        command = self.replace_paths(command)

        shfile = os.path.join(self.app_home, "start.sh")
        self.node.run_and_wait(command, self.run_home,
                shfile = shfile,
                overwrite = False,
                env = env,
                raise_on_error = True)

    def do_start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        command = self.get('command') or ''
        
        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = "ccndstop"
            env = self.get("env") 

            # replace application specific paths in the command
            command = self.replace_paths(command)
            env = env and self.replace_paths(env)

            # Upload the command to a file, and execute asynchronously
            shfile = os.path.join(self.app_home, "stop.sh")
            self.node.run_and_wait(command, self.run_home,
                        shfile = shfile,
                        overwrite = False,
                        env = env,
                        pidfile = "ccndstop_pidfile", 
                        ecodefile = "ccndstop_exitcode", 
                        stdout = "ccndstop_stdout", 
                        stderr = "ccndstop_stderr")

            self.set_stopped()
    
    @property
    def state(self):
        # First check if the ccnd has failed
        state_check_delay = 0.5
        if self._state == ResourceState.STARTED and \
                tdiffsec(tnow(), self._last_state_check) > state_check_delay:
            (out, err), proc = self._ccndstatus()

            retcode = proc.poll()

            if retcode == 1 and err.find("No such file or directory") > -1:
                # ccnd is not running (socket not found)
                self.set_stopped()
            elif retcode:
                # other errors ...
                msg = " Failed to execute command '%s'" % self.get("command")
                self.error(msg, out, err)
                self.fail()

            self._last_state_check = tnow()

        return self._state

    def _ccndstatus(self):
        env = self.get('env') or ""
        environ = self.node.format_environment(env, inline = True)
        command = environ + " ccndstatus"
        command = self.replace_paths(command)
    
        return self.node.execute(command)

    @property
    def _start_command(self):
        return "ccndstart"

    @property
    def _dependencies(self):
        if self.node.use_rpm:
            return ( " autoconf openssl-devel  expat-devel libpcap-devel "
                " ecryptfs-utils-devel libxml2-devel automake gawk " 
                " gcc gcc-c++ git pcre-devel make ")
        elif self.node.use_deb:
            return ( " autoconf libssl-dev libexpat-dev libpcap-dev "
                " libecryptfs0 libxml2-utils automake gawk gcc g++ "
                " git-core pkg-config libpcre3-dev make ")
        return ""

    @property
    def _sources(self):
        return "http://www.ccnx.org/releases/ccnx-0.7.2.tar.gz"

    @property
    def _build(self):
        sources = self.get("sources").split(" ")[0]
        sources = os.path.basename(sources)

        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${BIN}/%(version)s/ccnd && "
                " echo 'binaries found, nothing to do' "
            " ) || ( "
            # If not, untar and build
                " ( "
                    " mkdir -p ${SRC}/%(version)s && "
                    " tar xf ${SRC}/%(sources)s --strip-components=1 -C ${SRC}/%(version)s "
                 " ) && "
                    "cd ${SRC}/%(version)s && "
                    # Just execute and silence warnings...
                    " ( ./configure && make ) "
             " )") % ({ 'sources': sources,
                        'version': self.version
                 })

    @property
    def _install(self):
        return (
            # Evaluate if ccnx binaries are already installed
            " ( "
                " test -f ${BIN}/%(version)s/ccnd && "
                " echo 'binaries found, nothing to do' "
            " ) || ( "
            # If not, install
                "  mkdir -p ${BIN}/%(version)s && "
                "  mv ${SRC}/%(version)s/bin/* ${BIN}/%(version)s/ "
            " )"
            ) % ({ 'version': self.version
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

        env = self.path 
        env += " ".join(map(lambda k: "%s=%s" % (envs.get(k), str(self.get(k))) \
            if self.get(k) else "", envs.keys()))
        
        return env            

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

