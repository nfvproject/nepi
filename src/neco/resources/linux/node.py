from neco.execution.attribute import Attribute, Flags
from neco.execution.resource import ResourceManager, clsinit, ResourceState
from neco.resources.linux import rpmfuncs, debfuncs 
from neco.util import sshfuncs, execfuncs 

import collections
import logging
import os
import random
import re
import tempfile
import time
import threading

# TODO: Verify files and dirs exists already

@clsinit
class LinuxNode(ResourceManager):
    _rtype = "LinuxNode"

    @classmethod
    def _register_attributes(cls):
        hostname = Attribute("hostname", "Hostname of the machine")

        username = Attribute("username", "Local account username", 
                flags = Flags.Credential)

        port = Attribute("port", "SSH port", flags = Flags.Credential)
        
        home = Attribute("home", 
                "Experiment home directory to store all experiment related files")
        
        identity = Attribute("identity", "SSH identity file",
                flags = Flags.Credential)
        
        server_key = Attribute("serverKey", "Server public key", 
                flags = Flags.Credential)
        
        clean_home = Attribute("cleanHome", "Remove all files and directories " + \
                " from home folder before starting experiment", 
                flags = Flags.ReadOnly)
        
        clean_processes = Attribute("cleanProcesses", 
                "Kill all running processes before starting experiment", 
                flags = Flags.ReadOnly)
        
        tear_down = Attribute("tearDown", "Bash script to be executed before " + \
                "releasing the resource", flags = Flags.ReadOnly)

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
        self._home = "nepi-exp-%s" % os.urandom(8).encode('hex')
        
        # lock to avoid concurrency issues on methods used by applications 
        self._lock = threading.Lock()

        self._logger = logging.getLogger("neco.linux.Node.%d " % self.guid)

    @property
    def home(self):
        home = self.get("home")
        if home and not home.startswith("nepi-"):
            home = "nepi-" + home
        return home or self._home

    @property
    def os(self):
        if self._os:
            return self._os

        if (not self.get("hostname") or not self.get("username")):
            msg = "Can't resolve OS for guid %d. Insufficient data." % self.guid
            self.logger.error(msg)
            raise RuntimeError, msg

        (out, err), proc = self.execute("cat /etc/issue")

        if err and proc.poll():
            msg = "Error detecting OS for host %s. err: %s " % (self.get("hostname"), err)
            self.logger.error(msg)
            raise RuntimeError, msg

        if out.find("Fedora release 12") == 0:
            self._os = "f12"
        elif out.find("Fedora release 14") == 0:
            self._os = "f14"
        elif out.find("Debian") == 0: 
            self._os = "debian"
        elif out.find("Ubuntu") ==0:
            self._os = "ubuntu"
        else:
            msg = "Unsupported OS %s for host %s" % (out, self.get("hostname"))
            self.logger.error(msg)
            raise RuntimeError, msg

        return self._os

    @property
    def localhost(self):
        return self.get("hostname") in ['localhost', '127.0.0.7', '::1']

    def provision(self, filters = None):
        if not self.is_alive():
            self._state = ResourceState.FAILED
            self.logger.error("Deploy failed. Unresponsive node")
            return

    def deploy(self):
        self.provision()

        if self.get("cleanProcesses"):
            self.clean_processes()

        if self.get("cleanHome"):
            # self.clean_home() -> this is dangerous
            pass

        self.mkdir(self.home)

        super(LinuxNode, self).deploy()

    def release(self):
        tear_down = self.get("tearDown")
        if tear_down:
            self.execute(tear_down)

        super(LinuxNode, self).release()

    def validate_connection(self, guid):
        # TODO: Validate!
        return True

    def clean_processes(self):
        self.logger.info("Cleaning up processes")
        
        cmd = ("sudo -S killall python tcpdump || /bin/true ; " +
            "sudo -S killall python tcpdump || /bin/true ; " +
            "sudo -S kill $(ps -N -T -o pid --no-heading | grep -v $PPID | sort) || /bin/true ; " +
            "sudo -S killall -u root || /bin/true ; " +
            "sudo -S killall -u root || /bin/true ; ")

        out = err = ""
        with self._lock:
           (out, err), proc = self.run_and_wait(cmd, self.home, 
                pidfile = "cppid",
                stdout = "cplog", 
                stderr = "cperr", 
                raise_on_error = True)

        return (out, err)   
            
    def clean_home(self):
        self.logger.info("Cleaning up home")

        cmd = "find . -maxdepth 1  \( -name '.cache' -o -name '.local' -o -name '.config' -o -name 'nepi-*' \) -execdir rm -rf {} + "

        out = err = ""
        with self._lock:
            (out, err), proc = self.run_and_wait(cmd, self.home,
                pidfile = "chpid",
                stdout = "chlog", 
                stderr = "cherr", 
                raise_on_error = True)
        
        return (out, err)   

    def upload(self, src, dst):
        """ Copy content to destination

           src  content to copy. Can be a local file, directory or text input

           dst  destination path on the remote host (remote is always self.host)
        """
        # If source is a string input 
        if not os.path.isfile(src):
            # src is text input that should be uploaded as file
            # create a temporal file with the content to upload
            f = tempfile.NamedTemporaryFile(delete=False)
            f.write(src)
            f.close()
            src = f.name

        if not self.localhost:
            # Build destination as <user>@<server>:<path>
            dst = "%s@%s:%s" % (self.get("username"), self.get("hostname"), dst)

        return self.copy(src, dst)

    def download(self, src, dst):
        if not self.localhost:
            # Build destination as <user>@<server>:<path>
            src = "%s@%s:%s" % (self.get("username"), self.get("hostname"), src)
        return self.copy(src, dst)

    def install_packages(self, packages):
        cmd = ""
        if self.os in ["f12", "f14"]:
            cmd = rpmfuncs.install_packages_command(self.os, packages)
        elif self.os in ["debian", "ubuntu"]:
            cmd = debfuncs.install_packages_command(self.os, packages)
        else:
            msg = "Error installing packages. OS not known for host %s " % (
                    self.get("hostname"))
            self.logger.error(msg)
            raise RuntimeError, msg

        out = err = ""
        with self._lock:
            (out, err), proc = self.run_and_wait(cmd, self.home, 
                pidfile = "instpkgpid",
                stdout = "instpkglog", 
                stderr = "instpkgerr", 
                raise_on_error = True)

        return (out, err), proc 

    def remove_packages(self, packages):
        cmd = ""
        if self.os in ["f12", "f14"]:
            cmd = rpmfuncs.remove_packages_command(self.os, packages)
        elif self.os in ["debian", "ubuntu"]:
            cmd = debfuncs.remove_packages_command(self.os, packages)
        else:
            msg = "Error removing packages. OS not known for host %s " % (
                    self.get("hostname"))
            self.logger.error(msg)
            raise RuntimeError, msg

        out = err = ""
        with self._lock:
            (out, err), proc = self.run_and_wait(cmd, self.home, 
                pidfile = "rmpkgpid",
                stdout = "rmpkglog", 
                stderr = "rmpkgerr", 
                raise_on_error = True)
         
        return (out, err), proc 

    def mkdir(self, path, clean = False):
        if clean:
            self.rmdir(path)

        return self.execute("mkdir -p %s" % path)

    def rmdir(self, path):
        return self.execute("rm -rf %s" % path)

    def run_and_wait(self, command, 
            home = ".", 
            pidfile = "pid", 
            stdin = None, 
            stdout = 'stdout', 
            stderr = 'stderr', 
            sudo = False,
            raise_on_error = False):

        (out, err), proc = self.run(command, home, 
                pidfile = pidfile,
                stdin = stdin, 
                stdout = stdout, 
                stderr = stderr, 
                sudo = sudo)

        if proc.poll() and err:
            msg = " Failed to run command %s on host %s" % (
                    command, self.get("hostname"))
            self.logger.error(msg)
            if raise_on_error:
                raise RuntimeError, msg
        
        pid, ppid = self.wait_pid(
                home = home, 
                pidfile = pidfile, 
                raise_on_error = raise_on_error)

        self.wait_run(pid, ppid)
        
        (out, err), proc = self.check_run_error(home, stderr)

        if err or out:
            msg = "Error while running command %s on host %s. error output: %s" % (
                    command, self.get("hostname"), out)
            if err:
                msg += " . err: %s" % err

            self.logger.error(msg)
            if raise_on_error:
                raise RuntimeError, msg
        
        return (out, err), proc
 
    def wait_pid(self, home = ".", pidfile = "pid", raise_on_error = False):
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
            msg = " Failed to get pid for pidfile %s/%s on host %s" % (
                    home, pidfile, self.get("hostname"))
            self.logger.error(msg)
            if raise_on_error:
                raise RuntimeError, msg

        return pid, ppid

    def wait_run(self, pid, ppid, trial = 0):
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

    def check_run_error(self, home, stderr = 'stderr'):
        (out, err), proc = self.execute("cat %s" % 
                os.path.join(home, stderr))
        return (out, err), proc

    def check_run_output(self, home, stdout = 'stdout'):
        (out, err), proc = self.execute("cat %s" % 
                os.path.join(home, stdout))
        return (out, err), proc

    def is_alive(self):
        if self.localhost:
            return True

        out = err = ""
        try:
            (out, err), proc = self.execute("echo 'ALIVE'")
        except:
            import traceback
            trace = traceback.format_exc()
            self.logger.warn("Unresponsive host %s. got:\n out: %s err: %s\n traceback: %s", 
                    self.get("hostname"), out, err, trace)
            return False

        if out.strip().startswith('ALIVE'):
            return True
        else:
            self.logger.warn("Unresponsive host %s. got:\n%s%s", 
                    self.get("hostname"), out, err)
            return False

            # TODO!
            #if self.check_bad_host(out,err):
            #    self.blacklist()

    def copy(self, src, dst):
        if self.localhost:
            (out, err), proc =  execfuncs.lcopy(source, dest, 
                    recursive = True)
        else:
            (out, err), proc = self.safe_retry(sshfuncs.rcopy)(
                src, dst, 
                port = self.get("port"),
                identity = self.get("identity"),
                server_key = self.get("serverKey"),
                recursive = True)

        return (out, err), proc

    def execute(self, command,
            sudo = False,
            stdin = None, 
            env = None,
            tty = False,
            forward_x11 = False,
            timeout = None,
            retry = 0,
            err_on_timeout = True,
            connect_timeout = 30,
            persistent = True
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
            (out, err), proc = self.safe_retry(sshfuncs.rexec)(
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
            create_home = True,
            pidfile = "pid",
            stdin = None, 
            stdout = 'stdout', 
            stderr = 'stderr', 
            sudo = False):

        self.logger.info("Running %s", command)
        
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
            (out,err), proc = self.safe_retry(sshfuncs.rspawn)(
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
                server_key = self.get("serverKey")
                )

        return (out, err), proc

    def checkpid(self, home = ".", pidfile = "pid"):
        if self.localhost:
            pidtuple =  execfuncs.lcheckpid(os.path.join(home, pidfile))
        else:
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
                (out, err), proc = self.safe_retry(sshfuncs.rkill)(
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

    def blacklist(self):
        # TODO!!!!
        self.logger.warn("Blacklisting malfunctioning node %s", self.hostname)
        #import util
        #util.appendBlacklist(self.hostname)

    def safe_retry(self, func):
        """Retries a function invocation using a lock"""
        import functools
        @functools.wraps(func)
        def rv(*p, **kw):
            fail_msg = " Failed to execute function %s(%s, %s) at host %s" % (
                func.__name__, p, kw, self.get("hostname"))
            retry = kw.pop("_retry", False)
            wlock = kw.pop("_with_lock", False)

            out = err = ""
            proc = None
            for i in xrange(0 if retry else 4):
                try:
                    if wlock:
                        with self._lock:
                            (out, err), proc = func(*p, **kw)
                    else:
                        (out, err), proc = func(*p, **kw)
                        
                    if proc.poll():
                        if retry:
                            time.sleep(i*15)
                            continue
                        else:
                            self.logger.error("%s. out: %s error: %s", fail_msg, out, err)
                    break
                except RuntimeError, e:
                    if x >= 3:
                        self.logger.error("%s. error: %s", fail_msg, e.args)
            return (out, err), proc

        return rv

