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

import base64
import errno
import hashlib
import logging
import os
import os.path
import re
import select
import signal
import socket
import subprocess
import threading
import time
import tempfile

logger = logging.getLogger("sshfuncs")

def log(msg, level, out = None, err = None):
    if out:
        msg += " - OUT: %s " % out

    if err:
        msg += " - ERROR: %s " % err

    logger.log(level, msg)


if hasattr(os, "devnull"):
    DEV_NULL = os.devnull
else:
    DEV_NULL = "/dev/null"

SHELL_SAFE = re.compile('^[-a-zA-Z0-9_=+:.,/]*$')

class STDOUT: 
    """
    Special value that when given to rspawn in stderr causes stderr to 
    redirect to whatever stdout was redirected to.
    """

class ProcStatus:
    """
    Codes for status of remote spawned process
    """
    # Process is still running
    RUNNING = 1

    # Process is finished
    FINISHED = 2
    
    # Process hasn't started running yet (this should be very rare)
    NOT_STARTED = 3

hostbyname_cache = dict()
hostbyname_cache_lock = threading.Lock()

def gethostbyname(host):
    global hostbyname_cache
    global hostbyname_cache_lock
    
    hostbyname = hostbyname_cache.get(host)
    if not hostbyname:
        with hostbyname_cache_lock:
            hostbyname = socket.gethostbyname(host)
            hostbyname_cache[host] = hostbyname

            msg = " Added hostbyname %s - %s " % (host, hostbyname)
            log(msg, logging.DEBUG)

    return hostbyname

OPENSSH_HAS_PERSIST = None

def openssh_has_persist():
    """ The ssh_config options ControlMaster and ControlPersist allow to
    reuse a same network connection for multiple ssh sessions. In this 
    way limitations on number of open ssh connections can be bypassed.
    However, older versions of openSSH do not support this feature.
    This function is used to determine if ssh connection persist features
    can be used.
    """
    global OPENSSH_HAS_PERSIST
    if OPENSSH_HAS_PERSIST is None:
        proc = subprocess.Popen(["ssh","-v"],
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            stdin = open("/dev/null","r") )
        out,err = proc.communicate()
        proc.wait()
        
        vre = re.compile(r'OpenSSH_(?:[6-9]|5[.][8-9]|5[.][1-9][0-9]|[1-9][0-9]).*', re.I)
        OPENSSH_HAS_PERSIST = bool(vre.match(out))
    return OPENSSH_HAS_PERSIST

def make_server_key_args(server_key, host, port):
    """ Returns a reference to a temporary known_hosts file, to which 
    the server key has been added. 
    
    Make sure to hold onto the temp file reference until the process is 
    done with it

    :param server_key: the server public key
    :type server_key: str

    :param host: the hostname
    :type host: str

    :param port: the ssh port
    :type port: str

    """
    if port is not None:
        host = '%s:%s' % (host, str(port))

    # Create a temporary server key file
    tmp_known_hosts = tempfile.NamedTemporaryFile()
   
    hostbyname = gethostbyname(host) 

    # Add the intended host key
    tmp_known_hosts.write('%s,%s %s\n' % (host, hostbyname, server_key))
    
    # If we're not in strict mode, add user-configured keys
    if os.environ.get('NEPI_STRICT_AUTH_MODE',"").lower() not in ('1','true','on'):
        user_hosts_path = '%s/.ssh/known_hosts' % (os.environ.get('HOME',""),)
        if os.access(user_hosts_path, os.R_OK):
            f = open(user_hosts_path, "r")
            tmp_known_hosts.write(f.read())
            f.close()
        
    tmp_known_hosts.flush()
    
    return tmp_known_hosts

def make_control_path(agent, forward_x11):
    ctrl_path = "/tmp/nepi_ssh"

    if agent:
        ctrl_path +="_a"

    if forward_x11:
        ctrl_path +="_x"

    ctrl_path += "-%r@%h:%p"

    return ctrl_path

def shell_escape(s):
    """ Escapes strings so that they are safe to use as command-line 
    arguments """
    if SHELL_SAFE.match(s):
        # safe string - no escaping needed
        return s
    else:
        # unsafe string - escape
        def escp(c):
            if (32 <= ord(c) < 127 or c in ('\r','\n','\t')) and c not in ("'",'"'):
                return c
            else:
                return "'$'\\x%02x''" % (ord(c),)
        s = ''.join(map(escp,s))
        return "'%s'" % (s,)

