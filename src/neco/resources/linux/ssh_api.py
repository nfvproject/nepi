
from neco.util.sshfuncs import eintr_retry, rexec, rcopy, rspawn, \
        rcheckpid, rstatus, rkill, RUNNING, FINISHED 

import hashlib
import logging
import os
import re
import tempfile

class SSHApi(object):
    def __init__(self, host, user, port, identity, agent, forward_x11):
        self.host = host
        self.user = user
        # ssh identity file
        self.identity = identity
        self.port = port
        # use ssh agent
        self.agent = agent
        # forward X11 
        self.forward_x11 = forward_x11

        self._pm = None
        
        self._logger = logging.getLogger("neco.linux.SSHApi")

    # TODO: Investigate using http://nixos.org/nix/
    @property
    def pm(self):
        if self._pm:
            return self._pm

        if (not self.host or not self.user):
            msg = "Can't resolve package management system. Insufficient data."
            self._logger.error(msg)
            raise RuntimeError(msg)

        out, err = self.execute("cat /etc/issue")

        if out.find("Fedora") == 0:
            self._pm = "yum"
        elif out.find("Debian") == 0 or out.find("Ubuntu") ==0:
            self._pm = "apt-get"
        else:
            msg = "Can't resolve package management system. Unknown OS."
            self._logger.error(msg)
            raise RuntimeError(msg)

        return self._pm

    @property
    def is_localhost(self):
        return self.host in ['localhost', '127.0.0.7', '::1']

    # TODO: Investigate using http://nixos.org/nix/
    def install(self, packages):
        if not isinstance(packages, list):
            packages = [packages]

        for p in packages:
            self.execute("%s -y install %s" % (self.pm, p), sudo = True, 
                    tty = True)

    # TODO: Investigate using http://nixos.org/nix/
    def uninstall(self, packages):
        if not isinstance(packages, list):
            packages = [packages]

        for p in packages:
            self.execute("%s -y remove %s" % (self.pm, p), sudo = True, 
                    tty = True)

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

        if not self.is_localhost:
            # Build destination as <user>@<server>:<path>
            dst = "%s@%s:%s" % (self.user, self.host, dst)

        ret = self.copy(src, dst)

        return ret

    def download(self, src, dst):
        if not self.is_localhost:
            # Build destination as <user>@<server>:<path>
            src = "%s@%s:%s" % (self.user, self.host, src)
        return self.copy(src, dst)
        
    def is_alive(self, verbose = False):
        if self.is_localhost:
            return True

        try:
            (out, err) = self.execute("echo 'ALIVE'",
                timeout = 60,
                err_on_timeout = False,
                persistent = False)
        except:
            if verbose:
                self._logger.warn("Unresponsive node %s got:\n%s%s", self.host, out, err)
            return False

        if out.strip().startswith('ALIVE'):
            return True
        else:
            if verbose:
                self._logger.warn("Unresponsive node %s got:\n%s%s", self.host, out, err)
            return False

    def mkdir(self, path, clean = True):
        if clean:
            self.rmdir(path)

        return self.execute(
            "mkdir -p %s" % path,
            timeout = 120,
            retry = 3
            )

    def rmdir(self, path):
        return self.execute(
            "rm -rf %s" % path,
            timeout = 120,
            retry = 3
            )

    def copy(self, src, dst):
        if self.is_localhost:
            command = ["cp", "-R", src, dst]
            p = subprocess.Popen(command, stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
            out, err = p.communicate()
        else:
            (out, err), proc = eintr_retry(rcopy)(
                src, dst, 
                port = self.port,
                agent = self.agent,
                identity = self.identity)

            if proc.wait():
                msg = "Error uploading to %s got:\n%s%s" %\
                        (self.host, out, err)
                self._logger.error(msg)
                raise RuntimeError(msg)

        return (out, err)

    def execute(self, command,
            sudo = False,
            stdin = None, 
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

        if self.is_localhost:
            if env:
                export = ''
                for envkey, envval in env.iteritems():
                    export += '%s=%s ' % (envkey, envval)
                command = export + command

            if sudo:
                command = "sudo " + command

            p = subprocess.Popen(command, stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
            out, err = p.communicate()
        else:
            (out, err), proc = eintr_retry(rexec)(
                    command, 
                    self.host, 
                    self.user,
                    port = self.port, 
                    agent = self.agent,
                    sudo = sudo,
                    stdin = stdin, 
                    identity = self.identity,
                    tty = tty,
                    x11 = self.forward_x11,
                    env = env,
                    timeout = timeout,
                    retry = retry,
                    err_on_timeout = err_on_timeout,
                    connect_timeout = connect_timeout,
                    persistent = persistent)

            if proc.wait():
                msg = "Failed to execute command %s at node %s: %s %s" % \
                        (command, self.host, out, err,)
                self._logger.warn(msg)
                raise RuntimeError(msg)
        return (out, err)

    def run(self, command, home, 
            stdin = None, 
            stdout = 'stdout', 
            stderr = 'stderr', 
            sudo = False):
        self._logger.info("Running %s", command)
        
        pidfile = './pid'

        if self.is_localhost:
            if stderr == stdout:
                stderr = '&1'
            else:
                stderr = ' ' + stderr
            
            daemon_command = '{ { %(command)s  > %(stdout)s 2>%(stderr)s < %(stdin)s & } ; echo $! 1 > %(pidfile)s ; }' % {
                'command' : command,
                'pidfile' : pidfile,
                
                'stdout' : stdout,
                'stderr' : stderr,
                'stdin' : stdin,
            }
            
            cmd = "%(create)s%(gohome)s rm -f %(pidfile)s ; %(sudo)s nohup bash -c '%(command)s' " % {
                    'command' : daemon_command,
                    
                    'sudo' : 'sudo -S' if sudo else '',
                    
                    'pidfile' : pidfile,
                    'gohome' : 'cd %s ; ' % home if home else '',
                    'create' : 'mkdir -p %s ; ' % home if create_home else '',
                }
            p = subprocess.Popen(command, stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
            out, err = p.communicate()
        else:
            # Start process in a "daemonized" way, using nohup and heavy
            # stdin/out redirection to avoid connection issues
            (out,err), proc = rspawn(
                command,
                pidfile = pidfile,
                home = home,
                stdin = stdin if stdin is not None else '/dev/null',
                stdout = stdout if stdout else '/dev/null',
                stderr = stderr if stderr else '/dev/null',
                sudo = sudo,
                host = self.host,
                user = self.user,
                port = self.port,
                agent = self.agent,
                identity = self.identity
                )
            
            if proc.wait():
                raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

        return (out, err)
    
    def checkpid(self, path):            
        # Get PID/PPID
        # NOTE: wait a bit for the pidfile to be created
        pidtuple = rcheckpid(
            os.path.join(path, 'pid'),
            host = self.host,
            user = self.user,
            port = self.port,
            agent = self.agent,
            identity = self.identity
            )
        
        return pidtuple
    
    def status(self, pid, ppid):
        status = rstatus(
                pid, ppid,
                host = self.host,
                user = self.user,
                port = self.port,
                agent = self.agent,
                identity = self.identity
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
                agent = self.agent,
                sudo = sudo,
                identity = self.identity
                )

class SSHApiFactory(object):
    _apis = dict()

    @classmethod 
    def get_api(cls, host, user, port = 22, identity = None, 
            agent = True, forward_X11 = False):
 
        key = cls.make_key(host, user, port, agent, forward_X11)
        api = cls._apis.get(key)

        if not api:
            api = SSHApi(host, user, port, identity, agent, forward_X11)
            cls._apis[key] = api

        return api

    @classmethod 
    def make_key(cls, *args):
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()

