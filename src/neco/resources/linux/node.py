from neco.execution.resource import Resource
from neco.util.sshfuncs import eintr_retry, rexec, rcopy, \
        rspawn, rcheck_pid, rstatus, rkill, make_control_path, RUNNING 

import cStringIO
import logging
import os.path

class LinuxNode(Resource):
    def __init__(self, box, ec):
        super(LinuxNode, self).__init__(box, ec)
        self.ip = None
        self.host = None
        self.user = None
        self.port = None
        self.identity_file = None
        self.enable_x11 = False
        self.forward_agent = True

        # packet management system - either yum or apt for now...
        self._pm = None
       
        # Logging
        loglevel = "debug"
        self._logger = logging.getLogger("neco.resources.base.LinuxNode.%s" %\
                self.box.guid)
        self._logger.setLevel(getattr(logging, loglevel.upper()))

        # For ssh connections we use the ControlMaster option which 
        # allows us to decrease the number of open ssh network connections.
        # Subsequent ssh connections will reuse a same master connection.
        # This might pose a problem when using X11 and ssh-agent, since
        # display and agent forwarded will be those of the first connection,
        # which created the master. 
        # To avoid reusing a master created by a previous LinuxNode instance,
        # we explicitly erase the ControlPath socket.
        control_path = make_control_path(self.user, self.host, self.port)
        try:
            os.remove(control_path)
        except:
            pass

    @property
    def pm(self):
        if self._pm:
            return self._pm

        if (not (self.host or self.ip) or not self.user):
            msg = "Can't resolve package management system. Insufficient data."
            self._logger.error(msg)
            raise RuntimeError(msg)

        out = self.execute("cat /etc/issue")

        if out.find("Fedora") == 0:
            self._pm = "yum"
        elif out.find("Debian") == 0 or out.find("Ubuntu") ==0:
            self._pm = "apt-get"
        else:
            msg = "Can't resolve package management system. Unknown OS."
            self._logger.error(msg)
            raise RuntimeError(msg)

        return self._pm

    def install(self, packages):
        if not isinstance(packages, list):
            packages = [packages]

        for p in packages:
            self.execute("%s -y install %s" % (self.pm, p), sudo = True, 
                    tty = True)

    def uninstall(self, packages):
        if not isinstance(packages, list):
            packages = [packages]

        for p in packages:
            self.execute("%s -y remove %s" % (self.pm, p), sudo = True, 
                    tty = True)

    def upload(self, src, dst):
        if not os.path.isfile(src):
            src = cStringIO.StringIO(src)

        # Build destination as <user>@<server>:<path>
        dst = "%s@%s:%s" % (self.user, self.host or self.ip, dst)

        (out, err), proc = eintr_retry(rcopy)(
            src, dst, 
            port = self.port,
            identity_file = self.identity_file)

        if proc.wait():
            msg = "Error uploading to %s got:\n%s%s" %\
                    (self.host or self.ip, out, err)
            self._logger.error(msg)
            raise RuntimeError(msg)

    def download(self, src, dst):
        # Build destination as <user>@<server>:<path>
        src = "%s@%s:%s" % (self.user, self.host or self.ip, src)

        (out, err), proc = eintr_retry(rcopy)(
            src, dst, 
            port = self.port,
            identity_file = self.identity_file)

        if proc.wait():
            msg = "Error uploading to %s got:\n%s%s" %\
                    (self.host or self.ip, out, err)
            self._logger.error(msg)
            raise RuntimeError(msg)

    def is_alive(self, verbose = False):
        (out, err), proc = eintr_retry(rexec)(
                "echo 'ALIVE'",
                self.host or self.ip, 
                self.user,
                port = self.port, 
                agent = self.forward_agent,
                identity_file = self.identity_file,
                x11 = self.enable_x11,
                timeout = 60,
                err_on_timeout = False,
                persistent = False)
        
        if proc.wait():
            if verbose:
                self._logger.warn("Unresponsive node %s got:\n%s%s", self.host, out, err)
            return False
        elif out.strip().startswith('ALIVE'):
            return True
        else:
            if verbose:
                self._logger.warn("Unresponsive node %s got:\n%s%s", self.host, out, err)
            return False

    def mkdir(self, path, clean = True):
        if clean:
            self.rmdir(path)

        self.execute(
            "mkdir -p %s" % path,
            timeout = 120,
            retry = 3
            )

    def rmdir(self, path):
        self.execute(
            "rm -rf %s" % path,
            timeout = 120,
            retry = 3
            )

    def execute(self, command,
            sudo = False,
            stdin = "", 
            tty = False,
            env = None,
            timeout = None,
            retry = 0,
            err_on_timeout = True,
            connect_timeout = 30,
            persistent = True):
        """ Notice that this invocation will block until the
        execution finishes. If this is not the desired behavior,
        use 'run' instead."""
        (out, err), proc = eintr_retry(rexec)(
                command, 
                self.host or self.ip, 
                self.user,
                port = self.port, 
                agent = self.forward_agent,
                sudo = sudo,
                stdin = stdin, 
                identity_file = self.identity_file,
                tty = tty,
                x11 = self.enable_x11,
                env = env,
                timeout = timeout,
                retry = retry,
                err_on_timeout = err_on_timeout,
                connect_timeout = connect_timeout,
                persistent = persistent)

        if proc.wait():
            msg = "Failed to execute command %s at node %s: %s %s" % \
                    (command, self.host or self.ip, out, err,)
            self._logger.warn(msg)
            raise RuntimeError(msg)

        return out

    def run(self, command, home, 
            stdin = None, 
            stdout = 'stdout', 
            stderr = 'stderr', 
            sudo = False):
        self._logger.info("Running %s", command)

        # Start process in a "daemonized" way, using nohup and heavy
        # stdin/out redirection to avoid connection issues
        (out,err), proc = rspawn(
            command,
            pidfile = './pid',
            home = home,
            stdin = stdin if stdin is not None else '/dev/null',
            stdout = stdout if stdout else '/dev/null',
            stderr = stderr if stderr else '/dev/null',
            sudo = sudo,
            host = self.host,
            user = self.user,
            port = self.port,
            agent = self.forward_agent,
            identity_file = self.identity_file
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)
    
    def checkpid(self, path):            
        # Get PID/PPID
        # NOTE: wait a bit for the pidfile to be created
        pidtuple = rcheck_pid(
            os.path.join(path, 'pid'),
            host = self.host,
            user = self.user,
            port = self.port,
            agent = self.forward_agent,
            identity_file = self.identity_file
            )
        
        return pidtuple
    
    def status(self, pid, ppid):
        status = rstatus(
                pid, ppid,
                host = self.host,
                user = self.user,
                port = self.port,
                agent = self.forward_agent,
                identity_file = self.identity_file
                )
           
        return status
    
    def kill(self, pid, ppid, sudo = False):
        status = self.status(pid, ppid)
        if status == RUNNING:
            # kill by ppid+pid - SIGTERM first, then try SIGKILL
            rkill(
                pid, ppid,
                host = self.host,
                user = self.user,
                port = self.port,
                agent = self.forward_agent,
                sudo = sudo,
                identity_file = self.identity_file
                )

