#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util.constants import DeploymentConfiguration as DC

import base64
import errno
import os
import os.path
import resource
import select
import shutil
import signal
import socket
import sys
import subprocess
import threading
import time
import traceback
import re
import tempfile
import defer
import functools
import collections

CTRL_SOCK = "ctrl.sock"
CTRL_PID = "ctrl.pid"
STD_ERR = "stderr.log"
MAX_FD = 1024

STOP_MSG = "STOP"

TRACE = os.environ.get("NEPI_TRACE", "false").lower() in ("true", "1", "on")

if hasattr(os, "devnull"):
    DEV_NULL = os.devnull
else:
    DEV_NULL = "/dev/null"

SHELL_SAFE = re.compile('^[-a-zA-Z0-9_=+:.,/]*$')

def shell_escape(s):
    """ Escapes strings so that they are safe to use as command-line arguments """
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

class Server(object):
    def __init__(self, root_dir = ".", log_level = DC.ERROR_LEVEL, 
            environment_setup = "", clean_root = False):
        self._root_dir = root_dir
        self._clean_root = clean_root
        self._stop = False
        self._ctrl_sock = None
        self._log_level = log_level
        self._rdbuf = ""
        self._environment_setup = environment_setup

    def run(self):
        try:
            if self.daemonize():
                self.post_daemonize()
                self.loop()
                self.cleanup()
                # ref: "os._exit(0)"
                # can not return normally after fork beacuse no exec was done.
                # This means that if we don't do a os._exit(0) here the code that 
                # follows the call to "Server.run()" in the "caller code" will be 
                # executed... but by now it has already been executed after the 
                # first process (the one that did the first fork) returned.
                os._exit(0)
        except:
            print >>sys.stderr, "SERVER_ERROR."
            self.log_error()
            self.cleanup()
            os._exit(0)
        print >>sys.stderr, "SERVER_READY."

    def daemonize(self):
        # pipes for process synchronization
        (r, w) = os.pipe()
        
        # build root folder
        root = os.path.normpath(self._root_dir)
        if self._root_dir not in [".", ""] and os.path.exists(root) \
                and self._clean_root:
            shutil.rmtree(root)
        if not os.path.exists(root):
            os.makedirs(root, 0755)

        pid1 = os.fork()
        if pid1 > 0:
            os.close(w)
            while True:
                try:
                    os.read(r, 1)
                except OSError, e: # pragma: no cover
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise
                break
            os.close(r)
            # os.waitpid avoids leaving a <defunc> (zombie) process
            st = os.waitpid(pid1, 0)[1]
            if st:
                raise RuntimeError("Daemonization failed")
            # return 0 to inform the caller method that this is not the 
            # daemonized process
            return 0
        os.close(r)

        # Decouple from parent environment.
        os.chdir(self._root_dir)
        os.umask(0)
        os.setsid()

        # fork 2
        pid2 = os.fork()
        if pid2 > 0:
            # see ref: "os._exit(0)"
            os._exit(0)

        # close all open file descriptors.
        max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if (max_fd == resource.RLIM_INFINITY):
            max_fd = MAX_FD
        for fd in range(3, max_fd):
            if fd != w:
                try:
                    os.close(fd)
                except OSError:
                    pass

        # Redirect standard file descriptors.
        stdin = open(DEV_NULL, "r")
        stderr = stdout = open(STD_ERR, "a", 0)
        os.dup2(stdin.fileno(), sys.stdin.fileno())
        # NOTE: sys.stdout.write will still be buffered, even if the file
        # was opened with 0 buffer
        os.dup2(stdout.fileno(), sys.stdout.fileno())
        os.dup2(stderr.fileno(), sys.stderr.fileno())
        
        # setup environment
        if self._environment_setup:
            # parse environment variables and pass to child process
            # do it by executing shell commands, in case there's some heavy setup involved
            envproc = subprocess.Popen(
                [ "bash", "-c", 
                    "( %s python -c 'import os,sys ; print \"\\x01\".join(\"\\x02\".join(map(str,x)) for x in os.environ.iteritems())' ) | tail -1" %
                        ( self._environment_setup, ) ],
                stdin = subprocess.PIPE, 
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
            out,err = envproc.communicate()

            # parse new environment
            if out:
                environment = dict(map(lambda x:x.split("\x02"), out.split("\x01")))
            
                # apply to current environment
                for name, value in environment.iteritems():
                    os.environ[name] = value
                
                # apply pythonpath
                if 'PYTHONPATH' in environment:
                    sys.path = environment['PYTHONPATH'].split(':') + sys.path

        # create control socket
        self._ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._ctrl_sock.bind(CTRL_SOCK)
        except socket.error:
            # Address in use, check pidfile
            pid = None
            try:
                pidfile = open(CTRL_PID, "r")
                pid = pidfile.read()
                pidfile.close()
                pid = int(pid)
            except:
                # no pidfile
                pass
            
            if pid is not None:
                # Check process liveliness
                if not os.path.exists("/proc/%d" % (pid,)):
                    # Ok, it's dead, clean the socket
                    os.remove(CTRL_SOCK)
            
            # try again
            self._ctrl_sock.bind(CTRL_SOCK)
            
        self._ctrl_sock.listen(0)
        
        # Save pidfile
        pidfile = open(CTRL_PID, "w")
        pidfile.write(str(os.getpid()))
        pidfile.close()

        # let the parent process know that the daemonization is finished
        os.write(w, "\n")
        os.close(w)
        return 1

    def post_daemonize(self):
        os.environ["NEPI_CONTROLLER_LOGLEVEL"] = self._log_level
        # QT, for some strange reason, redefines the SIGCHILD handler to write
        # a \0 to a fd (lets say fileno 'x'), when ever a SIGCHILD is received.
        # Server dameonization closes all file descriptors from fileno '3',
        # but the overloaded handler (inherited by the forked process) will
        # keep trying to write the \0 to fileno 'x', which might have been reused 
        # after closing, for other operations. This is bad bad bad when fileno 'x'
        # is in use for communication pouroses, because unexpected \0 start
        # appearing in the communication messages... this is exactly what happens 
        # when using netns in daemonized form. Thus, be have no other alternative than
        # restoring the SIGCHLD handler to the default here.
        import signal
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def loop(self):
        while not self._stop:
            conn, addr = self._ctrl_sock.accept()
            self.log_error("ACCEPTED CONNECTION: %s" % (addr,))
            conn.settimeout(5)
            while not self._stop:
                try:
                    msg = self.recv_msg(conn)
                except socket.timeout, e:
                    #self.log_error("SERVER recv_msg: connection timedout ")
                    continue
                
                if not msg:
                    self.log_error("CONNECTION LOST")
                    break
                    
                if msg == STOP_MSG:
                    self._stop = True
                    reply = self.stop_action()
                else:
                    reply = self.reply_action(msg)
                
                try:
                    self.send_reply(conn, reply)
                except socket.error:
                    self.log_error()
                    self.log_error("NOTICE: Awaiting for reconnection")
                    break
            try:
                conn.close()
            except:
                # Doesn't matter
                self.log_error()

    def recv_msg(self, conn):
        data = [self._rdbuf]
        chunk = data[0]
        while '\n' not in chunk:
            try:
                chunk = conn.recv(1024)
            except (OSError, socket.error), e:
                if e[0] != errno.EINTR:
                    raise
                else:
                    continue
            if chunk:
                data.append(chunk)
            else:
                # empty chunk = EOF
                break
        data = ''.join(data).split('\n',1)
        while len(data) < 2:
            data.append('')
        data, self._rdbuf = data
        
        decoded = base64.b64decode(data)
        return decoded.rstrip()

    def send_reply(self, conn, reply):
        encoded = base64.b64encode(reply)
        conn.send("%s\n" % encoded)
       
    def cleanup(self):
        try:
            self._ctrl_sock.close()
            os.remove(CTRL_SOCK)
        except:
            self.log_error()

    def stop_action(self):
        return "Stopping server"

    def reply_action(self, msg):
        return "Reply to: %s" % msg

    def log_error(self, text = None, context = ''):
        if text == None:
            text = traceback.format_exc()
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        if context:
            context = " (%s)" % (context,)
        sys.stderr.write("ERROR%s: %s\n%s\n" % (context, date, text))
        return text

    def log_debug(self, text):
        if self._log_level == DC.DEBUG_LEVEL:
            date = time.strftime("%Y-%m-%d %H:%M:%S")
            sys.stderr.write("DEBUG: %s\n%s\n" % (date, text))

class Forwarder(object):
    def __init__(self, root_dir = "."):
        self._ctrl_sock = None
        self._root_dir = root_dir
        self._stop = False
        self._rdbuf = ""

    def forward(self):
        self.connect()
        print >>sys.stderr, "FORWARDER_READY."
        while not self._stop:
            data = self.read_data()
            if not data:
                # Connection to client lost
                break
            self.send_to_server(data)
            
            data = self.recv_from_server()
            if not data:
                # Connection to server lost
                raise IOError, "Connection to server lost while "\
                    "expecting response"
            self.write_data(data)
        self.disconnect()

    def read_data(self):
        return sys.stdin.readline()

    def write_data(self, data):
        sys.stdout.write(data)
        # sys.stdout.write is buffered, this is why we need to do a flush()
        sys.stdout.flush()

    def send_to_server(self, data):
        try:
            self._ctrl_sock.send(data)
        except (IOError, socket.error), e:
            if e[0] == errno.EPIPE:
                self.connect()
                self._ctrl_sock.send(data)
            else:
                raise e
        encoded = data.rstrip() 
        msg = base64.b64decode(encoded)
        if msg == STOP_MSG:
            self._stop = True

    def recv_from_server(self):
        data = [self._rdbuf]
        chunk = data[0]
        while '\n' not in chunk:
            try:
                chunk = self._ctrl_sock.recv(1024)
            except (OSError, socket.error), e:
                if e[0] != errno.EINTR:
                    raise
                continue
            if chunk:
                data.append(chunk)
            else:
                # empty chunk = EOF
                break
        data = ''.join(data).split('\n',1)
        while len(data) < 2:
            data.append('')
        data, self._rdbuf = data
        
        return data+'\n'
 
    def connect(self):
        self.disconnect()
        self._ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_addr = os.path.join(self._root_dir, CTRL_SOCK)
        self._ctrl_sock.connect(sock_addr)

    def disconnect(self):
        try:
            self._ctrl_sock.close()
        except:
            pass

class Client(object):
    def __init__(self, root_dir = ".", host = None, port = None, user = None, 
            agent = None, sudo = False, communication = DC.ACCESS_LOCAL,
            environment_setup = ""):
        self.root_dir = root_dir
        self.addr = (host, port)
        self.user = user
        self.agent = agent
        self.sudo = sudo
        self.communication = communication
        self.environment_setup = environment_setup
        self._stopped = False
        self._deferreds = collections.deque()
        self.connect()
    
    def __del__(self):
        if self._process.poll() is None:
            os.kill(self._process.pid, signal.SIGTERM)
        self._process.wait()
        
    def connect(self):
        root_dir = self.root_dir
        (host, port) = self.addr
        user = self.user
        agent = self.agent
        sudo = self.sudo
        communication = self.communication
        
        python_code = "from nepi.util import server;c=server.Forwarder(%r);\
                c.forward()" % (root_dir,)

        self._process = popen_python(python_code, 
                    communication = communication,
                    host = host, 
                    port = port, 
                    user = user, 
                    agent = agent, 
                    sudo = sudo, 
                    environment_setup = self.environment_setup)
               
        # Wait for the forwarder to be ready, otherwise nobody
        # will be able to connect to it
        err = []
        helo = "nope"
        while helo:
            helo = self._process.stderr.readline()
            if helo == 'FORWARDER_READY.\n':
                break
            err.append(helo)
        else:
            raise AssertionError, "Expected 'FORWARDER_READY.', got: %s" % (''.join(err),)
        
    def send_msg(self, msg):
        encoded = base64.b64encode(msg)
        data = "%s\n" % encoded
        
        try:
            self._process.stdin.write(data)
        except (IOError, ValueError):
            # dead process, poll it to un-zombify
            self._process.poll()
            
            # try again after reconnect
            # If it fails again, though, give up
            self.connect()
            self._process.stdin.write(data)

    def send_stop(self):
        self.send_msg(STOP_MSG)
        self._stopped = True

    def defer_reply(self, transform=None):
        defer_entry = []
        self._deferreds.append(defer_entry)
        return defer.Defer(
            functools.partial(self.read_reply, defer_entry, transform)
        )
        
    def _read_reply(self):
        data = self._process.stdout.readline()
        encoded = data.rstrip() 
        if not encoded:
            # empty == eof == dead process, poll it to un-zombify
            self._process.poll()
            
            raise RuntimeError, "Forwarder died while awaiting reply: %s" % (self._process.stderr.read(),)
        return base64.b64decode(encoded)
    
    def read_reply(self, which=None, transform=None):
        # Test to see if someone did it already
        if which is not None and len(which):
            # Ok, they did it...
            # ...just return the deferred value
            if transform:
                return transform(which[0])
            else:
                return which[0]
        
        # Process all deferreds until the one we're looking for
        # or until the queue is empty
        while self._deferreds:
            try:
                deferred = self._deferreds.popleft()
            except IndexError:
                # emptied
                break
            
            deferred.append(self._read_reply())
            if deferred is which:
                # We reached the one we were looking for
                if transform:
                    return transform(deferred[0])
                else:
                    return deferred[0]
        
        if which is None:
            # They've requested a synchronous read
            if transform:
                return transform(self._read_reply())
            else:
                return self._read_reply()

def _make_server_key_args(server_key, host, port, args):
    """ 
    Returns a reference to the created temporary file, and adds the
    corresponding arguments to the given argument list.
    
    Make sure to hold onto it until the process is done with the file
    """
    if port is not None:
        host = '%s:%s' % (host,port)
    # Create a temporary server key file
    tmp_known_hosts = tempfile.NamedTemporaryFile()
    
    # Add the intended host key
    tmp_known_hosts.write('%s,%s %s\n' % (host, socket.gethostbyname(host), server_key))
    
    # If we're not in strict mode, add user-configured keys
    if os.environ.get('NEPI_STRICT_AUTH_MODE',"").lower() not in ('1','true','on'):
        user_hosts_path = '%s/.ssh/known_hosts' % (os.environ.get('HOME',""),)
        if os.access(user_hosts_path, os.R_OK):
            f = open(user_hosts_path, "r")
            tmp_known_hosts.write(f.read())
            f.close()
        
    tmp_known_hosts.flush()
    
    args.extend(['-o', 'UserKnownHostsFile=%s' % (tmp_known_hosts.name,)])
    
    return tmp_known_hosts

def popen_ssh_command(command, host, port, user, agent, 
        stdin="", 
        ident_key = None,
        server_key = None,
        tty = False,
        timeout = None,
        retry = 0,
        err_on_timeout = True,
        connect_timeout = 30):
    """
    Executes a remote commands, returns ((stdout,stderr),process)
    """
    if TRACE:
        print "ssh", host, command
    
    tmp_known_hosts = None
    args = ['ssh',
            # Don't bother with localhost. Makes test easier
            '-o', 'NoHostAuthenticationForLocalhost=yes,ConnectTimeout=%s' % (connect_timeout,),
            '-l', user, host]
    if agent:
        args.append('-A')
    if port:
        args.append('-p%d' % port)
    if ident_key:
        args.extend(('-i', ident_key))
    if tty:
        args.append('-t')
    if server_key:
        # Create a temporary server key file
        tmp_known_hosts = _make_server_key_args(
            server_key, host, port, args)
    args.append(command)

    for x in xrange(retry or 3):
        # connects to the remote host and starts a remote connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        
        # attach tempfile object to the process, to make sure the file stays
        # alive until the process is finished with it
        proc._known_hosts = tmp_known_hosts
        
        try:
            out, err = _communicate(proc, stdin, timeout, err_on_timeout)
            if proc.poll() and err.strip().startswith('ssh: '):
                # SSH error, can safely retry
                continue
            break
        except RuntimeError,e:
            if retry <= 0:
                raise
            if TRACE:
                print " timedout -> ", e.args
            retry -= 1
        
    if TRACE:
        print " -> ", out, err

    return ((out, err), proc)

def popen_scp(source, dest, 
        port = None, 
        agent = None, 
        recursive = False,
        ident_key = None,
        server_key = None):
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
    
    if TRACE:
        print "scp", source, dest
    
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
                host ]
        if port:
            args.append('-P%d' % port)
        if ident_key:
            args.extend(('-i', ident_key))
        if server_key:
            # Create a temporary server key file
            tmp_known_hosts = _make_server_key_args(
                server_key, host, port, args)
        
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
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes' ]
        if port:
            args.append('-P%d' % port)
        if recursive:
            args.append('-r')
        if ident_key:
            args.extend(('-i', ident_key))
        if server_key:
            # Create a temporary server key file
            tmp_known_hosts = _make_server_key_args(
                server_key, host, port, args)
        if isinstance(source,list):
            args.extend(source)
        else:
            args.append(source)
        args.append(dest)

        # connects to the remote host and starts a remote connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        proc._known_hosts = tmp_known_hosts
        
        comm = proc.communicate()
        eintr_retry(proc.wait)()
        return (comm, proc)

