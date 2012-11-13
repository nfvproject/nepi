import base64
import errno
import os
import os.path
import select
import signal
import socket
import subprocess
import time
import traceback
import re
import tempfile
import hashlib

OPENSSH_HAS_PERSIST = None
CONTROL_PATH = "yyy_ssh_ctrl_path"

if hasattr(os, "devnull"):
    DEV_NULL = os.devnull
else:
    DEV_NULL = "/dev/null"

SHELL_SAFE = re.compile('^[-a-zA-Z0-9_=+:.,/]*$')

hostbyname_cache = dict()

class STDOUT: 
    """
    Special value that when given to rspawn in stderr causes stderr to 
    redirect to whatever stdout was redirected to.
    """

class RUNNING:
    """
    Process is still running
    """

class FINISHED:
    """
    Process is finished
    """

class NOT_STARTED:
    """
    Process hasn't started running yet (this should be very rare)
    """

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

def make_connkey(user, host, port):
    connkey = repr((user,host,port)).encode("base64").strip().replace('/','.')
    if len(connkey) > 60:
        connkey = hashlib.sha1(connkey).hexdigest()
    return connkey

def make_control_path(user, host, port):
    connkey = make_connkey(user, host, port)
    return '/tmp/%s_%s' % ( CONTROL_PATH, connkey, )

def rexec(command, host, user, 
        port = None, 
        agent = True,
        sudo = False,
        stdin = "",
        identity_file = None,
        env = None,
        tty = False,
        x11 = False,
        timeout = None,
        retry = 0,
        err_on_timeout = True,
        connect_timeout = 30,
        persistent = True):
    """
    Executes a remote command, returns ((stdout,stderr),process)
    """
    args = ['ssh', '-C',
            # Don't bother with localhost. Makes test easier
            '-o', 'NoHostAuthenticationForLocalhost=yes',
            # XXX: Possible security issue
            # Avoid interactive requests to accept new host keys
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=%d' % (int(connect_timeout),),
            '-o', 'ConnectionAttempts=3',
            '-o', 'ServerAliveInterval=30',
            '-o', 'TCPKeepAlive=yes',
            '-l', user, host]

    if persistent and openssh_has_persist():
        control_path = make_control_path(user, host, port)
        args.extend([
            '-o', 'ControlMaster=auto',
            '-o', 'ControlPath=%s' % control_path,
            '-o', 'ControlPersist=60' ])
    if agent:
        args.append('-A')
    if port:
        args.append('-p%d' % port)
    if identity_file:
        args.extend(('-i', identity_file))
    if tty:
        args.append('-t')
        if sudo:
            args.append('-t')
    if x11:
        args.append('-X')

    if env:
        export = ''
        for envkey, envval in env.iteritems():
            export += '%s=%s ' % (envkey, envval)
        command = export + command

    if sudo:
        command = "sudo " + command

    args.append(command)

    for x in xrange(retry or 3):
        # connects to the remote host and starts a remote connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        
        try:
            out, err = _communicate(proc, stdin, timeout, err_on_timeout)
            if proc.poll():
                if err.strip().startswith('ssh: ') or err.strip().startswith('mux_client_hello_exchange: '):
                    # SSH error, can safely retry
                    continue
                elif retry:
                    # Probably timed out or plain failed but can retry
                    continue
            break
        except RuntimeError,e:
            if retry <= 0:
                raise
            retry -= 1
        
    return ((out, err), proc)

