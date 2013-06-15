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

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        self.info("Retrieving '%s' trace %s " % (name, attr))

        path = os.path.join(self.app_home, name)
        
        command = "(test -f %s && echo 'success') || echo 'error'" % path
        (out, err), proc = self.node.execute(command)

        if (err and proc.poll()) or out.find("error") != -1:
            msg = " Couldn't find trace %s " % name
            self.error(msg, out, err)
            return None
    
        if attr == TraceAttr.PATH:
            return path

        if attr == TraceAttr.ALL:
            (out, err), proc = self.node.check_output(self.app_home, name)
            
            if err and proc.poll():
                msg = " Couldn't read trace %s " % name
                self.error(msg, out, err)
                return None

            return out

        if attr == TraceAttr.STREAM:
            cmd = "dd if=%s bs=%d count=1 skip=%d" % (path, block, offset)
        elif attr == TraceAttr.SIZE:
            cmd = "stat -c%%s %s " % path

        (out, err), proc = self.node.execute(cmd)

        if err and proc.poll():
            msg = " Couldn't find trace %s " % name
            self.error(msg, out, err)
            return None
        
        if attr == TraceAttr.SIZE:
            out = int(out.strip())

        return out
            
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

    def start(self):
        command = self.get("command")
        env = self.get("env")
        stdin = "stdin" if self.get("stdin") else None
        stdout = "stdout" if self.get("stdout") else "stdout"
        stderr = "stderr" if self.get("stderr") else "stderr"
        sudo = self.get("sudo") or False
        x11 = self.get("forwardX11") or False
        failed = False

        if not command:
            # If no command was given, then the application 
            # is directly marked as FINISHED
            self._state = ResourceState.FINISHED
    
        self.info("Starting command '%s'" % command)

        if x11:
            # If X11 forwarding was specified, then the application
            # can not run detached, so instead of invoking asynchronous
            # 'run' we invoke synchronous 'execute'.
            if not command:
                msg = "No command is defined but X11 forwarding has been set"
                self.error(msg)
                self._state = ResourceState.FAILED
                raise RuntimeError, msg

            # Export environment
            environ = "\n".join(map(lambda e: "export %s" % e, env.split(" ")))\
                if env else ""

            command = environ + command
            command = self.replace_paths(command)

            # Mark application as started before executing the command
            # since after the thread will be blocked by the execution
            # until it finished
            super(LinuxApplication, self).start()
            
            # If the command requires X11 forwarding, we
            # can't run it asynchronously
            (out, err), proc = self.node.execute(command,
                    sudo = sudo,
                    stdin = stdin,
                    forward_x11 = x11)

            self._state = ResourceState.FINISHED

            if proc.poll() and err:
                failed = True
        else:
            # Command was  previously uploaded, now run the remote
            # bash file asynchronously
            cmd = "bash ./app.sh"
            (out, err), proc = self.node.run(cmd, self.app_home, 
                stdin = stdin, 
                stdout = stdout,
                stderr = stderr,
                sudo = sudo)

            # check if execution errors occurred
            msg = " Failed to start command '%s' " % command
            
            if proc.poll() and err:
                self.error(msg, out, err)
                raise RuntimeError, msg
        
            # Check status of process running in background
            pid, ppid = self.node.wait_pid(self.app_home)
            if pid: self._pid = int(pid)
            if ppid: self._ppid = int(ppid)

            # If the process is not running, check for error information
            # on the remote machine
            if not self.pid or not self.ppid:
                (out, err), proc = self.node.check_output(self.app_home, 'stderr')
                self.error(msg, out, err)

                msg2 = " Setting state to Failed"
                self.debug(msg2)
                self._state = ResourceState.FAILED

                raise RuntimeError, msg
            
            super(LinuxApplication, self).start()

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
            # To avoid overwhelming the remote hosts and the local processor
            # with too many ssh queries, the state is only requested
            # every 'state_check_delay' seconds.
            state_check_delay = 0.5
            if strfdiff(strfnow(), self._last_state_check) > state_check_delay:
                # check if execution errors occurred
                (out, err), proc = self.node.check_errors(self.app_home)

                if out or err:
                    if err.find("No such file or directory") >= 0 :
                        # The resource is marked as started, but the
                        # command was not yet executed
                        return ResourceState.READY

                    msg = " Failed to execute command '%s'" % self.get("command")
                    self.error(msg, out, err)
                    self._state = ResourceState.FAILED

                elif self.pid and self.ppid:
                    status = self.node.status(self.pid, self.ppid)

                    if status == ProcStatus.FINISHED:
                        self._state = ResourceState.FINISHED


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
                "  test -f ${EXP_HOME}/ccnx/bin/ccnd"
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
                "  test -f ${EXP_HOME}/ccnx/bin/ccnd"
            " ) || ( "
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

        env = "PATH=$PATH:${EXP_HOME}/ccnx/bin"
        for key in envs.keys():
            val = self.get(key)
            if val:
                env += " %s=%s" % (key, val)
        
        return env            
        
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

