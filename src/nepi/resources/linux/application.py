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
from nepi.execution.resource import ResourceManager, clsinit, ResourceState, \
    reschedule_delay
from nepi.resources.linux.node import LinuxNode
from nepi.util.sshfuncs import ProcStatus
from nepi.util.timefuncs import tnow, tdiffsec

import os
import subprocess

# TODO: Resolve wildcards in commands!!
# TODO: During provisioning, everything that is not scp could be
#       uploaded to a same script, http_sources download, etc...
#       and like that require performing less ssh connections!!!
# TODO: Make stdin be a symlink to the original file in ${SHARE}
#       - later use md5sum to check wether the file needs to be re-upload


@clsinit
class LinuxApplication(ResourceManager):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    .. note::

    A LinuxApplication RM represents a process that can be executed in
    a remote Linux host using SSH.

    The LinuxApplication RM takes care of uploadin sources and any files
    needed to run the experiment, to the remote host. 
    It also allows to provide source compilation (build) and installation 
    instructions, and takes care of automating the sources build and 
    installation tasks for the user.

    It is important to note that files uploaded to the remote host have
    two possible scopes: single-experiment or multi-experiment.
    Single experiment files are those that will not be re-used by other 
    experiments. Multi-experiment files are those that will.
    Sources and shared files are always made available to all experiments.

    Directory structure:

    The directory structure used by LinuxApplication RM at the Linux
    host is the following:

        ${HOME}/nepi-usr --> Base directory for multi-experiment files
                      |
        ${LIB}        |- /lib --> Base directory for libraries
        ${BIN}        |- /bin --> Base directory for binary files
        ${SRC}        |- /src --> Base directory for sources
        ${SHARE}      |- /share --> Base directory for other files

        ${HOME}/nepi-exp --> Base directory for single-experiment files
                      |
        ${EXP_HOME}   |- /<exp-id>  --> Base directory for experiment exp-id
                          |
        ${APP_HOME}       |- /<app-guid> --> Base directory for application 
                               |     specific files (e.g. command.sh, input)
                               | 
        ${RUN_HOME}            |- /<run-id> --> Base directory for run specific

    """

    _rtype = "LinuxApplication"

    @classmethod
    def _register_attributes(cls):
        command = Attribute("command", "Command to execute at application start. "
                "Note that commands will be executed in the ${RUN_HOME} directory, "
                "make sure to take this into account when using relative paths. ", 
                flags = Flags.ExecReadOnly)
        forward_x11 = Attribute("forwardX11", "Enables X11 forwarding for SSH connections", 
                flags = Flags.ExecReadOnly)
        env = Attribute("env", "Environment variables string for command execution",
                flags = Flags.ExecReadOnly)
        sudo = Attribute("sudo", "Run with root privileges", 
                flags = Flags.ExecReadOnly)
        depends = Attribute("depends", 
                "Space-separated list of packages required to run the application",
                flags = Flags.ExecReadOnly)
        sources = Attribute("sources", 
                "Space-separated list of regular files to be uploaded to ${SRC} "
                "directory prior to building. Archives won't be expanded automatically. "
                "Sources are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all sources). ",
                flags = Flags.ExecReadOnly)
        files = Attribute("files", 
                "Space-separated list of regular miscellaneous files to be uploaded "
                "to ${SHARE} directory. "
                "Files are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all files). ",
                flags = Flags.ExecReadOnly)
        libs = Attribute("libs", 
                "Space-separated list of libraries (e.g. .so files) to be uploaded "
                "to ${LIB} directory. "
                "Libraries are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all files). ",
                flags = Flags.ExecReadOnly)
        bins = Attribute("bins", 
                "Space-separated list of binary files to be uploaded "
                "to ${BIN} directory. "
                "Binaries are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all files). ",
                flags = Flags.ExecReadOnly)
        code = Attribute("code", 
                "Plain text source code to be uploaded to the ${APP_HOME} directory. ",
                flags = Flags.ExecReadOnly)
        build = Attribute("build", 
                "Build commands to execute after deploying the sources. "
                "Sources are uploaded to the ${SRC} directory and code "
                "is uploaded to the ${APP_HOME} directory. \n"
                "Usage example: tar xzf ${SRC}/my-app.tgz && cd my-app && "
                "./configure && make && make clean.\n"
                "Make sure to make the build commands return with a nonzero exit "
                "code on error.",
                flags = Flags.ReadOnly)
        install = Attribute("install", 
                "Commands to transfer built files to their final destinations. "
                "Install commands are executed after build commands. ",
                flags = Flags.ReadOnly)
        stdin = Attribute("stdin", "Standard input for the 'command'", 
                flags = Flags.ExecReadOnly)
        tear_down = Attribute("tearDown", "Command to be executed just before " 
                "releasing the resource", 
                flags = Flags.ReadOnly)

        cls._register_attribute(command)
        cls._register_attribute(forward_x11)
        cls._register_attribute(env)
        cls._register_attribute(sudo)
        cls._register_attribute(depends)
        cls._register_attribute(sources)
        cls._register_attribute(code)
        cls._register_attribute(files)
        cls._register_attribute(bins)
        cls._register_attribute(libs)
        cls._register_attribute(build)
        cls._register_attribute(install)
        cls._register_attribute(stdin)
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
        self._in_foreground = False

        # keep a reference to the running process handler when 
        # the command is not executed as remote daemon in background
        self._proc = None

        # timestamp of last state check of the application
        self._last_state_check = tnow()

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
    def run_home(self):
        return os.path.join(self.app_home, self.ec.run_id)

    @property
    def pid(self):
        return self._pid

    @property
    def ppid(self):
        return self._ppid

    @property
    def in_foreground(self):
        """ Returns True if the command needs to be executed in foreground.
        This means that command will be executed using 'execute' instead of
        'run' ('run' executes a command in background and detached from the 
        terminal)
        
        When using X11 forwarding option, the command can not run in background
        and detached from a terminal, since we need to keep the terminal attached 
        to interact with it.
        """
        return self.get("forwardX11") or self._in_foreground

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        self.info("Retrieving '%s' trace %s " % (name, attr))

        path = os.path.join(self.run_home, name)
        
        command = "(test -f %s && echo 'success') || echo 'error'" % path
        (out, err), proc = self.node.execute(command)

        if (err and proc.poll()) or out.find("error") != -1:
            msg = " Couldn't find trace %s " % name
            self.error(msg, out, err)
            return None
    
        if attr == TraceAttr.PATH:
            return path

        if attr == TraceAttr.ALL:
            (out, err), proc = self.node.check_output(self.run_home, name)
            
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
        # create run dir for application
        self.node.mkdir(self.run_home)
   
        # List of all the provision methods to invoke
        steps = [
            # upload sources
            self.upload_sources,
            # upload files
            self.upload_files,
            # upload binaries
            self.upload_binaries,
            # upload libraries
            self.upload_libraries,
            # upload code
            self.upload_code,
            # upload stdin
            self.upload_stdin,
            # install dependencies
            self.install_dependencies,
            # build
            self.build,
            # Install
            self.install]

        command = []

        # Since provisioning takes a long time, before
        # each step we check that the EC is still 
        for step in steps:
            if self.ec.finished:
                raise RuntimeError, "EC finished"
            
            ret = step()
            if ret:
                command.append(ret)

        # upload deploy script
        deploy_command = ";".join(command)
        self.execute_deploy_command(deploy_command)

        # upload start script
        self.upload_start_command()
       
        self.info("Provisioning finished")

        super(LinuxApplication, self).provision()

    def upload_start_command(self):
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

            shfile = os.path.join(self.app_home, "start.sh")

            self.node.upload_command(command, 
                    shfile = shfile,
                    env = env)

    def execute_deploy_command(self, command):
        if command:
            # Upload the command to a bash script and run it
            # in background ( but wait until the command has
            # finished to continue )
            shfile = os.path.join(self.app_home, "deploy.sh")
            self.node.run_and_wait(command, self.run_home,
                    shfile = shfile, 
                    overwrite = False,
                    pidfile = "deploy_pidfile", 
                    ecodefile = "deploy_exitcode", 
                    stdout = "deploy_stdout", 
                    stderr = "deploy_stderr")

    def upload_sources(self):
        sources = self.get("sources")
   
        command = ""

        if sources:
            self.info("Uploading sources ")

            sources = sources.split(' ')

            # Separate sources that should be downloaded from 
            # the web, from sources that should be uploaded from
            # the local machine
            command = []
            for source in list(sources):
                if source.startswith("http") or source.startswith("https"):
                    # remove the hhtp source from the sources list
                    sources.remove(source)

                    command.append( " ( " 
                            # Check if the source already exists
                            " ls ${SRC}/%(basename)s "
                            " || ( "
                            # If source doesn't exist, download it and check
                            # that it it downloaded ok
                            "   wget -c --directory-prefix=${SRC} %(source)s && "
                            "   ls ${SRC}/%(basename)s "
                            " ) ) " % {
                                "basename": os.path.basename(source),
                                "source": source
                                })

            command = " && ".join(command)

            # replace application specific paths in the command
            command = self.replace_paths(command)
       
            if sources:
                sources = ' '.join(sources)
                self.node.upload(sources, self.node.src_dir, overwrite = False)

        return command

    def upload_files(self):
        files = self.get("files")

        if files:
            self.info("Uploading files %s " % files)
            self.node.upload(files, self.node.share_dir, overwrite = False)

    def upload_libraries(self):
        libs = self.get("libs")

        if libs:
            self.info("Uploading libraries %s " % libaries)
            self.node.upload(libs, self.node.lib_dir, overwrite = False)

    def upload_binaries(self):
        bins = self.get("bins")

        if bins:
            self.info("Uploading binaries %s " % binaries)
            self.node.upload(bins, self.node.bin_dir, overwrite = False)

    def upload_code(self):
        code = self.get("code")

        if code:
            self.info("Uploading code")

            dst = os.path.join(self.app_home, "code")
            self.node.upload(code, dst, overwrite = False, text = True)

    def upload_stdin(self):
        stdin = self.get("stdin")
        if stdin:
            # create dir for sources
            self.info("Uploading stdin")
            
            dst = os.path.join(self.app_home, "stdin")
            self.node.upload(stdin, dst, overwrite = False, text = True)

    def install_dependencies(self):
        depends = self.get("depends")
        if depends:
            self.info("Installing dependencies %s" % depends)
            self.node.install_packages(depends, self.app_home, self.run_home)

    def build(self):
        build = self.get("build")

        if build:
            self.info("Building sources ")
            
            # replace application specific paths in the command
            return self.replace_paths(build)

    def install(self):
        install = self.get("install")

        if install:
            self.info("Installing sources ")

            # replace application specific paths in the command
            return self.replace_paths(install)

    def deploy(self):
        # Wait until node is associated and deployed
        node = self.node
        if not node or node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            try:
                command = self.get("command") or ""
                self.info("Deploying command '%s' " % command)
                self.discover()
                self.provision()
            except:
                self.fail()
                raise

            super(LinuxApplication, self).deploy()

    def start(self):
        command = self.get("command")

        self.info("Starting command '%s'" % command)

        if not command:
            # If no command was given (i.e. Application was used for dependency
            # installation), then the application is directly marked as FINISHED
            self._state = ResourceState.FINISHED
        else:

            if self.in_foreground:
                self._start_in_foreground()
            else:
                self._start_in_background()

            super(LinuxApplication, self).start()

    def _start_in_foreground(self):
        command = self.get("command")
        sudo = self.get("sudo") or False
        x11 = self.get("forwardX11")

        # For a command being executed in foreground, if there is stdin,
        # it is expected to be text string not a file or pipe
        stdin = self.get("stdin") or None

        # Command will be launched in foreground and attached to the
        # terminal using the node 'execute' in non blocking mode.

        # Export environment
        env = self.get("env")
        environ = self.node.format_environment(env, inline = True)
        command = environ + command
        command = self.replace_paths(command)

        # We save the reference to the process in self._proc 
        # to be able to kill the process from the stop method.
        # We also set blocking = False, since we don't want the
        # thread to block until the execution finishes.
        (out, err), self._proc = self.node.execute(command,
                sudo = sudo,
                stdin = stdin,
                forward_x11 = x11,
                blocking = False)

        if self._proc.poll():
            self.fail()
            self.error(msg, out, err)
            raise RuntimeError, msg

    def _start_in_background(self):
        command = self.get("command")
        env = self.get("env")
        sudo = self.get("sudo") or False

        stdout = "stdout"
        stderr = "stderr"
        stdin = os.path.join(self.app_home, "stdin") if self.get("stdin") \
                else None

        # Command will be run as a daemon in baground and detached from any
        # terminal.
        # The command to run was previously uploaded to a bash script
        # during deployment, now we launch the remote script using 'run'
        # method from the node.
        cmd = "bash %s" % os.path.join(self.app_home, "start.sh")
        (out, err), proc = self.node.run(cmd, self.run_home, 
            stdin = stdin, 
            stdout = stdout,
            stderr = stderr,
            sudo = sudo)

        # check if execution errors occurred
        msg = " Failed to start command '%s' " % command
        
        if proc.poll():
            self.fail()
            self.error(msg, out, err)
            raise RuntimeError, msg
    
        # Wait for pid file to be generated
        pid, ppid = self.node.wait_pid(self.run_home)
        if pid: self._pid = int(pid)
        if ppid: self._ppid = int(ppid)

        # If the process is not running, check for error information
        # on the remote machine
        if not self.pid or not self.ppid:
            (out, err), proc = self.node.check_errors(self.run_home,
                    stderr = stderr) 

            # Out is what was written in the stderr file
            if err:
                self.fail()
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg
        
    def stop(self):
        """ Stops application execution
        """
        command = self.get('command') or ''

        if self.state == ResourceState.STARTED:
            stopped = True

            self.info("Stopping command '%s'" % command)
        
            # If the command is running in foreground (it was launched using
            # the node 'execute' method), then we use the handler to the Popen
            # process to kill it. Else we send a kill signal using the pid and ppid
            # retrieved after running the command with the node 'run' method

            if self._proc:
                self._proc.kill()
            else:
                # Only try to kill the process if the pid and ppid
                # were retrieved
                if self.pid and self.ppid:
                    (out, err), proc = self.node.kill(self.pid, self.ppid)

                    if out or err:
                        # check if execution errors occurred
                        msg = " Failed to STOP command '%s' " % self.get("command")
                        self.error(msg, out, err)
                        self.fail()
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
        """ Returns the state of the application
        """
        if self._state == ResourceState.STARTED:
            if self.in_foreground:
                # Check if the process we used to execute the command
                # is still running ...
                retcode = self._proc.poll()

                # retcode == None -> running
                # retcode > 0 -> error
                # retcode == 0 -> finished
                if retcode:
                    out = ""
                    msg = " Failed to execute command '%s'" % self.get("command")
                    err = self._proc.stderr.read()
                    self.error(msg, out, err)
                    self.fail()
                elif retcode == 0:
                    self._state = ResourceState.FINISHED

            else:
                # We need to query the status of the command we launched in 
                # background. In oredr to avoid overwhelming the remote host and
                # the local processor with too many ssh queries, the state is only
                # requested every 'state_check_delay' seconds.
                state_check_delay = 0.5
                if tdiffsec(tnow(), self._last_state_check) > state_check_delay:
                    # check if execution errors occurred
                    (out, err), proc = self.node.check_errors(self.run_home)

                    if err:
                        msg = " Failed to execute command '%s'" % self.get("command")
                        self.error(msg, out, err)
                        self.fail()

                    elif self.pid and self.ppid:
                        # No execution errors occurred. Make sure the background
                        # process with the recorded pid is still running.
                        status = self.node.status(self.pid, self.ppid)

                        if status == ProcStatus.FINISHED:
                            self._state = ResourceState.FINISHED

                    self._last_state_check = tnow()

        return self._state

    def replace_paths(self, command):
        """
        Replace all special path tags with shell-escaped actual paths.
        """
        return ( command
            .replace("${USR}", self.node.usr_dir)
            .replace("${LIB}", self.node.lib_dir)
            .replace("${BIN}", self.node.bin_dir)
            .replace("${SRC}", self.node.src_dir)
            .replace("${SHARE}", self.node.share_dir)
            .replace("${EXP}", self.node.exp_dir)
            .replace("${EXP_HOME}", self.node.exp_home)
            .replace("${APP_HOME}", self.app_home)
            .replace("${RUN_HOME}", self.run_home)
            .replace("${NODE_HOME}", self.node.node_home)
            .replace("${HOME}", self.node.home_dir)
            )

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

