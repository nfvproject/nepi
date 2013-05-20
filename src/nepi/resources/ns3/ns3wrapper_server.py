"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

"""

class Server(object):
    def __init__(self, root_dir = ".", log_level = "ERROR", 
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
"""
