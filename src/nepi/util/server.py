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

CTRL_SOCK = "ctrl.sock"
STD_ERR = "stderr.log"
MAX_FD = 1024

STOP_MSG = "STOP"

class Server(object):
    def __init__(self, root_dir = "."):
        self._root_dir = root_dir
        self._stop = False
        self._ctrl_sock = None
        self._stderr = None 

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
            raise

    def daemonize(self):
        pid1 = os.fork()
        if pid1 > 0:
            # we do os.waitpid to avoid leaving a <defunc> (zombie) process
            os.waitpid(pid1, 0)
            # return 0 to inform the caller method that this is not the 
            # daemonized process
            return 0

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
        for fd in range(2, MAX_FD):
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
                    try:
                        reply = self.stop_action()
                    except:
                        self.log_error()
                    self.send_reply(conn, reply)
                    break
                else:
                    try:
                        reply = self.reply_action(msg)
                    except:
                        self.log_error()
                    self.send_reply(conn, reply)
            conn.close()

    def recv_msg(self, conn):
       data = conn.recv(1024)
       decoded = base64.b64decode(data)
       return decoded.rstrip()

    def send_reply(self, conn, reply):
       encoded = base64.b64encode(reply)
       conn.send("%s\n" % encoded)
       
    def cleanup(self):
        try:
            self._ctrl_sock.close()
            os.remove(CTRL_SOCK)
        except e:
            self.log_error()

    def stop_action(self):
        return "Stopping server"

    def reply_action(self, msg):
        return "Reply to: %s" % msg

    def log_error(self, error = None):
        if error == None:
            import traceback
            error = "%s\n" %  traceback.format_exc()
        sys.stderr.write(error)
        return error

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
        return self._ctrl_sock.recv(1024)
 
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
                stdout = subprocess.PIPE, 
                env = os.environ)

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

