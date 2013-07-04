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

from nepi.execution.attribute import Attribute, Flags
from nepi.execution.resource import ResourceManager, clsinit, ResourceState, \
        reschedule_delay
from nepi.resources.linux import rpmfuncs, debfuncs 
from nepi.util import sshfuncs, execfuncs
from nepi.util.sshfuncs import ProcStatus

import collections
import os
import random
import re
import tempfile
import time
import threading
import traceback

# TODO: Unify delays!!
# TODO: Validate outcome of uploads!! 

class ExitCode:
    """
    Error codes that the rexitcode function can return if unable to
    check the exit code of a spawned process
    """
    FILENOTFOUND = -1
    CORRUPTFILE = -2
    ERROR = -3
    OK = 0

class OSType:
    """
    Supported flavors of Linux OS
    """
    FEDORA_8 = "f8"
    FEDORA_12 = "f12"
    FEDORA_14 = "f14"
    FEDORA = "fedora"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"

@clsinit
class LinuxNode(ResourceManager):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    .. note::

        There are different ways in which commands can be executed using the
        LinuxNode interface (i.e. 'execute' - blocking and non blocking, 'run',
        'run_and_wait'). 
        
        Brief explanation:

            * 'execute' (blocking mode) :  

                     HOW IT WORKS: 'execute', forks a process and run the
                     command, synchronously, attached to the terminal, in
                     foreground.
                     The execute method will block until the command returns
                     the result on 'out', 'err' (so until it finishes executing).
  
                     USAGE: short-lived commands that must be executed attached
                     to a terminal and in foreground, for which it IS necessary
                     to block until the command has finished (e.g. if you want
                     to run 'ls' or 'cat').

            * 'execute' (NON blocking mode - blocking = False) :

                    HOW IT WORKS: Same as before, except that execute method
                    will return immediately (even if command still running).

                    USAGE: long-lived commands that must be executed attached
                    to a terminal and in foreground, but for which it is not
                    necessary to block until the command has finished. (e.g.
                    start an application using X11 forwarding)

             * 'run' :

                   HOW IT WORKS: Connects to the host ( using SSH if remote)
                   and launches the command in background, detached from any
                   terminal (daemonized), and returns. The command continues to
                   run remotely, but since it is detached from the terminal,
                   its pipes (stdin, stdout, stderr) can't be redirected to the
                   console (as normal non detached processes would), and so they
                   are explicitly redirected to files. The pidfile is created as
                   part of the process of launching the command. The pidfile
                   holds the pid and ppid of the process forked in background,
                   so later on it is possible to check whether the command is still
                   running.

                    USAGE: long-lived commands that can run detached in background,
                    for which it is NOT necessary to block (wait) until the command
                    has finished. (e.g. start an application that is not using X11
                    forwarding. It can run detached and remotely in background)

             * 'run_and_wait' :

                    HOW IT WORKS: Similar to 'run' except that it 'blocks' until
                    the command has finished execution. It also checks whether
                    errors occurred during runtime by reading the exitcode file,
                    which contains the exit code of the command that was run
                    (checking stderr only is not always reliable since many
                    commands throw debugging info to stderr and the only way to
                    automatically know whether an error really happened is to
                    check the process exit code).

                    Another difference with respect to 'run', is that instead
                    of directly executing the command as a bash command line,
                    it uploads the command to a bash script and runs the script.
                    This allows to use the bash script to debug errors, since
                    it remains at the remote host and can be run manually to
                    reproduce the error.
                  
                    USAGE: medium-lived commands that can run detached in
                    background, for which it IS necessary to block (wait) until
                    the command has finished. (e.g. Package installation,
                    source compilation, file download, etc)

    """
    _rtype = "LinuxNode"

    @classmethod
    def _register_attributes(cls):
        hostname = Attribute("hostname", "Hostname of the machine",
                flags = Flags.ExecReadOnly)

        username = Attribute("username", "Local account username", 
                flags = Flags.Credential)

        port = Attribute("port", "SSH port", flags = Flags.ExecReadOnly)
        
        home = Attribute("home",
                "Experiment home directory to store all experiment related files",
                flags = Flags.ExecReadOnly)
        
        identity = Attribute("identity", "SSH identity file",
                flags = Flags.Credential)
        
        server_key = Attribute("serverKey", "Server public key", 
                flags = Flags.ExecReadOnly)
        
        clean_home = Attribute("cleanHome", "Remove all nepi files and directories "
                " from node home folder before starting experiment", 
                flags = Flags.ExecReadOnly)

        clean_experiment = Attribute("cleanExperiment", "Remove all files and directories " 
                " from a previous same experiment, before the new experiment starts", 
                flags = Flags.ExecReadOnly)
        
        clean_processes = Attribute("cleanProcesses", 
                "Kill all running processes before starting experiment",
                flags = Flags.ExecReadOnly)
        
        tear_down = Attribute("tearDown", "Bash script to be executed before " + \
                "releasing the resource",
                flags = Flags.ExecReadOnly)

        cls._register_attribute(hostname)
        cls._register_attribute(username)
        cls._register_attribute(port)
        cls._register_attribute(home)
        cls._register_attribute(identity)
        cls._register_attribute(server_key)
        cls._register_attribute(clean_home)
        cls._register_attribute(clean_experiment)
        cls._register_attribute(clean_processes)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(LinuxNode, self).__init__(ec, guid)
        self._os = None
        # home directory at Linux host
        self._home_dir = ""
        
        # lock to avoid concurrency issues on methods used by applications 
        self._lock = threading.Lock()
    
    def log_message(self, msg):
        return " guid %d - host %s - %s " % (self.guid, 
                self.get("hostname"), msg)

    @property
    def home_dir(self):
        home = self.get("home") or ""
        if not home.startswith("/"):
           home = os.path.join(self._home_dir, home) 
        return home

    @property
    def usr_dir(self):
        return os.path.join(self.home_dir, "nepi-usr")

    @property
    def lib_dir(self):
        return os.path.join(self.usr_dir, "lib")

    @property
    def bin_dir(self):
        return os.path.join(self.usr_dir, "bin")

    @property
    def src_dir(self):
        return os.path.join(self.usr_dir, "src")

    @property
    def share_dir(self):
        return os.path.join(self.usr_dir, "share")

    @property
    def exp_dir(self):
        return os.path.join(self.home_dir, "nepi-exp")

    @property
    def exp_home(self):
        return os.path.join(self.exp_dir, self.ec.exp_id)

    @property
    def node_home(self):
        return os.path.join(self.exp_home, "node-%d" % self.guid)

    @property
    def run_home(self):
        return os.path.join(self.node_home, self.ec.run_id)

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

        if out.find("Fedora release 8") == 0:
            self._os = OSType.FEDORA_8
        elif out.find("Fedora release 12") == 0:
            self._os = OSType.FEDORA_12
        elif out.find("Fedora release 14") == 0:
            self._os = OSType.FEDORA_14
        elif out.find("Debian") == 0: 
            self._os = OSType.DEBIAN
        elif out.find("Ubuntu") ==0:
            self._os = OSType.UBUNTU
        else:
            msg = "Unsupported OS"
            self.error(msg, out)
            raise RuntimeError, "%s - %s " %( msg, out )

        return self._os

    @property
    def use_deb(self):
        return self.os in [OSType.DEBIAN, OSType.UBUNTU]

    @property
    def use_rpm(self):
        return self.os in [OSType.FEDORA_12, OSType.FEDORA_14, OSType.FEDORA_8,
                OSType.FEDORA]

    @property
    def localhost(self):
        return self.get("hostname") in ['localhost', '127.0.0.7', '::1']

    def provision(self):
        # check if host is alive
        if not self.is_alive():
            self.fail()
            
            msg = "Deploy failed. Unresponsive node %s" % self.get("hostname")
            self.error(msg)
            raise RuntimeError, msg

        self.find_home()

        if self.get("cleanProcesses"):
            self.clean_processes()

        if self.get("cleanHome"):
            self.clean_home()
 
        if self.get("cleanExperiment"):
            self.clean_experiment()
    
        # Create shared directory structure
        self.mkdir(self.lib_dir)
        self.mkdir(self.bin_dir)
        self.mkdir(self.src_dir)
        self.mkdir(self.share_dir)

        # Create experiment node home directory
        self.mkdir(self.node_home)

        super(LinuxNode, self).provision()

    def deploy(self):
        if self.state == ResourceState.NEW:
            try:
                self.discover()
                self.provision()
            except:
                self._state = ResourceState.FAILED
                raise

        # Node needs to wait until all associated interfaces are 
        # ready before it can finalize deployment
        from nepi.resources.linux.interface import LinuxInterface
        ifaces = self.get_connected(LinuxInterface.rtype())
        for iface in ifaces:
            if iface.state < ResourceState.READY:
                self.ec.schedule(reschedule_delay, self.deploy)
                return 

        super(LinuxNode, self).deploy()

    def release(self):
        tear_down = self.get("tearDown")
        if tear_down:
            self.execute(tear_down)

        self.clean_processes()

        super(LinuxNode, self).release()

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

    def clean_processes(self, killer = False):
        self.info("Cleaning up processes")
        
        if killer:
            # Hardcore kill
            cmd = ("sudo -S killall python tcpdump || /bin/true ; " +
                "sudo -S killall python tcpdump || /bin/true ; " +
                "sudo -S kill $(ps -N -T -o pid --no-heading | grep -v $PPID | sort) || /bin/true ; " +
                "sudo -S killall -u root || /bin/true ; " +
                "sudo -S killall -u root || /bin/true ; ")
        else:
            # Be gentler...
            cmd = ("sudo -S killall tcpdump || /bin/true ; " +
                "sudo -S killall tcpdump || /bin/true ; " +
                "sudo -S killall -u %s || /bin/true ; " % self.get("username") +
                "sudo -S killall -u %s || /bin/true ; " % self.get("username"))

        out = err = ""
        (out, err), proc = self.execute(cmd, retry = 1, with_lock = True) 
            
    def clean_home(self):
        """ Cleans all NEPI related folders in the Linux host
        """
        self.info("Cleaning up home")
        
        cmd = "cd %s ; find . -maxdepth 1 \( -name 'nepi-usr' -o -name 'nepi-exp' \) -execdir rm -rf {} + " % (
                self.home_dir )

        return self.execute(cmd, with_lock = True)

    def clean_experiment(self):
        """ Cleans all experiment related files in the Linux host.
        It preserves NEPI files and folders that have a multi experiment
        scope.
        """
        self.info("Cleaning up experiment files")
        
        cmd = "cd %s ; find . -maxdepth 1 -name '%s' -execdir rm -rf {} + " % (
                self.exp_dir,
                self.ec.exp_id )
            
        return self.execute(cmd, with_lock = True)

    def execute(self, command,
            sudo = False,
            stdin = None, 
            env = None,
            tty = False,
            forward_x11 = False,
            timeout = None,
            retry = 3,
            err_on_timeout = True,
            connect_timeout = 30,
            strict_host_checking = False,
            persistent = True,
            blocking = True,
            with_lock = False
            ):
        """ Notice that this invocation will block until the
        execution finishes. If this is not the desired behavior,
        use 'run' instead."""

        if self.localhost:
            (out, err), proc = execfuncs.lexec(command, 
                    user = user,
                    sudo = sudo,
                    stdin = stdin,
                    env = env)
        else:
            if with_lock:
                with self._lock:
                    (out, err), proc = sshfuncs.rexec(
                        command, 
                        host = self.get("hostname"),
                        user = self.get("username"),
                        port = self.get("port"),
                        agent = True,
                        sudo = sudo,
                        stdin = stdin,
                        identity = self.get("identity"),
                        server_key = self.get("serverKey"),
                        env = env,
                        tty = tty,
                        forward_x11 = forward_x11,
                        timeout = timeout,
                        retry = retry,
                        err_on_timeout = err_on_timeout,
                        connect_timeout = connect_timeout,
                        persistent = persistent,
                        blocking = blocking, 
                        strict_host_checking = strict_host_checking
                        )
            else:
                (out, err), proc = sshfuncs.rexec(
                    command, 
                    host = self.get("hostname"),
                    user = self.get("username"),
                    port = self.get("port"),
                    agent = True,
                    sudo = sudo,
                    stdin = stdin,
                    identity = self.get("identity"),
                    server_key = self.get("serverKey"),
                    env = env,
                    tty = tty,
                    forward_x11 = forward_x11,
                    timeout = timeout,
                    retry = retry,
                    err_on_timeout = err_on_timeout,
                    connect_timeout = connect_timeout,
                    persistent = persistent,
                    blocking = blocking, 
                    strict_host_checking = strict_host_checking
                    )

        return (out, err), proc

    def run(self, command, home,
            create_home = False,
            pidfile = 'pidfile',
            stdin = None, 
            stdout = 'stdout', 
            stderr = 'stderr', 
            sudo = False,
            tty = False):
        
        self.debug("Running command '%s'" % command)
        
        if self.localhost:
            (out, err), proc = execfuncs.lspawn(command, pidfile, 
                    stdout = stdout, 
                    stderr = stderr, 
                    stdin = stdin, 
                    home = home, 
                    create_home = create_home, 
                    sudo = sudo,
                    user = user) 
        else:
            with self._lock:
                (out, err), proc = sshfuncs.rspawn(
                    command,
                    pidfile = pidfile,
                    home = home,
                    create_home = create_home,
                    stdin = stdin if stdin is not None else '/dev/null',
                    stdout = stdout if stdout else '/dev/null',
                    stderr = stderr if stderr else '/dev/null',
                    sudo = sudo,
                    host = self.get("hostname"),
                    user = self.get("username"),
                    port = self.get("port"),
                    agent = True,
                    identity = self.get("identity"),
                    server_key = self.get("serverKey"),
                    tty = tty
                    )

        return (out, err), proc

    def getpid(self, home, pidfile = "pidfile"):
        if self.localhost:
            pidtuple =  execfuncs.lgetpid(os.path.join(home, pidfile))
        else:
            with self._lock:
                pidtuple = sshfuncs.rgetpid(
                    os.path.join(home, pidfile),
                    host = self.get("hostname"),
                    user = self.get("username"),
                    port = self.get("port"),
                    agent = True,
                    identity = self.get("identity"),
                    server_key = self.get("serverKey")
                    )
        
        return pidtuple

    def status(self, pid, ppid):
        if self.localhost:
            status = execfuncs.lstatus(pid, ppid)
        else:
            with self._lock:
                status = sshfuncs.rstatus(
                        pid, ppid,
                        host = self.get("hostname"),
                        user = self.get("username"),
                        port = self.get("port"),
                        agent = True,
                        identity = self.get("identity"),
                        server_key = self.get("serverKey")
                        )
           
        return status
    
    def kill(self, pid, ppid, sudo = False):
        out = err = ""
        proc = None
        status = self.status(pid, ppid)

        if status == sshfuncs.ProcStatus.RUNNING:
            if self.localhost:
                (out, err), proc = execfuncs.lkill(pid, ppid, sudo)
            else:
                with self._lock:
                    (out, err), proc = sshfuncs.rkill(
                        pid, ppid,
                        host = self.get("hostname"),
                        user = self.get("username"),
                        port = self.get("port"),
                        agent = True,
                        sudo = sudo,
                        identity = self.get("identity"),
                        server_key = self.get("serverKey")
                        )

        return (out, err), proc

    def copy(self, src, dst):
        if self.localhost:
            (out, err), proc = execfuncs.lcopy(source, dest, 
                    recursive = True,
                    strict_host_checking = False)
        else:
            with self._lock:
                (out, err), proc = sshfuncs.rcopy(
                    src, dst, 
                    port = self.get("port"),
                    identity = self.get("identity"),
                    server_key = self.get("serverKey"),
                    recursive = True,
                    strict_host_checking = False)

        return (out, err), proc


    def upload(self, src, dst, text = False, overwrite = True):
        """ Copy content to destination

           src  content to copy. Can be a local file, directory or a list of files

           dst  destination path on the remote host (remote is always self.host)

           text src is text input, it must be stored into a temp file before uploading
        """
        # If source is a string input 
        f = None
        if text and not os.path.isfile(src):
            # src is text input that should be uploaded as file
            # create a temporal file with the content to upload
            f = tempfile.NamedTemporaryFile(delete=False)
            f.write(src)
            f.close()
            src = f.name

        # If dst files should not be overwritten, check that the files do not
        # exits already 
        if overwrite == False:
            src = self.filter_existing_files(src, dst)
            if not src:
                return ("", ""), None 

        if not self.localhost:
            # Build destination as <user>@<server>:<path>
            dst = "%s@%s:%s" % (self.get("username"), self.get("hostname"), dst)

        result = self.copy(src, dst)

        # clean up temp file
        if f:
            os.remove(f.name)

        return result

    def download(self, src, dst):
        if not self.localhost:
            # Build destination as <user>@<server>:<path>
            src = "%s@%s:%s" % (self.get("username"), self.get("hostname"), src)
        return self.copy(src, dst)

    def install_packages(self, packages, home, run_home = None):
        """ Install packages in the Linux host.

        'home' is the directory to upload the package installation script.
        'run_home' is the directory from where to execute the script.
        """
        command = ""
        if self.use_rpm:
            command = rpmfuncs.install_packages_command(self.os, packages)
        elif self.use_deb:
            command = debfuncs.install_packages_command(self.os, packages)
        else:
            msg = "Error installing packages ( OS not known ) "
            self.error(msg, self.os)
            raise RuntimeError, msg

        run_home = run_home or home

        (out, err), proc = self.run_and_wait(command, run_home, 
            shfile = os.path.join(home, "instpkg.sh"),
            pidfile = "instpkg_pidfile",
            ecodefile = "instpkg_exitcode",
            stdout = "instpkg_stdout", 
            stderr = "instpkg_stderr",
            overwrite = False,
            raise_on_error = True)

        return (out, err), proc 

    def remove_packages(self, packages, home, run_home = None):
        """ Uninstall packages from the Linux host.

        'home' is the directory to upload the package un-installation script.
        'run_home' is the directory from where to execute the script.
        """
        if self.use_rpm:
            command = rpmfuncs.remove_packages_command(self.os, packages)
        elif self.use_deb:
            command = debfuncs.remove_packages_command(self.os, packages)
        else:
            msg = "Error removing packages ( OS not known ) "
            self.error(msg)
            raise RuntimeError, msg

        run_home = run_home or home

        (out, err), proc = self.run_and_wait(command, run_home, 
            shfile = os.path.join(home, "rmpkg.sh"),
            pidfile = "rmpkg_pidfile",
            ecodefile = "rmpkg_exitcode",
            stdout = "rmpkg_stdout", 
            stderr = "rmpkg_stderr",
            overwrite = False,
            raise_on_error = True)
         
        return (out, err), proc 

    def mkdir(self, path, clean = False):
        if clean:
            self.rmdir(path)

        return self.execute("mkdir -p %s" % path, with_lock = True)

    def rmdir(self, path):
        return self.execute("rm -rf %s" % path, with_lock = True)
        
    def run_and_wait(self, command, home, 
            shfile = "cmd.sh",
            env = None,
            overwrite = True,
            pidfile = "pidfile", 
            ecodefile = "exitcode", 
            stdin = None, 
            stdout = "stdout", 
            stderr = "stderr", 
            sudo = False,
            tty = False,
            raise_on_error = False):
        """
        Uploads the 'command' to a bash script in the host.
        Then runs the script detached in background in the host, and
        busy-waites until the script finishes executing.
        """

        if not shfile.startswith("/"):
            shfile = os.path.join(home, shfile)

        self.upload_command(command, 
            shfile = shfile, 
            ecodefile = ecodefile, 
            env = env,
            overwrite = overwrite)

        command = "bash %s" % shfile
        # run command in background in remote host
        (out, err), proc = self.run(command, home, 
                pidfile = pidfile,
                stdin = stdin, 
                stdout = stdout, 
                stderr = stderr, 
                sudo = sudo,
                tty = tty)

        # check no errors occurred
        if proc.poll():
            msg = " Failed to run command '%s' " % command
            self.error(msg, out, err)
            if raise_on_error:
                raise RuntimeError, msg

        # Wait for pid file to be generated
        pid, ppid = self.wait_pid(
                home = home, 
                pidfile = pidfile, 
                raise_on_error = raise_on_error)

        # wait until command finishes to execute
        self.wait_run(pid, ppid)
      
        (out, err), proc = self.check_errors(home,
            ecodefile = ecodefile,
            stdout = stdout,
            stderr= stderr)

        # Out is what was written in the stderr file
        if err:
            msg = " Failed to run command '%s' " % command
            self.error(msg, out, err)

            if raise_on_error:
                raise RuntimeError, msg
        
        return (out, err), proc

    def exitcode(self, home, ecodefile = "exitcode"):
        """
        Get the exit code of an application.
        Returns an integer value with the exit code 
        """
        (out, err), proc = self.check_output(home, ecodefile)

        # Succeeded to open file, return exit code in the file
        if proc.wait() == 0:
            try:
                return int(out.strip())
            except:
                # Error in the content of the file!
                return ExitCode.CORRUPTFILE

        # No such file or directory
        if proc.returncode == 1:
            return ExitCode.FILENOTFOUND
        
        # Other error from 'cat'
        return ExitCode.ERROR

    def upload_command(self, command, 
            shfile = "cmd.sh",
            ecodefile = "exitcode",
            overwrite = True,
            env = None):
        """ Saves the command as a bash script file in the remote host, and
        forces to save the exit code of the command execution to the ecodefile
        """

        if not (command.strip().endswith(";") or command.strip().endswith("&")):
            command += ";"
      
        # The exit code of the command will be stored in ecodefile
        command = " { %(command)s } ; echo $? > %(ecodefile)s ;" % {
                'command': command,
                'ecodefile': ecodefile,
                } 

        # Export environment
        environ = self.format_environment(env)

        # Add environ to command
        command = environ + command

        return self.upload(command, shfile, text = True, overwrite = overwrite)

    def format_environment(self, env, inline = False):
        """Format environmental variables for command to be executed either
        as an inline command
        (i.e. export PYTHONPATH=src/..; export LALAL= ..;python script.py) or 
        as a bash script (i.e. export PYTHONPATH=src/.. \n export LALA=.. \n)
        """
        if not env: return ""

        # Remove extra white spaces
        env = re.sub(r'\s+', ' ', env.strip())

        sep = ";" if inline else "\n"
        return sep.join(map(lambda e: " export %s" % e, env.split(" "))) + sep 

    def check_errors(self, home, 
            ecodefile = "exitcode", 
            stdout = "stdout",
            stderr = "stderr"):
        """
        Checks whether errors occurred while running a command.
        It first checks the exit code for the command, and only if the
        exit code is an error one it returns the error output.

        """
        proc = None
        err = ""
        # retrive standard output from the file
        (out, oerr), oproc = self.check_output(home, stdout)

        # get exit code saved in the 'exitcode' file
        ecode = self.exitcode(home, ecodefile)

        if ecode in [ ExitCode.CORRUPTFILE, ExitCode.ERROR ]:
            err = "Error retrieving exit code status from file %s/%s" % (home, ecodefile)
        elif ecode > 0 or ecode == ExitCode.FILENOTFOUND:
            # The process returned an error code or didn't exist. 
            # Check standard error.
            (err, eerr), proc = self.check_output(home, stderr)

            # If the stderr file was not found, assume nothing bad happened,
            # and just ignore the error.
            # (cat returns 1 for error "No such file or directory")
            if ecode == ExitCode.FILENOTFOUND and proc.poll() == 1: 
                err = "" 
            
        return (out, err), proc
 
    def wait_pid(self, home, pidfile = "pidfile", raise_on_error = False):
        """ Waits until the pid file for the command is generated, 
            and returns the pid and ppid of the process """
        pid = ppid = None
        delay = 1.0

        for i in xrange(4):
            pidtuple = self.getpid(home = home, pidfile = pidfile)
            
            if pidtuple:
                pid, ppid = pidtuple
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = " Failed to get pid for pidfile %s/%s " % (
                    home, pidfile )
            self.error(msg)
            
            if raise_on_error:
                raise RuntimeError, msg

        return pid, ppid

    def wait_run(self, pid, ppid, trial = 0):
        """ wait for a remote process to finish execution """
        start_delay = 1.0

        while True:
            status = self.status(pid, ppid)
            
            if status is ProcStatus.FINISHED:
                break
            elif status is not ProcStatus.RUNNING:
                delay = delay * 1.5
                time.sleep(delay)
                # If it takes more than 20 seconds to start, then
                # asume something went wrong
                if delay > 20:
                    break
            else:
                # The app is running, just wait...
                time.sleep(0.5)

    def check_output(self, home, filename):
        """ Retrives content of file """
        (out, err), proc = self.execute("cat %s" % 
            os.path.join(home, filename), retry = 1, with_lock = True)
        return (out, err), proc

    def is_alive(self):
        """ Checks if host is responsive
        """
        if self.localhost:
            return True

        out = err = ""
        try:
            (out, err), proc = self.execute("echo 'ALIVE'",
                    retry = 5, 
                    with_lock = True)
        except:
            trace = traceback.format_exc()
            msg = "Unresponsive host  %s " % err
            self.error(msg, out, trace)
            return False

        if out.strip() == "ALIVE":
            return True
        else:
            msg = "Unresponsive host "
            self.error(msg, out, err)
            return False

    def find_home(self):
        """ Retrieves host home directory
        """
        (out, err), proc = self.execute("echo ${HOME}", retry = 5, 
                    with_lock = True)

        if proc.poll():
            msg = "Imposible to retrieve HOME directory"
            self.error(msg, out, err)
            raise RuntimeError, msg

        self._home_dir =  out.strip()

    def filter_existing_files(self, src, dst):
        """ Removes files that already exist in the Linux host from src list
        """
        # construct a dictionary with { dst: src }
        dests = dict(map(lambda x: ( os.path.join(dst, os.path.basename(x) ),  x ), 
            src.strip().split(" ") ) ) if src.strip().find(" ") != -1 else dict({dst: src})

        command = []
        for d in dests.keys():
            command.append(" [ -f %(dst)s ] && echo '%(dst)s' " % {'dst' : d} )

        command = ";".join(command)

        (out, err), proc = self.execute(command, retry = 1, with_lock = True)
    
        for d in dests.keys():
            if out.find(d) > -1:
                del dests[d]

        if not dests:
            return ""

        return " ".join(dests.values())

