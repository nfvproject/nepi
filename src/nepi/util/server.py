#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import errno
import os
import resource
import select
import socket
import sys
import subprocess
import threading
import time
import traceback
import signal

CTRL_SOCK = "ctrl.sock"
STD_ERR = "stderr.log"
MAX_FD = 1024

STOP_MSG = "STOP"

ERROR_LEVEL = 0
DEBUG_LEVEL = 1

if hasattr(os, "devnull"):
    DEV_NULL = os.devnull
else:
    DEV_NULL = "/dev/null"

class Server(object):
    def __init__(self, root_dir = ".", log_level = ERROR_LEVEL):
        self._root_dir = root_dir
        self._stop = False
        self._ctrl_sock = None
        self._log_level = log_level

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

        pid1 = os.fork()
        if pid1 > 0:
            os.close(w)
            os.read(r, 1)
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
        data = ""
        while True:
            try:
                chunk = conn.recv(1024)
            except OSError, e:
                if e.errno != errno.EINTR:
                    raise
                if chunk == '':
                    continue
            if chunk:
                data += chunk
                if chunk[-1] == "\n":
                    break
            else:
                # empty chunk = EOF
                break
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
        except IOError, e:
            if e.errno == errno.EPIPE:
                self.connect()
                self._ctrl_sock.send(data)
            else:
                raise e
        encoded = data.rstrip() 
        msg = base64.b64decode(encoded)
        if msg == STOP_MSG:
            self._stop = True

    def recv_from_server(self):
        data = ""
        while True:
            try:
                chunk = self._ctrl_sock.recv(1024)
            except OSError, e:
                if e.errno != errno.EINTR:
                    raise
                if chunk == '':
                    continue
            data += chunk
            if chunk[-1] == "\n":
                break
        return data
 
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
            agent = None):
        self.root_dir = root_dir
        self.addr = (host, port)
        self.user = user
        self.agent = agent
        self._stopped = False
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
                    user, agent)
            # popen_ssh_subprocess already waits for readiness
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
            raise AssertionError, "Expected 'Ready.', got %r" % (helo,)
        
        if self._process.poll():
            err = self._process.stderr.read()
            raise RuntimeError("Client could not be executed: %s" % \
                    err)

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

    def read_reply(self):
        data = self._process.stdout.readline()
        encoded = data.rstrip() 
        return base64.b64decode(encoded)

def popen_ssh_subprocess(python_code, host, port, user, agent, 
        python_path = None):
        if python_path:
            python_path.replace("'", r"'\''")
            cmd = """PYTHONPATH="$PYTHONPATH":'%s' """ % python_path
        else:
            cmd = ""
        # Uncomment for debug (to run everything under strace)
        # We had to verify if strace works (cannot nest them)
        #cmd += "if strace echo >/dev/null 2>&1; then CMD='strace -ff -tt -s 200 -o strace.out'; else CMD=''; fi\n"
        #cmd += "$CMD "
        #if self.mode == MODE_SSH:
        #    cmd += "strace -f -tt -s 200 -o strace$$.out "
        cmd += "python -c '"
        cmd += "import base64, os\n"
        cmd += "cmd = \"\"\n"
        cmd += "while True:\n"
        cmd += " cmd += os.read(0, 1)\n" # one byte from stdin
        cmd += " if cmd[-1] == \"\\n\": break\n"
        cmd += "cmd = base64.b64decode(cmd)\n"
        # Uncomment for debug
        #cmd += "os.write(2, \"Executing python code: %s\\n\" % cmd)\n"
        cmd += "os.write(1, \"OK\\n\")\n" # send a sync message
        cmd += "exec(cmd)\n'"

        args = ['ssh',
                # Don't bother with localhost. Makes test easier
                '-o', 'NoHostAuthenticationForLocalhost=yes',
                '-l', user, host]
        if agent:
            args.append('-A')
        if port:
            args.append('-p%d' % port)
        args.append(cmd)

        # connects to the remote host and starts a remote rpyc connection
        proc = subprocess.Popen(args, 
                stdout = subprocess.PIPE,
                stdin = subprocess.PIPE, 
                stderr = subprocess.PIPE)
        # send the command to execute
        os.write(proc.stdin.fileno(),
                base64.b64encode(python_code) + "\n")
        msg = os.read(proc.stdout.fileno(), 3)
        if msg != "OK\n":
            raise RuntimeError("Failed to start remote python interpreter")
        return proc
 