def decode_and_execute():
    # The python code we want to execute might have characters that 
    # are not compatible with the 'inline' mode we are using. To avoid
    # problems we receive the encoded python code in base64 as a input 
    # stream and decode it for execution.
    import base64, os
    cmd = ""
    while True:
        try:
            cmd += os.read(0, 1)# one byte from stdin
        except OSError, e:            
            if e.errno == errno.EINTR:
                continue
            else:
                raise
        if cmd[-1] == "\n": 
            break
    cmd = base64.b64decode(cmd)
    # Uncomment for debug
    #os.write(2, "Executing python code: %s\n" % cmd)
    os.write(1, "OK\n") # send a sync message
    exec(cmd)

def popen_python(python_code, 
        communication = DC.ACCESS_LOCAL,
        host = None, 
        port = None, 
        user = None, 
        agent = False, 
        python_path = None,
        ident_key = None,
        server_key = None,
        tty = False,
        sudo = False, 
        environment_setup = ""):

    cmd = ""
    if python_path:
        python_path.replace("'", r"'\''")
        cmd = """PYTHONPATH="$PYTHONPATH":'%s' """ % python_path
        cmd += " ; "
    if environment_setup:
        cmd += environment_setup
        cmd += " ; "
    # Uncomment for debug (to run everything under strace)
    # We had to verify if strace works (cannot nest them)
    #cmd += "if strace echo >/dev/null 2>&1; then CMD='strace -ff -tt -s 200 -o strace.out'; else CMD=''; fi\n"
    #cmd += "$CMD "
    #cmd += "strace -f -tt -s 200 -o strace$$.out "
    import nepi
    cmd += "python -c 'import sys; sys.path.insert(0,%s); from nepi.util import server; server.decode_and_execute()'" % (
        repr(os.path.dirname(os.path.dirname(nepi.__file__))).replace("'",'"'),
    )

    if sudo:
        if ';' in cmd:
            cmd = "sudo bash -c " + shell_escape(cmd)
        else:
            cmd = "sudo " + cmd

    if communication == DC.ACCESS_SSH:
        tmp_known_hosts = None
        args = ['ssh',
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes',
                '-l', user, host]
        if agent:
            args.append('-A')
        if port:
            args.append('-p%d' % port)
        if ident_key:
            args.extend(('-i', ident_key))
        if tty:
            args.append('-t')
        if server_key:
            # Create a temporary server key file
            tmp_known_hosts = _make_server_key_args(
                server_key, host, port, args)
        args.append(cmd)
    else:
        args = [ "/bin/bash", "-c", cmd ]

    # connects to the remote host and starts a remote
    proc = subprocess.Popen(args,
            shell = False, 
            stdout = subprocess.PIPE,
            stdin = subprocess.PIPE, 
            stderr = subprocess.PIPE)

    if communication == DC.ACCESS_SSH:
        proc._known_hosts = tmp_known_hosts

    # send the command to execute
    os.write(proc.stdin.fileno(),
            base64.b64encode(python_code) + "\n")
 
    while True: 
        try:
            msg = os.read(proc.stdout.fileno(), 3)
            break
        except OSError, e:            
            if e.errno == errno.EINTR:
                continue
            else:
                raise
    
    if msg != "OK\n":
        raise RuntimeError, "Failed to start remote python interpreter: \nout:\n%s%s\nerr:\n%s" % (
            msg, proc.stdout.read(), proc.stderr.read())

    return proc

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
            select_timeout = None
            
        try:
            rlist, wlist, xlist = select.select(read_set, write_set, [], select_timeout)
        except select.error,e:
            if e[0] != 4:
                raise
            else:
                continue

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