def eintr_retry(func):
    """Retries a function invocation when a EINTR occurs"""
    import functools
    @functools.wraps(func)
    def rv(*p, **kw):
        retry = kw.pop("_retry", False)
        for i in xrange(0 if retry else 4):
            try:
                return func(*p, **kw)
            except (select.error, socket.error), args:
                if args[0] == errno.EINTR:
                    continue
                else:
                    raise 
            except OSError, e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
        else:
            return func(*p, **kw)
    return rv

def rexec(command, host, user, 
        port = None, 
        agent = True,
        sudo = False,
        stdin = None,
        identity = None,
        server_key = None,
        env = None,
        tty = False,
        timeout = None,
        retry = 3,
        err_on_timeout = True,
        connect_timeout = 30,
        persistent = True,
        forward_x11 = False,
        strict_host_checking = True):
    """
    Executes a remote command, returns ((stdout,stderr),process)
    """
    
    tmp_known_hosts = None
    hostip = gethostbyname(host)

    args = ['ssh', '-C',
            # Don't bother with localhost. Makes test easier
            '-o', 'NoHostAuthenticationForLocalhost=yes',
            '-o', 'ConnectTimeout=%d' % (int(connect_timeout),),
            '-o', 'ConnectionAttempts=3',
            '-o', 'ServerAliveInterval=30',
            '-o', 'TCPKeepAlive=yes',
            '-l', user, hostip or host]

    if persistent and openssh_has_persist():
        args.extend([
            '-o', 'ControlMaster=auto',
            '-o', 'ControlPath=%s' % (make_control_path(agent, forward_x11),),
            '-o', 'ControlPersist=60' ])

    if not strict_host_checking:
        # Do not check for Host key. Unsafe.
        args.extend(['-o', 'StrictHostKeyChecking=no'])

    if agent:
        args.append('-A')

    if port:
        args.append('-p%d' % port)

    if identity:
        args.extend(('-i', identity))

    if tty:
        args.append('-t')
        args.append('-t')

    if forward_x11:
        args.append('-X')

    if server_key:
        # Create a temporary server key file
        tmp_known_hosts = make_server_key_args(server_key, host, port)
        args.extend(['-o', 'UserKnownHostsFile=%s' % (tmp_known_hosts.name,)])

    args.append(command)

    for x in xrange(retry):
        # connects to the remote host and starts a remote connection
        proc = subprocess.Popen(args,
                env = env,
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        
        # attach tempfile object to the process, to make sure the file stays
        # alive until the process is finished with it
        proc._known_hosts = tmp_known_hosts
    
        try:
            out, err = _communicate(proc, stdin, timeout, err_on_timeout)
            msg = " rexec - host %s - command %s " % (host, " ".join(args))
            log(msg, logging.DEBUG, out, err)

            if proc.poll():
                skip = False

                if err.strip().startswith('ssh: ') or err.strip().startswith('mux_client_hello_exchange: '):
                    # SSH error, can safely retry
                    skip = True 
                elif retry:
                    # Probably timed out or plain failed but can retry
                    skip = True 
                
                if skip:
                    t = x*2
                    msg = "SLEEPING %d ... ATEMPT %d - host %s - command %s " % ( 
                            t, x, host, " ".join(args))
                    log(msg, logging.DEBUG)

                    time.sleep(t)
                    continue
            break
        except RuntimeError, e:
            msg = " rexec EXCEPTION - host %s - command %s - TIMEOUT -> %s" % (host, " ".join(args), e.args)
            log(msg, logging.DEBUG, out, err)

            if retry <= 0:
                raise
            retry -= 1
        
    return ((out, err), proc)

def rcopy(source, dest,
        port = None, 
        agent = True, 
        recursive = False,
        identity = None,
        server_key = None,
        retry = 3,
        strict_host_checking = True):
    """
    Copies from/to remote sites.
    
    Source and destination should have the user and host encoded
    as per scp specs.
    
    If source is a file object, a special mode will be used to
    create the remote file with the same contents.
    
    If dest is a file object, the remote file (source) will be
    read and written into dest.
    
    In these modes, recursive cannot be True.
    
    Source can be a list of files to copy to a single destination,
    in which case it is advised that the destination be a folder.
    """
    
    if isinstance(source, file) and source.tell() == 0:
        source = source.name
    elif hasattr(source, 'read'):
        tmp = tempfile.NamedTemporaryFile()
        while True:
            buf = source.read(65536)
            if buf:
                tmp.write(buf)
            else:
                break
        tmp.seek(0)
        source = tmp.name
    
    if isinstance(source, file) or isinstance(dest, file) \
            or hasattr(source, 'read')  or hasattr(dest, 'write'):
        assert not recursive
        
        # Parse source/destination as <user>@<server>:<path>
        if isinstance(dest, basestring) and ':' in dest:
            remspec, path = dest.split(':',1)
        elif isinstance(source, basestring) and ':' in source:
            remspec, path = source.split(':',1)
        else:
            raise ValueError, "Both endpoints cannot be local"
        user,host = remspec.rsplit('@',1)
        
        tmp_known_hosts = None
        hostip = gethostbyname(host)
        
        args = ['ssh', '-l', user, '-C',
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes',
                '-o', 'ConnectTimeout=60',
                '-o', 'ConnectionAttempts=3',
                '-o', 'ServerAliveInterval=30',
                '-o', 'TCPKeepAlive=yes',
                hostip or host ]

        if openssh_has_persist():
            args.extend([
                '-o', 'ControlMaster=auto',
                '-o', 'ControlPath=%s' % (make_control_path(agent, False),),
                '-o', 'ControlPersist=60' ])

        if port:
            args.append('-P%d' % port)

        if identity:
            args.extend(('-i', identity))

        if server_key:
            # Create a temporary server key file
            tmp_known_hosts = make_server_key_args(server_key, host, port)
            args.extend(['-o', 'UserKnownHostsFile=%s' % (tmp_known_hosts.name,)])
        
        if isinstance(source, file) or hasattr(source, 'read'):
            args.append('cat > %s' % (shell_escape(path),))
        elif isinstance(dest, file) or hasattr(dest, 'write'):
            args.append('cat %s' % (shell_escape(path),))
        else:
            raise AssertionError, "Unreachable code reached! :-Q"
        
        # connects to the remote host and starts a remote connection
        if isinstance(source, file):
            proc = subprocess.Popen(args, 
                    stdout = open('/dev/null','w'),
                    stderr = subprocess.PIPE,
                    stdin = source)
            err = proc.stderr.read()
            proc._known_hosts = tmp_known_hosts
            eintr_retry(proc.wait)()
            return ((None,err), proc)
        elif isinstance(dest, file):
            proc = subprocess.Popen(args, 
                    stdout = open('/dev/null','w'),
                    stderr = subprocess.PIPE,
                    stdin = source)
            err = proc.stderr.read()
            proc._known_hosts = tmp_known_hosts
            eintr_retry(proc.wait)()
            return ((None,err), proc)
        elif hasattr(source, 'read'):
            # file-like (but not file) source
            proc = subprocess.Popen(args, 
                    stdout = open('/dev/null','w'),
                    stderr = subprocess.PIPE,
                    stdin = subprocess.PIPE)
            
            buf = None
            err = []
            while True:
                if not buf:
                    buf = source.read(4096)
                if not buf:
                    #EOF
                    break
                
                rdrdy, wrdy, broken = select.select(
                    [proc.stderr],
                    [proc.stdin],
                    [proc.stderr,proc.stdin])
                
                if proc.stderr in rdrdy:
                    # use os.read for fully unbuffered behavior
                    err.append(os.read(proc.stderr.fileno(), 4096))
                
                if proc.stdin in wrdy:
                    proc.stdin.write(buf)
                    buf = None
                
                if broken:
                    break
            proc.stdin.close()
            err.append(proc.stderr.read())
                
            proc._known_hosts = tmp_known_hosts
            eintr_retry(proc.wait)()
            return ((None,''.join(err)), proc)
        elif hasattr(dest, 'write'):
            # file-like (but not file) dest
            proc = subprocess.Popen(args, 
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE,
                    stdin = open('/dev/null','w'))
            
            buf = None
            err = []
            while True:
                rdrdy, wrdy, broken = select.select(
                    [proc.stderr, proc.stdout],
                    [],
                    [proc.stderr, proc.stdout])
                
                if proc.stderr in rdrdy:
                    # use os.read for fully unbuffered behavior
                    err.append(os.read(proc.stderr.fileno(), 4096))
                
                if proc.stdout in rdrdy:
                    # use os.read for fully unbuffered behavior
                    buf = os.read(proc.stdout.fileno(), 4096)
                    dest.write(buf)
                    
                    if not buf:
                        #EOF
                        break
                
                if broken:
                    break
            err.append(proc.stderr.read())
                
            proc._known_hosts = tmp_known_hosts
            eintr_retry(proc.wait)()
            return ((None,''.join(err)), proc)
        else:
            raise AssertionError, "Unreachable code reached! :-Q"
    else:
        # Parse destination as <user>@<server>:<path>
        if isinstance(dest, basestring) and ':' in dest:
            remspec, path = dest.split(':',1)
        elif isinstance(source, basestring) and ':' in source:
            remspec, path = source.split(':',1)
        else:
            raise ValueError, "Both endpoints cannot be local"
        user,host = remspec.rsplit('@',1)
        
        # plain scp
        tmp_known_hosts = None

        args = ['scp', '-q', '-p', '-C',
                # Speed up transfer using blowfish cypher specification which is 
                # faster than the default one (3des)
                '-c', 'blowfish',
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes',
                '-o', 'ConnectTimeout=60',
                '-o', 'ConnectionAttempts=3',
                '-o', 'ServerAliveInterval=30',
                '-o', 'TCPKeepAlive=yes' ]
                
        if port:
            args.append('-P%d' % port)

        if recursive:
            args.append('-r')

        if identity:
            args.extend(('-i', identity))

        if server_key:
            # Create a temporary server key file
            tmp_known_hosts = make_server_key_args(server_key, host, port)
            args.extend(['-o', 'UserKnownHostsFile=%s' % (tmp_known_hosts.name,)])

        if not strict_host_checking:
            # Do not check for Host key. Unsafe.
            args.extend(['-o', 'StrictHostKeyChecking=no'])

        if isinstance(source,list):
            args.extend(source)
        else:
            if openssh_has_persist():
                args.extend([
                    '-o', 'ControlMaster=auto',
                    '-o', 'ControlPath=%s' % (make_control_path(agent, False),)
                    ])
            args.append(source)

        args.append(dest)

        for x in xrange(retry):
            # connects to the remote host and starts a remote connection
            proc = subprocess.Popen(args,
                    stdout = subprocess.PIPE,
                    stdin = subprocess.PIPE, 
                    stderr = subprocess.PIPE)
            
            # attach tempfile object to the process, to make sure the file stays
            # alive until the process is finished with it
            proc._known_hosts = tmp_known_hosts
        
            try:
                (out, err) = proc.communicate()
                eintr_retry(proc.wait)()
                msg = " rcopy - host %s - command %s " % (host, " ".join(args))
                log(msg, logging.DEBUG, out, err)

                if proc.poll():
                    t = x*2
                    msg = "SLEEPING %d ... ATEMPT %d - host %s - command %s " % ( 
                            t, x, host, " ".join(args))
                    log(msg, logging.DEBUG)

                    time.sleep(t)
                    continue

                break
            except RuntimeError, e:
                msg = " rcopy EXCEPTION - host %s - command %s - TIMEOUT -> %s" % (host, " ".join(args), e.args)
                log(msg, logging.DEBUG, out, err)

                if retry <= 0:
                    raise
                retry -= 1
            
        return ((out, err), proc)

def rspawn(command, pidfile, 
        stdout = '/dev/null', 
        stderr = STDOUT, 
        stdin = '/dev/null',
        home = None, 
        create_home = False, 
        sudo = False,
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        identity = None, 
        server_key = None,
        tty = False):
    """
    Spawn a remote command such that it will continue working asynchronously in 
    background. 

        :param command: The command to run, it should be a single line.
        :type command: str

        :param pidfile: Path to a file where to store the pid and ppid of the 
                        spawned process
        :type pidfile: str

        :param stdout: Path to file to redirect standard output. 
                       The default value is /dev/null
        :type stdout: str

        :param stderr: Path to file to redirect standard error.
                       If the special STDOUT value is used, stderr will 
                       be redirected to the same file as stdout
        :type stderr: str

        :param stdin: Path to a file with input to be piped into the command's standard input
        :type stdin: str

        :param home: Path to working directory folder. 
                    It is assumed to exist unless the create_home flag is set.
        :type home: str

        :param create_home: Flag to force creation of the home folder before 
                            running the command
        :type create_home: bool
 
        :param sudo: Flag forcing execution with sudo user
        :type sudo: bool
        
        :rtype: touple

        (stdout, stderr), process
        
        Of the spawning process, which only captures errors at spawning time.
        Usually only useful for diagnostics.
    """
    # Start process in a "daemonized" way, using nohup and heavy
    # stdin/out redirection to avoid connection issues
    if stderr is STDOUT:
        stderr = '&1'
    else:
        stderr = ' ' + stderr
    
    daemon_command = '{ { %(command)s  > %(stdout)s 2>%(stderr)s < %(stdin)s & } ; echo $! 1 > %(pidfile)s ; }' % {
        'command' : command,
        'pidfile' : shell_escape(pidfile),
        'stdout' : stdout,
        'stderr' : stderr,
        'stdin' : stdin,
    }
    
    cmd = "%(create)s%(gohome)s rm -f %(pidfile)s ; %(sudo)s nohup bash -c %(command)s " % {
            'command' : shell_escape(daemon_command),
            'sudo' : 'sudo -S' if sudo else '',
            'pidfile' : shell_escape(pidfile),
            'gohome' : 'cd %s ; ' % (shell_escape(home),) if home else '',
            'create' : 'mkdir -p %s ; ' % (shell_escape(home),) if create_home and home else '',
        }

    (out,err),proc = rexec(
        cmd,
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity = identity,
        server_key = server_key,
        tty = tty ,
        )
    
    if proc.wait():
        raise RuntimeError, "Failed to set up application on host %s: %s %s" % (host, out,err,)

    return ((out, err), proc)

@eintr_retry
def rgetpid(pidfile,
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        identity = None,
        server_key = None):
    """
    Returns the pid and ppid of a process from a remote file where the 
    information was stored.

        :param home: Path to directory where the pidfile is located
        :type home: str

        :param pidfile: Name of file containing the pid information
        :type pidfile: str
        
        :rtype: int
        
        A (pid, ppid) tuple useful for calling rstatus and rkill,
        or None if the pidfile isn't valid yet (can happen when process is staring up)

    """
    (out,err),proc = rexec(
        "cat %(pidfile)s" % {
            'pidfile' : pidfile,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity = identity,
        server_key = server_key
        )
        
    if proc.wait():
        return None
    
    if out:
        try:
            return map(int,out.strip().split(' ',1))
        except:
            # Ignore, many ways to fail that don't matter that much
            return None

@eintr_retry
def rstatus(pid, ppid, 
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        identity = None,
        server_key = None):
    """
    Returns a code representing the the status of a remote process

        :param pid: Process id of the process
        :type pid: int

        :param ppid: Parent process id of process
        :type ppid: int
    
        :rtype: int (One of NOT_STARTED, RUNNING, FINISHED)
    
    """
    (out,err),proc = rexec(
        # Check only by pid. pid+ppid does not always work (especially with sudo) 
        " (( ps --pid %(pid)d -o pid | grep -c %(pid)d && echo 'wait')  || echo 'done' ) | tail -n 1" % {
            'ppid' : ppid,
            'pid' : pid,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity = identity,
        server_key = server_key
        )
    
    if proc.wait():
        return ProcStatus.NOT_STARTED
    
    status = False
    if err:
        if err.strip().find("Error, do this: mount -t proc none /proc") >= 0:
            status = True
    elif out:
        status = (out.strip() == 'wait')
    else:
        return ProcStatus.NOT_STARTED
    return ProcStatus.RUNNING if status else ProcStatus.FINISHED

@eintr_retry
def rkill(pid, ppid,
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        sudo = False,
        identity = None, 
        server_key = None, 
        nowait = False):
    """
    Sends a kill signal to a remote process.

    First tries a SIGTERM, and if the process does not end in 10 seconds,
    it sends a SIGKILL.
 
        :param pid: Process id of process to be killed
        :type pid: int

        :param ppid: Parent process id of process to be killed
        :type ppid: int

        :param sudo: Flag indicating if sudo should be used to kill the process
        :type sudo: bool
        
    """
    subkill = "$(ps --ppid %(pid)d -o pid h)" % { 'pid' : pid }
    cmd = """
SUBKILL="%(subkill)s" ;
%(sudo)s kill -- -%(pid)d $SUBKILL || /bin/true
%(sudo)s kill %(pid)d $SUBKILL || /bin/true
for x in 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 ; do 
    sleep 0.2 
    if [ `ps --pid %(pid)d -o pid | grep -c %(pid)d` == '0' ]; then
        break
    else
        %(sudo)s kill -- -%(pid)d $SUBKILL || /bin/true
        %(sudo)s kill %(pid)d $SUBKILL || /bin/true
    fi
    sleep 1.8
done
if [ `ps --pid %(pid)d -o pid | grep -c %(pid)d` != '0' ]; then
    %(sudo)s kill -9 -- -%(pid)d $SUBKILL || /bin/true
    %(sudo)s kill -9 %(pid)d $SUBKILL || /bin/true
fi
"""
    if nowait:
        cmd = "( %s ) >/dev/null 2>/dev/null </dev/null &" % (cmd,)

    (out,err),proc = rexec(
        cmd % {
            'ppid' : ppid,
            'pid' : pid,
            'sudo' : 'sudo -S' if sudo else '',
            'subkill' : subkill,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity = identity,
        server_key = server_key
        )
    
    # wait, don't leave zombies around
    proc.wait()

    return (out, err), proc

# POSIX
def _communicate(self, input, timeout=None, err_on_timeout=True):
    read_set = []
    write_set = []
    stdout = None # Return
    stderr = None # Return
    
    killed = False
    
    if timeout is not None:
        timelimit = time.time() + timeout
        killtime = timelimit + 4
        bailtime = timelimit + 4

    if self.stdin:
        # Flush stdio buffer.  This might block, if the user has
        # been writing to .stdin in an uncontrolled fashion.
        self.stdin.flush()
        if input:
            write_set.append(self.stdin)
        else:
            self.stdin.close()
    if self.stdout:
        read_set.append(self.stdout)
        stdout = []
    if self.stderr:
        read_set.append(self.stderr)
        stderr = []

    input_offset = 0
    while read_set or write_set:
        if timeout is not None:
            curtime = time.time()
            if timeout is None or curtime > timelimit:
                if curtime > bailtime:
                    break
                elif curtime > killtime:
                    signum = signal.SIGKILL
                else:
                    signum = signal.SIGTERM
                # Lets kill it
                os.kill(self.pid, signum)
                select_timeout = 0.5
            else:
                select_timeout = timelimit - curtime + 0.1
        else:
            select_timeout = 1.0
        
        if select_timeout > 1.0:
            select_timeout = 1.0
            
        try:
            rlist, wlist, xlist = select.select(read_set, write_set, [], select_timeout)
        except select.error,e:
            if e[0] != 4:
                raise
            else:
                continue
        
        if not rlist and not wlist and not xlist and self.poll() is not None:
            # timeout and process exited, say bye
            break

        if self.stdin in wlist:
            # When select has indicated that the file is writable,
            # we can write up to PIPE_BUF bytes without risk
            # blocking.  POSIX defines PIPE_BUF >= 512
            bytes_written = os.write(self.stdin.fileno(), buffer(input, input_offset, 512))
            input_offset += bytes_written
            if input_offset >= len(input):
                self.stdin.close()
                write_set.remove(self.stdin)

        if self.stdout in rlist:
            data = os.read(self.stdout.fileno(), 1024)
            if data == "":
                self.stdout.close()
                read_set.remove(self.stdout)
            stdout.append(data)

        if self.stderr in rlist:
            data = os.read(self.stderr.fileno(), 1024)
            if data == "":
                self.stderr.close()
                read_set.remove(self.stderr)
            stderr.append(data)
    
    # All data exchanged.  Translate lists into strings.
    if stdout is not None:
        stdout = ''.join(stdout)
    if stderr is not None:
        stderr = ''.join(stderr)

    # Translate newlines, if requested.  We cannot let the file
    # object do the translation: It is based on stdio, which is
    # impossible to combine with select (unless forcing no
    # buffering).
    if self.universal_newlines and hasattr(file, 'newlines'):
        if stdout:
            stdout = self._translate_newlines(stdout)
        if stderr:
            stderr = self._translate_newlines(stderr)

    if killed and err_on_timeout:
        errcode = self.poll()
        raise RuntimeError, ("Operation timed out", errcode, stdout, stderr)
    else:
        if killed:
            self.poll()
        else:
            self.wait()
        return (stdout, stderr)

