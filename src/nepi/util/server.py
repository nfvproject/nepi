# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et:ai:sts=4
import errno
import os
import select
import socket
import sys
import threading

CTRL_SOCK = "ctrl.sock"
STD_ERR = "stderr.log"
MAX_FD = 1024

STOP_MSG = "STOP"

class Server(object):
    def __init__(self):
        self.stop = False
        self.ctrl_sock = None

    def run(self):
        if self.daemonize():
            self.loop()
            self.cleanup()

    def daemonize(self):
        if True:
            return 1

        pid1 = os.fork()
        if pid1 > 0:
            return 0

        # Decouple from parent environment.
        #os.chdir(?)
        os.umask(0)
        os.setsid()

        # fork 2
        pid2 = os.fork()
        if pid2 > 0:
            return 0

        # close all open file descriptors.
        for fd in range(0, MAX_FD):
            try:
                os.close(fd)
            except OSError:
                pass

        # Redirect standard file descriptors.
        stdout = stderr = file(STD_ERR, "a", 0)
        stdin = open('/dev/null', 'r')
        os.dup2(stdin.fileno(), sys.stdin.fileno())
        os.dup2(stdout.fileno(), sys.stdout.fileno())
        os.dup2(stderr.fileno(), sys.stderr.fileno())
        return 1

    def loop(self):
        self.ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ctrl_sock.bind(CTRL_SOCK)
        self.ctrl_sock.listen(0)
        while not self.stop:
            print 'accept'
            conn, addr = self.ctrl_sock.accept()
            conn.settimeout(5)
            while True:
                try:
                    print 'recv'
                    data = conn.recv(1024)
                except socket.timeout, e:
                    print e
                    break
                    
                if data == STOP_MSG:
                    self.stop = True
                else:
                    conn.send("%s received" % data)
            conn.close()
        
    def cleanup(self):
        self.ctrl_sock.close()
        try:
            s.remove(CTRL_SOCK)
        except:
            pass

class Forwarder(object):
    def __init__(self):
        self.ctrl_sock = None

    def forward(self):
        self.connect()
        while True:
            msg = sys.stdin.readline()
            self.send(msg)
            reply = self.ctrl_sock.recv(1024)
            sys.stdout.write(reply)

    def send(self, msg):
        try:
            self.ctrl_sock.send(msg)
        except IOError, e:
            if e.errno == errno.EPIPE:
                self.connect()
                self.ctrl_sock.send(msg)
            else:
                raise e
    
    def connect(self):
        try:
            self.ctrl_sock.close()
        except:
            pass
        self.ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ctrl_sock.connect(CTRL_SOCK)

# Client
# import subprocess
# s = subprocess.Popen(['python' ,'-c' 'import server;c=server.Forwarder();c.forward()'], stdin = subprocess.PIPE)
# s.stdin.write('aaaa\n')
