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
from nepi.execution.resource import ResourceManager, clsinit, ResourceState
from nepi.resources.linux import rpmfuncs, debfuncs 
from nepi.util import sshfuncs, execfuncs 

import collections
import os
import random
import re
import tempfile
import time
import threading

# TODO: Verify files and dirs exists already
# TODO: Blacklist nodes!
# TODO: Unify delays!!
# TODO: Validate outcome of uploads!! 

reschedule_delay = "0.5s"


@clsinit
class LinuxNode(ResourceManager):
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
        
        clean_home = Attribute("cleanHome", "Remove all files and directories " + \
                " from home folder before starting experiment", 
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
        cls._register_attribute(clean_processes)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(LinuxNode, self).__init__(ec, guid)
        self._os = None
        
        # lock to avoid concurrency issues on methods used by applications 
        self._lock = threading.Lock()
    
    def log_message(self, msg):
        return " guid %d - host %s - %s " % (self.guid, 
                self.get("hostname"), msg)

    @property
    def home(self):
        return self.get("home") or ""

    @property
    def exp_home(self):
        return os.path.join(self.home, self.ec.exp_id)

    @property
    def node_home(self):
        node_home = "node-%d" % self.guid
        return os.path.join(self.exp_home, node_home)

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
        elif out.find("Debian") == 0: 
            self._os = "debian"
        elif out.find("Ubuntu") ==0:
            self._os = "ubuntu"
        else:
            msg = "Unsupported OS"
            self.error(msg, out)
            raise RuntimeError, "%s - %s " %( msg, out )

        return self._os

    @property
    def localhost(self):
        return self.get("hostname") in ['localhost', '127.0.0.7', '::1']

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
        self.info("Cleaning up home")
        
        cmd = (
            # "find . -maxdepth 1  \( -name '.cache' -o -name '.local' -o -name '.config' -o -name 'nepi-*' \)" +
            "find . -maxdepth 1 -name 'nepi-*' " +
            " -execdir rm -rf {} + "
            )
            
        if self.home:
            cmd = "cd %s ; " % self.home + cmd

        out = err = ""
        (out, err), proc = self.execute(cmd, with_lock = True)

    def upload(self, src, dst, text = False):
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

    def install_packages(self, packages, home = None):
        home = home or self.node_home

        cmd = ""
        if self.os in ["f12", "f14"]:
            cmd = rpmfuncs.install_packages_command(self.os, packages)
        elif self.os in ["debian", "ubuntu"]:
            cmd = debfuncs.install_packages_command(self.os, packages)
        else:
            msg = "Error installing packages ( OS not known ) "
            self.error(msg, self.os)
            raise RuntimeError, msg

        out = err = ""
        (out, err), proc = self.run_and_wait(cmd, home, 
            pidfile = "instpkg_pid",
            stdout = "instpkg_out", 
            stderr = "instpkg_err",
            raise_on_error = True)

        return (out, err), proc 

    def remove_packages(self, packages, home = None):
        home = home or self.node_home

        cmd = ""
        if self.os in ["f12", "f14"]:
            cmd = rpmfuncs.remove_packages_command(self.os, packages)
        elif self.os in ["debian", "ubuntu"]:
            cmd = debfuncs.remove_packages_command(self.os, packages)
        else:
            msg = "Error removing packages ( OS not known ) "
            self.error(msg)
            raise RuntimeError, msg

        out = err = ""
        (out, err), proc = self.run_and_wait(cmd, home, 
            pidfile = "rmpkg_pid",
            stdout = "rmpkg_out", 
            stderr = "rmpkg_err",
            raise_on_error = True)
         
        return (out, err), proc 

    def mkdir(self, path, clean = False):
        if clean:
            self.rmdir(path)

        return self.execute("mkdir -p %s" % path, with_lock = True)

    def rmdir(self, path):
        return self.execute("rm -rf %s" % path, with_lock = True)

    def run_and_wait(self, command, 
            home = ".", 
            pidfile = "pid", 
            stdin = None, 
            stdout = 'stdout', 
            stderr = 'stderr', 
            sudo = False,
            tty = False,
            raise_on_error = False):
        """ runs a command in background on the remote host, but waits
            until the command finishes execution.
            This is more robust than doing a simple synchronized 'execute',
            since in the remote host the command can continue to run detached
            even if network disconnections occur
        """
        # run command in background in remote host
        (out, err), proc = self.run(command, home, 
                pidfile = pidfile,
                stdin = stdin, 
                stdout = stdout, 
                stderr = stderr, 
                sudo = sudo,
                tty = tty)

        # check no errors occurred
        if proc.poll() and err:
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
       
        # check if execution errors occurred
        (out, err), proc = self.check_output(home, stderr)

        if err or out:
            msg = " Failed to run command '%s' " % command
            self.error(msg, out, err)

            if raise_on_error:
                raise RuntimeError, msg
        
        return (out, err), proc
 
    def wait_pid(self, home = ".", pidfile = "pid", raise_on_error = False):
        """ Waits until the pid file for the command is generated, 
            and returns the pid and ppid of the process """
        pid = ppid = None
        delay = 1.0
        for i in xrange(5):
            pidtuple = self.checkpid(home = home, pidfile = pidfile)
            
            if pidtuple:
                pid, ppid = pidtuple
                break
            else:
                time.sleep(delay)
                delay = min(30,delay*1.2)
        else:
            msg = " Failed to get pid for pidfile %s/%s " % (
                    home, pidfile )
            self.error(msg)
            
            if raise_on_error:
                raise RuntimeError, msg

        return pid, ppid

    def wait_run(self, pid, ppid, trial = 0):
        """ wait for a remote process to finish execution """
        delay = 1.0
        first = True
        bustspin = 0

        while True:
            status = self.status(pid, ppid)
            
            if status is sshfuncs.FINISHED:
                break
            elif status is not sshfuncs.RUNNING:
                bustspin += 1
                time.sleep(delay*(5.5+random.random()))
                if bustspin > 12:
                    break
            else:
                if first:
                    first = False

                time.sleep(delay*(0.5+random.random()))
                delay = min(30,delay*1.2)
                bustspin = 0

    def check_output(self, home, filename):
        """ checks file content """
        (out, err), proc = self.execute("cat %s" % 
            os.path.join(home, filename), retry = 1, with_lock = True)
        return (out, err), proc

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

    def copy(self, src, dst):
        if self.localhost:
            (out, err), proc =  execfuncs.lcopy(source, dest, 
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
                    persistent = persistent
                    )

        return (out, err), proc

    def run(self, command, 
            home = None,
            create_home = False,
            pidfile = "pid",
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
            # Start process in a "daemonized" way, using nohup and heavy
            # stdin/out redirection to avoid connection issues
            with self._lock:
                (out,err), proc = sshfuncs.rspawn(
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

    def checkpid(self, home = ".", pidfile = "pid"):
        if self.localhost:
            pidtuple =  execfuncs.lcheckpid(os.path.join(home, pidfile))
        else:
            with self._lock:
                pidtuple = sshfuncs.rcheckpid(
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

        if status == sshfuncs.RUNNING:
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

    def check_bad_host(self, out, err):
        badre = re.compile(r'(?:'
                           r'|Error: disk I/O error'
                           r')', 
                           re.I)
        return badre.search(out) or badre.search(err)
