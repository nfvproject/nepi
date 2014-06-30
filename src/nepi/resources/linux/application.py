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
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.linux.node import LinuxNode
from nepi.util.sshfuncs import ProcStatus
from nepi.util.timefuncs import tnow, tdiffsec

import os
import subprocess

# TODO: Resolve wildcards in commands!!
# TODO: When a failure occurs during deployment, scp and ssh processes are left running behind!!

@clsinit_copy
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

        ${HOME}/.nepi/nepi-usr --> Base directory for multi-experiment files
                      |
        ${LIB}        |- /lib --> Base directory for libraries
        ${BIN}        |- /bin --> Base directory for binary files
        ${SRC}        |- /src --> Base directory for sources
        ${SHARE}      |- /share --> Base directory for other files

        ${HOME}/.nepi/nepi-exp --> Base directory for single-experiment files
                      |
        ${EXP_HOME}   |- /<exp-id>  --> Base directory for experiment exp-id
                          |
        ${APP_HOME}       |- /<app-guid> --> Base directory for application 
                               |     specific files (e.g. command.sh, input)
                               | 
        ${RUN_HOME}            |- /<run-id> --> Base directory for run specific

    """

    _rtype = "LinuxApplication"
    _help = "Runs an application on a Linux host with a BASH command "
    _backend_type = "linux"

    @classmethod
    def _register_attributes(cls):
        command = Attribute("command", "Command to execute at application start. "
                "Note that commands will be executed in the ${RUN_HOME} directory, "
                "make sure to take this into account when using relative paths. ", 
                flags = Flags.Design)
        forward_x11 = Attribute("forwardX11", "Enables X11 forwarding for SSH connections", 
                flags = Flags.Design)
        env = Attribute("env", "Environment variables string for command execution",
                flags = Flags.Design)
        sudo = Attribute("sudo", "Run with root privileges", 
                flags = Flags.Design)
        depends = Attribute("depends", 
                "Space-separated list of packages required to run the application",
                flags = Flags.Design)
        sources = Attribute("sources", 
                "semi-colon separated list of regular files to be uploaded to ${SRC} "
                "directory prior to building. Archives won't be expanded automatically. "
                "Sources are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all sources). ",
                flags = Flags.Design)
        files = Attribute("files", 
                "semi-colon separated list of regular miscellaneous files to be uploaded "
                "to ${SHARE} directory. "
                "Files are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all files). ",
                flags = Flags.Design)
        libs = Attribute("libs", 
                "semi-colon separated list of libraries (e.g. .so files) to be uploaded "
                "to ${LIB} directory. "
                "Libraries are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all files). ",
                flags = Flags.Design)
        bins = Attribute("bins", 
                "semi-colon separated list of binary files to be uploaded "
                "to ${BIN} directory. "
                "Binaries are globally available for all experiments unless "
                "cleanHome is set to True (This will delete all files). ",
                flags = Flags.Design)
        code = Attribute("code", 
                "Plain text source code to be uploaded to the ${APP_HOME} directory. ",
                flags = Flags.Design)
        build = Attribute("build", 
                "Build commands to execute after deploying the sources. "
                "Sources are uploaded to the ${SRC} directory and code "
                "is uploaded to the ${APP_HOME} directory. \n"
                "Usage example: tar xzf ${SRC}/my-app.tgz && cd my-app && "
                "./configure && make && make clean.\n"
                "Make sure to make the build commands return with a nonzero exit "
                "code on error.",
                flags = Flags.Design)
        install = Attribute("install", 
                "Commands to transfer built files to their final destinations. "
                "Install commands are executed after build commands. ",
                flags = Flags.Design)
        stdin = Attribute("stdin", "Standard input for the 'command'", 
                flags = Flags.Design)
        tear_down = Attribute("tearDown", "Command to be executed just before " 
                "releasing the resource", 
                flags = Flags.Design)

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
        stdout = Trace("stdout", "Standard output stream", enabled = True)
        stderr = Trace("stderr", "Standard error stream", enabled = True)

        cls._register_trace(stdout)
        cls._register_trace(stderr)

    def __init__(self, ec, guid):
        super(LinuxApplication, self).__init__(ec, guid)
        self._pid = None
        self._ppid = None
        self._home = "app-%s" % self.guid
        # whether the command should run in foreground attached
        # to a terminal
        self._in_foreground = False

        # whether to use sudo to kill the application process
        self._sudo_kill = False

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
        node = self.get_connected(LinuxNode.get_rtype())
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

    def trace_filepath(self, filename):
        return os.path.join(self.run_home, filename)

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        self.info("Retrieving '%s' trace %s " % (name, attr))

        path = self.trace_filepath(name)
        
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
            
            if proc.poll():
                msg = " Couldn't read trace %s " % name
                self.error(msg, out, err)
                return None

            return out

        if attr == TraceAttr.STREAM:
            cmd = "dd if=%s bs=%d count=1 skip=%d" % (path, block, offset)
        elif attr == TraceAttr.SIZE:
            cmd = "stat -c%%s %s " % path

        (out, err), proc = self.node.execute(cmd)

        if proc.poll():
            msg = " Couldn't find trace %s " % name
            self.error(msg, out, err)
            return None
        
        if attr == TraceAttr.SIZE:
            out = int(out.strip())

        return out

    def do_provision(self):
        # take a snapshot of the system if user is root
        # to ensure that cleanProcess will not kill
        # pre-existent processes
        if self.node.get("username") == 'root':
            import pickle
            procs = dict()
            ps_aux = "ps aux |awk '{print $2,$11}'"
            (out, err), proc = self.node.execute(ps_aux)
            if len(out) != 0:
                for line in out.strip().split("\n"):
                    parts = line.strip().split(" ")
                    procs[parts[0]] = parts[1]
                pickle.dump(procs, open("/tmp/save.proc", "wb"))
            
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
            if self.ec.abort:
                self.debug("Interrupting provisioning. EC says 'ABORT")
                return
            
            ret = step()
            if ret:
                command.append(ret)

        # upload deploy script
        deploy_command = ";".join(command)
        self.execute_deploy_command(deploy_command)

        # upload start script
        self.upload_start_command()
       
        self.info("Provisioning finished")

        super(LinuxApplication, self).do_provision()

    def upload_start_command(self, overwrite = False):
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
                    env = env,
                    overwrite = overwrite)

    def execute_deploy_command(self, command, prefix="deploy"):
        if command:
            # replace application specific paths in the command
            command = self.replace_paths(command)
            
            # replace application specific paths in the environment
            env = self.get("env")
            env = env and self.replace_paths(env)

            # Upload the command to a bash script and run it
            # in background ( but wait until the command has
            # finished to continue )
            shfile = os.path.join(self.app_home, "%s.sh" % prefix)
            self.node.run_and_wait(command, self.run_home,
                    shfile = shfile, 
                    overwrite = False,
                    pidfile = "%s_pidfile" % prefix, 
                    ecodefile = "%s_exitcode" % prefix, 
                    stdout = "%s_stdout" % prefix, 
                    stderr = "%s_stderr" % prefix)

    def upload_sources(self, sources = None, src_dir = None):
        if not sources:
            sources = self.get("sources")
   
        command = ""

        if not src_dir:
            src_dir = self.node.src_dir

        if sources:
            self.info("Uploading sources ")

            sources = map(str.strip, sources.split(";"))

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
                            " ls %(src_dir)s/%(basename)s "
                            " || ( "
                            # If source doesn't exist, download it and check
                            # that it it downloaded ok
                            "   wget -c --directory-prefix=%(src_dir)s %(source)s && "
                            "   ls %(src_dir)s/%(basename)s "
                            " ) ) " % {
                                "basename": os.path.basename(source),
                                "source": source,
                                "src_dir": src_dir
                                })

            command = " && ".join(command)

            # replace application specific paths in the command
            command = self.replace_paths(command)
       
            if sources:
                sources = ';'.join(sources)
                self.node.upload(sources, src_dir, overwrite = False)

        return command

    def upload_files(self, files = None):
        if not files:
            files = self.get("files")

        if files:
            self.info("Uploading files %s " % files)
            self.node.upload(files, self.node.share_dir, overwrite = False)

    def upload_libraries(self, libs = None):
        if not libs:
            libs = self.get("libs")

        if libs:
            self.info("Uploading libraries %s " % libaries)
            self.node.upload(libs, self.node.lib_dir, overwrite = False)

    def upload_binaries(self, bins = None):
        if not bins:
            bins = self.get("bins")

        if bins:
            self.info("Uploading binaries %s " % binaries)
            self.node.upload(bins, self.node.bin_dir, overwrite = False)

    def upload_code(self, code = None):
        if not code:
            code = self.get("code")

        if code:
            self.info("Uploading code")

            dst = os.path.join(self.app_home, "code")
            self.node.upload(code, dst, overwrite = False, text = True)

    def upload_stdin(self, stdin = None):
        if not stdin:
           stdin = self.get("stdin")

        if stdin:
            # create dir for sources
            self.info("Uploading stdin")
            
            # upload stdin file to ${SHARE_DIR} directory
            if os.path.isfile(stdin):
                basename = os.path.basename(stdin)
                dst = os.path.join(self.node.share_dir, basename)
            else:
                dst = os.path.join(self.app_home, "stdin")

            self.node.upload(stdin, dst, overwrite = False, text = True)

            # create "stdin" symlink on ${APP_HOME} directory
            command = "( cd %(app_home)s ; [ ! -f stdin ] &&  ln -s %(stdin)s stdin )" % ({
                "app_home": self.app_home, 
                "stdin": dst })

            return command

    def install_dependencies(self, depends = None):
        if not depends:
            depends = self.get("depends")

        if depends:
            self.info("Installing dependencies %s" % depends)
            return self.node.install_packages_command(depends)

    def build(self, build = None):
        if not build:
            build = self.get("build")

        if build:
            self.info("Building sources ")
            
            # replace application specific paths in the command
            return self.replace_paths(build)

    def install(self, install = None):
        if not install:
            install = self.get("install")

        if install:
            self.info("Installing sources ")

            # replace application specific paths in the command
            return self.replace_paths(install)

    def do_deploy(self):
        # Wait until node is associated and deployed
        node = self.node
        if not node or node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            command = self.get("command") or ""
            self.info("Deploying command '%s' " % command)
            self.do_discover()
            self.do_provision()

            super(LinuxApplication, self).do_deploy()
   
    def do_start(self):
        command = self.get("command")

        self.info("Starting command '%s'" % command)

        if not command:
            # If no command was given (i.e. Application was used for dependency
            # installation), then the application is directly marked as STOPPED
            super(LinuxApplication, self).set_stopped()
        else:
            if self.in_foreground:
                self._run_in_foreground()
            else:
                self._run_in_background()

            super(LinuxApplication, self).do_start()

    def _run_in_foreground(self):
        command = self.get("command")
        sudo = self.get("sudo") or False
        x11 = self.get("forwardX11")
        env = self.get("env")

        # Command will be launched in foreground and attached to the
        # terminal using the node 'execute' in non blocking mode.

        # We save the reference to the process in self._proc 
        # to be able to kill the process from the stop method.
        # We also set blocking = False, since we don't want the
        # thread to block until the execution finishes.
        (out, err), self._proc = self.execute_command(command, 
                env = env,
                sudo = sudo,
                forward_x11 = x11,
                blocking = False)

        if self._proc.poll():
            self.error(msg, out, err)
            raise RuntimeError, msg

    def _run_in_background(self):
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
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg
    
    def do_stop(self):
        """ Stops application execution
        """
        command = self.get('command') or ''

        if self.state == ResourceState.STARTED:
        
            self.info("Stopping command '%s' " % command)
        
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
                    (out, err), proc = self.node.kill(self.pid, self.ppid,
                            sudo = self._sudo_kill)

                    # TODO: check if execution errors occurred
                    if (proc and proc.poll()) or err:
                        msg = " Failed to STOP command '%s' " % self.get("command")
                        self.error(msg, out, err)
        
            super(LinuxApplication, self).do_stop()

    def do_release(self):
        self.info("Releasing resource")

        self.do_stop()
        
        tear_down = self.get("tearDown")
        if tear_down:
            self.node.execute(tear_down)

        hard_release = self.get("hardRelease")
        if hard_release:
            self.node.rmdir(self.app_home)

        super(LinuxApplication, self).do_release()
        
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
                    self.do_fail()

                elif retcode == 0:
                    self.set_stopped()
            else:
                # We need to query the status of the command we launched in 
                # background. In order to avoid overwhelming the remote host and
                # the local processor with too many ssh queries, the state is only
                # requested every 'state_check_delay' seconds.
                state_check_delay = 0.5
                if tdiffsec(tnow(), self._last_state_check) > state_check_delay:
                    if self.pid and self.ppid:
                        # Make sure the process is still running in background
                        status = self.node.status(self.pid, self.ppid)

                        if status == ProcStatus.FINISHED:
                            # If the program finished, check if execution
                            # errors occurred
                            (out, err), proc = self.node.check_errors(
                                    self.run_home)

                            if err:
                                msg = "Failed to execute command '%s'" % \
                                        self.get("command")
                                self.error(msg, out, err)
                                self.do_fail()
                            else:
                                self.set_stopped()

                    self._last_state_check = tnow()

        return self._state

    def execute_command(self, command, 
            env = None,
            sudo = False,
            forward_x11 = False,
            blocking = False):

        environ = ""
        if env:
            environ = self.node.format_environment(env, inline = True)
        command = environ + command
        command = self.replace_paths(command)

        return self.node.execute(command,
                sudo = sudo,
                forward_x11 = forward_x11,
                blocking = blocking)

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

