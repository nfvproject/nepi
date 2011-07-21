#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import errno
import os
import os.path
import resource
import select
import socket
import sys
import subprocess
import threading
import time
import traceback
import signal
import re
import tempfile
import defer
import functools
import collections

CTRL_SOCK = "ctrl.sock"
STD_ERR = "stderr.log"
MAX_FD = 1024

STOP_MSG = "STOP"

ERROR_LEVEL = 0
DEBUG_LEVEL = 1
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
            if (32 <= ord(c) < 127 or c in ('\r','\n','\t')) and c not in ("'",):
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
    def __init__(self, root_dir = ".", log_level = ERROR_LEVEL):
        self._root_dir = root_dir
        self._stop = False
        self._ctrl_sock = None
        self._log_level = log_level
        self._rdbuf = ""

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
            self.log_error()
            self.cleanup()
            os._exit(0)

    def daemonize(self):
        # pipes for process synchronization
        (r, w) = os.pipe()
        
        # build root folder
        root = os.path.normpath(self._root_dir)
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

        # create control socket
        self._ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._ctrl_sock.bind(CTRL_SOCK)
        self._ctrl_sock.listen(0)

        # let the parent process know that the daemonization is finished
        os.write(w, "\n")
        os.close(w)
        return 1

    def post_daemonize(self):
        pass

    def loop(self):
        while not self._stop:
            conn, addr = self._ctrl_sock.accept()
            conn.settimeout(5)
            while not self._stop:
                try:
                    msg = self.recv_msg(conn)
                except socket.timeout, e:
                    self.log_error()
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
        if self._log_level == DEBUG_LEVEL:
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
        print >>sys.stderr, "READY."
        while not self._stop:
            data = self.read_data()
            self.send_to_server(data)
            data = self.recv_from_server()
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
            agent = None, environment_setup = ""):
        self.root_dir = root_dir
        self.addr = (host, port)
        self.user = user
        self.agent = agent
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
        
        python_code = "from nepi.util import server;c=server.Forwarder(%r);\
                c.forward()" % (root_dir,)
        if host != None:
            self._process = popen_ssh_subprocess(python_code, host, port, 
                    user, agent,
                    environment_setup = self.environment_setup)
            # popen_ssh_subprocess already waits for readiness
            if self._process.poll():
                err = proc.stderr.read()
                raise RuntimeError("Client could not be reached: %s" % \
                        err)
        else:
            self._process = subprocess.Popen(
                    ["python", "-c", python_code],
                    stdin = subprocess.PIPE, 
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE
                )
                
        # Wait for the forwarder to be ready, otherwise nobody
        # will be able to connect to it
        helo = self._process.stderr.readline()
        if helo != 'READY.\n':
            raise AssertionError, "Expected 'Ready.', got %r: %s" % (helo,
                    helo + self._process.stderr.read())
        
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
            tty = False):
        """
        Executes a remote commands, returns ((stdout,stderr),process)
        """
        if TRACE:
            print "ssh", host, command
        
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
        args.append(command)

        # connects to the remote host and starts a remote connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        
        # attach tempfile object to the process, to make sure the file stays
        # alive until the process is finished with it
        proc._known_hosts = tmp_known_hosts
        
        out, err = proc.communicate(stdin)
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
 
def popen_ssh_subprocess(python_code, host, port, user, agent, 
        python_path = None,
        ident_key = None,
        server_key = None,
        tty = False,
        environment_setup = "",
        waitcommand = False):
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
        cmd += "python -c '"
        cmd += "import base64, os\n"
        cmd += "cmd = \"\"\n"
        cmd += "while True:\n"
        cmd += " cmd += os.read(0, 1)\n" # one byte from stdin
        cmd += " if cmd[-1] == \"\\n\": break\n"
        cmd += "cmd = base64.b64decode(cmd)\n"
        # Uncomment for debug
        #cmd += "os.write(2, \"Executing python code: %s\\n\" % cmd)\n"
        if not waitcommand:
            cmd += "os.write(1, \"OK\\n\")\n" # send a sync message
        cmd += "exec(cmd)\n"
        if waitcommand:
            cmd += "os.write(1, \"OK\\n\")\n" # send a sync message
        cmd += "'"
        
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

        # connects to the remote host and starts a remote rpyc connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        proc._known_hosts = tmp_known_hosts
        
        # send the command to execute
        os.write(proc.stdin.fileno(),
                base64.b64encode(python_code) + "\n")
        msg = os.read(proc.stdout.fileno(), 3)
        if msg != "OK\n":
            raise RuntimeError, "Failed to start remote python interpreter: \nout:\n%s%s\nerr:\n%s" % (
                msg, proc.stdout.read(), proc.stderr.read())
        return proc
 
