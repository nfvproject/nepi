#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import errno
import os
import select
import socket
import sys
import subprocess
import threading
from time import strftime
import traceback

CTRL_SOCK = "ctrl.sock"
STD_ERR = "stderr.log"
MAX_FD = 1024

STOP_MSG = "STOP"

ERROR_LEVEL = 0
DEBUG_LEVEL = 1

class Server(object):
    def __init__(self, root_dir = "."):
        self._root_dir = root_dir
        self._stop = False
        self._ctrl_sock = None
        self._stderr = None
        self._log_level = ERROR_LEVEL

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
        for fd in range(3, MAX_FD):
            if fd != w:
                try:
                    os.close(fd)
                except OSError:
                    pass

        # Redirect standard file descriptors.
        self._stderr = stdout = file(STD_ERR, "a", 0)
        stdin = open('/dev/null', 'r')
        os.dup2(stdin.fileno(), sys.stdin.fileno())
        os.dup2(stdout.fileno(), sys.stdout.fileno())
        os.dup2(self._stderr.fileno(), sys.stderr.fileno())
        # let the parent process know that the daemonization is finished
        os.write(w, "\n")
        os.close(w)
        return 1

    def post_daemonize(self):
        pass

    def loop(self):
        self._ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._ctrl_sock.bind(CTRL_SOCK)
        self._ctrl_sock.listen(0)
        while not self._stop:
            conn, addr = self._ctrl_sock.accept()
            conn.settimeout(5)
            while True:
                try:
                    msg = self.recv_msg(conn)
                except socket.timeout, e:
                    break
                    
                if msg == STOP_MSG:
                    self._stop = True
                    reply = self.stop_action()
                else:
                    reply = self.reply_action(msg)
                self.send_reply(conn, reply)
            conn.close()

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
            data += chunk
            if chunk[-1] == "\n":
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

    def set_error_log_level(self):
        self._log_level = ERROR_LEVEL

    def set_debug_log_level(self):
        self._log_level = DEBUG_LEVEL

    def log_error(self, text = None):
        if text == None:
            text = traceback.format_exc()
        date = strftime("%Y-%m-%d %H:%M:%S")
        sys.stderr.write("ERROR: %s\n%s\n" % (date, text))
        return text

    def log_debug(self, text):
        if self._log_level == DEBUG_LEVEL:
            date = strftime("%Y-%m-%d %H:%M:%S")
            sys.stderr.write("DEBUG: %s\n%s\n" % (date, text))

class Forwarder(object):
    def __init__(self, root_dir = "."):
        self._ctrl_sock = None
        self._root_dir = root_dir
        self._stop = False

    def forward(self):
        self.connect()
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
    def __init__(self, root_dir = "."):
        self._process = subprocess.Popen(
                ["python", "-c", 
                "from nepi.util import server;c=server.Forwarder('%s');\
                        c.forward()" % root_dir
                ],
                stdin = subprocess.PIPE, 
                stdout = subprocess.PIPE)

    def send_msg(self, msg):
        encoded = base64.b64encode(msg)
        data = "%s\n" % encoded
        self._process.stdin.write(data)

    def send_stop(self):
        self.send_msg(STOP_MSG)

    def read_reply(self):
        data = self._process.stdout.readline()
        encoded = data.rstrip() 
        return base64.b64decode(encoded)