def rcopy(source, dest,
        port = None, 
        agent = True, 
        recursive = False,
        identity_file = None):
    """
    Copies file from/to remote sites.
    
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
        
        args = ['ssh', '-l', user, '-C',
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes',
                # XXX: Possible security issue
                # Avoid interactive requests to accept new host keys
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=30',
                '-o', 'ConnectionAttempts=3',
                '-o', 'ServerAliveInterval=30',
                '-o', 'TCPKeepAlive=yes',
                host ]

        if openssh_has_persist():
            control_path = make_control_path(user, host, port)
            args.extend([
                '-o', 'ControlMaster=auto',
                '-o', 'ControlPath=%s' % control_path,
                '-o', 'ControlPersist=60' ])
        if port:
            args.append('-P%d' % port)
        if identity_file:
            args.extend(('-i', identity_file))
        
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
            eintr_retry(proc.wait)()
            return ((None,err), proc)
        elif isinstance(dest, file):
            proc = subprocess.Popen(args, 
                    stdout = open('/dev/null','w'),
                    stderr = subprocess.PIPE,
                    stdin = source)
            err = proc.stderr.read()
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
        args = ['scp', '-q', '-p', '-C',
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes',
                # XXX: Possible security issue
                # Avoid interactive requests to accept new host keys
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=30',
                '-o', 'ConnectionAttempts=3',
                '-o', 'ServerAliveInterval=30',
                '-o', 'TCPKeepAlive=yes' ]
                
        if port:
            args.append('-P%d' % port)
        if recursive:
            args.append('-r')
        if identity_file:
            args.extend(('-i', identity_file))

        if isinstance(source,list):
            args.extend(source)
        else:
            if openssh_has_persist():
                control_path = make_control_path(user, host, port)
                args.extend([
                    '-o', 'ControlMaster=no',
                    '-o', 'ControlPath=%s' % control_path ])
            args.append(source)

        args.append(dest)

        # connects to the remote host and starts a remote connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        
        comm = proc.communicate()
        eintr_retry(proc.wait)()
        return (comm, proc)

def rspawn(command, pidfile, 
        stdout = '/dev/null', 
        stderr = STDOUT, 
        stdin = '/dev/null', 
        home = None, 
        create_home = False, 
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        sudo = False,
        identity_file = None, 
        tty = False):
    """
    Spawn a remote command such that it will continue working asynchronously.
    
    Parameters:
        command: the command to run - it should be a single line.
        
        pidfile: path of a (ideally unique to this task) pidfile for tracking the process.
        
        stdout: path of a file to redirect standard output to - must be a string.
            Defaults to /dev/null
        stderr: path of a file to redirect standard error to - string or the special STDOUT value
            to redirect to the same file stdout was redirected to. Defaults to STDOUT.
        stdin: path of a file with input to be piped into the command's standard input
        
        home: path of a folder to use as working directory - should exist, unless you specify create_home
        
        create_home: if True, the home folder will be created first with mkdir -p
        
        sudo: whether the command needs to be executed as root
        
        host/port/user/agent/identity_file: see rexec
    
    Returns:
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

    (out,err), proc = rexec(
        cmd,
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity_file = identity_file,
        tty = tty
        )
    
    if proc.wait():
        raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

    return (out,err),proc

@eintr_retry
def rcheck_pid(pidfile,
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        identity_file = None):
    """
    Check the pidfile of a process spawned with remote_spawn.
    
    Parameters:
        pidfile: the pidfile passed to remote_span
        
        host/port/user/agent/identity_file: see rexec
    
    Returns:
        
        A (pid, ppid) tuple useful for calling remote_status and remote_kill,
        or None if the pidfile isn't valid yet (maybe the process is still starting).
    """

    (out,err),proc = rexec(
        "cat %(pidfile)s" % {
            'pidfile' : pidfile,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity_file = identity_file
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
        identity_file = None):
    """
    Check the status of a process spawned with remote_spawn.
    
    Parameters:
        pid/ppid: pid and parent-pid of the spawned process. See remote_check_pid
        
        host/port/user/agent/identity_file: see rexec
    
    Returns:
        
        One of NOT_STARTED, RUNNING, FINISHED
    """

    (out,err),proc = rexec(
        "ps --pid %(pid)d -o pid | grep -c %(pid)d ; true" % {
            'ppid' : ppid,
            'pid' : pid,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        identity_file = identity_file
        )
    
    if proc.wait():
        return NOT_STARTED
    
    status = False
    if out:
        try:
            status = bool(int(out.strip()))
        except:
            if out or err:
                logging.warn("Error checking remote status:\n%s%s\n", out, err)
            # Ignore, many ways to fail that don't matter that much
            return NOT_STARTED
    return RUNNING if status else FINISHED
    

@eintr_retry
def rkill(pid, ppid, 
        host = None, 
        port = None, 
        user = None, 
        agent = None, 
        sudo = False,
        identity_file = None, 
        nowait = False):
    """
    Kill a process spawned with remote_spawn.
    
    First tries a SIGTERM, and if the process does not end in 10 seconds,
    it sends a SIGKILL.
    
    Parameters:
        pid/ppid: pid and parent-pid of the spawned process. See remote_check_pid
        
        sudo: whether the command was run with sudo - careful killing like this.
        
        host/port/user/agent/identity_file: see rexec
    
    Returns:
        
        Nothing, should have killed the process
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
        identity_file = identity_file
        )
    
    # wait, don't leave zombies around
    proc.wait()

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

