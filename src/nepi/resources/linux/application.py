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
from nepi.execution.resource import ResourceManager, clsinit, ResourceState
from nepi.resources.linux.node import LinuxNode
from nepi.util.sshfuncs import ProcStatus
from nepi.util.timefuncs import strfnow, strfdiff

import os

# TODO: Resolve wildcards in commands!!


@clsinit
class LinuxApplication(ResourceManager):
    _rtype = "LinuxApplication"

    @classmethod
    def _register_attributes(cls):
        command = Attribute("command", "Command to execute", 
                flags = Flags.ExecReadOnly)
        forward_x11 = Attribute("forwardX11", " Enables X11 forwarding for SSH connections", 
                flags = Flags.ExecReadOnly)
        env = Attribute("env", "Environment variables string for command execution",
                flags = Flags.ExecReadOnly)
        sudo = Attribute("sudo", "Run with root privileges", 
                flags = Flags.ExecReadOnly)
        depends = Attribute("depends", 
                "Space-separated list of packages required to run the application",
                flags = Flags.ExecReadOnly)
        sources = Attribute("sources", 
                "Space-separated list of regular files to be deployed in the working "
                "path prior to building. Archives won't be expanded automatically.",
                flags = Flags.ExecReadOnly)
        code = Attribute("code", 
                "Plain text source code to be uploaded to the server. It will be stored "
                "under ${SOURCES}/code",
                flags = Flags.ExecReadOnly)
        build = Attribute("build", 
                "Build commands to execute after deploying the sources. "
                "Sources will be in the ${SOURCES} folder. "
                "Example: tar xzf ${SOURCES}/my-app.tgz && cd my-app && ./configure && make && make clean.\n"
                "Try to make the commands return with a nonzero exit code on error.\n"
                "Also, do not install any programs here, use the 'install' attribute. This will "
                "help keep the built files constrained to the build folder (which may "
                "not be the home folder), and will result in faster deployment. Also, "
                "make sure to clean up temporary files, to reduce bandwidth usage between "
                "nodes when transferring built packages.",
                flags = Flags.ReadOnly)
        install = Attribute("install", 
                "Commands to transfer built files to their final destinations. "
                "Sources will be in the initial working folder, and a special "
                "tag ${SOURCES} can be used to reference the experiment's "
                "home folder (where the application commands will run).\n"
                "ALL sources and targets needed for execution must be copied there, "
                "if building has been enabled.\n"
                "That is, 'slave' nodes will not automatically get any source files. "
                "'slave' nodes don't get build dependencies either, so if you need "
                "make and other tools to install, be sure to provide them as "
                "actual dependencies instead.",
                flags = Flags.ReadOnly)
        stdin = Attribute("stdin", "Standard input", flags = Flags.ExecReadOnly)
        stdout = Attribute("stdout", "Standard output", flags = Flags.ExecReadOnly)
        stderr = Attribute("stderr", "Standard error", flags = Flags.ExecReadOnly)
        tear_down = Attribute("tearDown", "Bash script to be executed before "
                "releasing the resource", 
                flags = Flags.ReadOnly)

        cls._register_attribute(command)
        cls._register_attribute(forward_x11)
        cls._register_attribute(env)
        cls._register_attribute(sudo)
        cls._register_attribute(depends)
        cls._register_attribute(sources)
        cls._register_attribute(code)
        cls._register_attribute(build)
        cls._register_attribute(install)
        cls._register_attribute(stdin)
        cls._register_attribute(stdout)
        cls._register_attribute(stderr)
        cls._register_attribute(tear_down)

    @classmethod
    def _register_traces(cls):
        stdout = Trace("stdout", "Standard output stream")
        stderr = Trace("stderr", "Standard error stream")

        cls._register_trace(stdout)
        cls._register_trace(stderr)

    def __init__(self, ec, guid):
        super(LinuxApplication, self).__init__(ec, guid)
        self._pid = None
        self._ppid = None
        self._home = "app-%s" % self.guid

        # keep a reference to the running process handler when 
        # the command is not executed as remote daemon in background
        self._proc = None

        # timestamp of last state check of the application
        self._last_state_check = strfnow()
    
    def log_message(self, msg):
        return " guid %d - host %s - %s " % (self.guid, 
                self.node.get("hostname"), msg)

    @property
    def node(self):
        node = self.get_connected(LinuxNode.rtype())
        if node: return node[0]
        return None

    @property
    def app_home(self):
        return os.path.join(self.node.exp_home, self._home)

    @property
    def src_dir(self):
        return os.path.join(self.app_home, 'src')

    @property
    def build_dir(self):
        return os.path.join(self.app_home, 'build')

    @property
    def pid(self):
        return self._pid

    @property
    def ppid(self):
        return self._ppid

    @property
    def in_foreground(self):
        """ Returns True is the command needs to be executed in foreground.
        This means that command will be executed using 'execute' instead of
        'run'.

        When using X11 forwarding option, the command can not run in background
        and detached from a terminal in the remote host, since we need to keep 
        the SSH connection to receive graphical data
        """
        return self.get("forwardX11") or False

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
            
    def provision(self):
        # create home dir for application
        self.node.mkdir(self.app_home)

        # upload sources
        self.upload_sources()

        # upload code
        self.upload_code()

        # upload stdin
        self.upload_stdin()

        # install dependencies
        self.install_dependencies()

        # build
        self.build()

        # Install
        self.install()

        # Upload command to remote bash script
        # - only if command can be executed in background and detached
        command = self.get("command")

        if command and not self.in_foreground:
            self.info("Uploading command '%s'" % command)

            # replace application specific paths in the command
            command = self.replace_paths(command)
            
            # replace application specific paths in the environment
            env = self.get("env")
            env = env and self.replace_paths(env)

            self.node.upload_command(command, self.app_home, 
                    shfile = "app.sh",
                    env = env)
       
        self.info("Provisioning finished")

        super(LinuxApplication, self).provision()

    def upload_sources(self):
        sources = self.get("sources")
        if sources:
            self.info("Uploading sources ")

            # create dir for sources
            self.node.mkdir(self.src_dir)

            sources = sources.split(' ')

            http_sources = list()
            for source in list(sources):
                if source.startswith("http") or source.startswith("https"):
                    http_sources.append(source)
                    sources.remove(source)

            # Download http sources remotely
            if http_sources:
                command = [" wget -c --directory-prefix=${SOURCES} "]
                check = []

                for source in http_sources:
                    command.append(" %s " % (source))
                    check.append(" ls ${SOURCES}/%s " % os.path.basename(source))
                
                command = " ".join(command)
                check = " ; ".join(check)

                # Append the command to check that the sources were downloaded
                command += " ; %s " % check

                # replace application specific paths in the command
                command = self.replace_paths(command)
                
                # Upload the command to a bash script and run it
                # in background ( but wait until the command has
                # finished to continue )
                self.node.run_and_wait(command, self.app_home,
                        shfile = "http_sources.sh",
                        pidfile = "http_sources_pidfile", 
                        ecodefile = "http_sources_exitcode", 
                        stdout = "http_sources_stdout", 
                        stderr = "http_sources_stderr")

            if sources:
                self.node.upload(sources, self.src_dir)

    def upload_code(self):
        code = self.get("code")
        if code:
            # create dir for sources
            self.node.mkdir(self.src_dir)

            self.info("Uploading code ")

            dst = os.path.join(self.src_dir, "code")
            self.node.upload(sources, dst, text = True)

    def upload_stdin(self):
        stdin = self.get("stdin")
        if stdin:
            # create dir for sources
            self.info(" Uploading stdin ")

            dst = os.path.join(self.app_home, "stdin")
            self.node.upload(stdin, dst, text = True)

    def install_dependencies(self):
        depends = self.get("depends")
        if depends:
            self.info("Installing dependencies %s" % depends)
            self.node.install_packages(depends, self.app_home)

    def build(self):
        build = self.get("build")
        if build:
            self.info("Building sources ")
            
            # create dir for build
            self.node.mkdir(self.build_dir)

            # replace application specific paths in the command
            command = self.replace_paths(build)

            # Upload the command to a bash script and run it
            # in background ( but wait until the command has
            # finished to continue )
            self.node.run_and_wait(command, self.app_home,
                    shfile = "build.sh",
                    pidfile = "build_pidfile", 
                    ecodefile = "build_exitcode", 
                    stdout = "build_stdout", 
                    stderr = "build_stderr")
 
    def install(self):
        install = self.get("install")
        if install:
            self.info("Installing sources ")

            # replace application specific paths in the command
            command = self.replace_paths(install)

            # Upload the command to a bash script and run it
            # in background ( but wait until the command has
            # finished to continue )
            self.node.run_and_wait(command, self.app_home,
                    shfile = "install.sh",
                    pidfile = "install_pidfile", 
                    ecodefile = "install_exitcode", 
                    stdout = "install_stdout", 
                    stderr = "install_stderr")

    def deploy(self):
        # Wait until node is associated and deployed
        node = self.node
        if not node or node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            
            reschedule_delay = "0.5s"
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            try:
                command = self.get("command") or ""
                self.info("Deploying command '%s' " % command)
                self.discover()
                self.provision()
            except:
                self._state = ResourceState.FAILED
                raise

            super(LinuxApplication, self).deploy()

    def start(self):
        command = self.get("command")
        env = self.get("env")
        stdin = "stdin" if self.get("stdin") else None
        stdout = "stdout" if self.get("stdout") else "stdout"
        stderr = "stderr" if self.get("stderr") else "stderr"
        sudo = self.get("sudo") or False
        failed = False

        self.info("Starting command '%s'" % command)

        if self.in_foreground:
            # If command should be ran in foreground, we invoke
            # the node 'execute' method
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
            
            x11 = self.get("forwardX11")

            # We save the reference to the process in self._proc 
            # to be able to kill the process from the stop method
            (out, err), self._proc = self.node.execute(command,
                    sudo = sudo,
                    stdin = stdin,
                    forward_x11 = x11,
                    blocking = False)

            if self._proc.poll():
                out = ""
                err = self._proc.stderr.read()
                self._state = ResourceState.FAILED
                self.error(msg, out, err)
                raise RuntimeError, msg
            
            super(LinuxApplication, self).start()

        elif command:
            # If command is set (i.e. application not used only for dependency
            # installation), and it does not need to run in foreground, we use 
            # the 'run' method of the node to launch the application as a daemon 

            # The real command to execute was previously uploaded to a remote bash
            # script during deployment, now run the remote script using 'run' method 
            # from the node
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

        else:
            # If no command was given (i.e. Application was used for dependency
            # installation), then the application is directly marked as FINISHED
            self._state = ResourceState.FINISHED
 
    def stop(self):
        """ Stops application execution
        """
        command = self.get('command') or ''
        state = self.state

        if state == ResourceState.STARTED:
            stopped = True

            self.info("Stopping command '%s'" % command)
        
            # If the command is running in foreground (it was launched using
            # the node 'execute' method), then we use the handler to the Popen
            # process to kill it. Else we send a kill signal using the pid and ppid
            # retrieved after running the command with the node 'run' method

            if self._proc:
                self._proc.kill()
            else:
                (out, err), proc = self.node.kill(self.pid, self.ppid)

                if out or err:
                    # check if execution errors occurred
                    msg = " Failed to STOP command '%s' " % self.get("command")
                    self.error(msg, out, err)
                    self._state = ResourceState.FAILED
                    stopped = False

            if stopped:
                super(LinuxApplication, self).stop()

    def release(self):
        self.info("Releasing resource")

        tear_down = self.get("tearDown")
        if tear_down:
            self.node.execute(tear_down)

        self.stop()
        if self.state == ResourceState.STOPPED:
            super(LinuxApplication, self).release()
    
    @property
    def state(self):
        if self._state == ResourceState.STARTED:
            if self.in_foreground:
                retcode = self._proc.poll()
                
                # retcode == None -> running
                # retcode > 0 -> error
                # retcode == 0 -> finished
                if retcode:
                    out = ""
                    err = self._proc.stderr.read()
                    self._state = ResourceState.FAILED
                    self.error(msg, out, err)
                elif retcode == 0:
                    self._state = ResourceState.FINISHED

            else:
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

    def replace_paths(self, command):
        """
        Replace all special path tags with shell-escaped actual paths.
        """
        def absolute_dir(d):
            return d if d.startswith("/") else os.path.join("${HOME}", d)

        return ( command
            .replace("${SOURCES}", absolute_dir(self.src_dir))
            .replace("${BUILD}", absolute_dir(self.build_dir))
            .replace("${APP_HOME}", absolute_dir(self.app_home))
            .replace("${NODE_HOME}", absolute_dir(self.node.node_home))
            .replace("${EXP_HOME}", absolute_dir(self.node.exp_home) )
            )
        
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

