#!/usr/bin/env python

from neco.util.sshfuncs import *

import getpass
import unittest
import os
import subprocess
import re
import signal
import shutil
import socket
import subprocess
import tempfile
import time

def find_bin(name, extra_path = None):
    search = []
    if "PATH" in os.environ:
        search += os.environ["PATH"].split(":")
    for pref in ("/", "/usr/", "/usr/local/"):
        for d in ("bin", "sbin"):
            search.append(pref + d)
    if extra_path:
        search += extra_path

    for d in search:
            try:
                os.stat(d + "/" + name)
                return d + "/" + name
            except OSError, e:
                if e.errno != os.errno.ENOENT:
                    raise
    return None

def find_bin_or_die(name, extra_path = None):
    r = find_bin(name)
    if not r:
        raise RuntimeError(("Cannot find `%s' command, impossible to " +
                "continue.") % name)
    return r

def gen_ssh_keypair(filename):
    ssh_keygen = find_bin_or_die("ssh-keygen")
    args = [ssh_keygen, '-q', '-N', '', '-f', filename]
    assert subprocess.Popen(args).wait() == 0
    return filename, "%s.pub" % filename

def add_key_to_agent(filename):
    ssh_add = find_bin_or_die("ssh-add")
    args = [ssh_add, filename]
    null = file("/dev/null", "w")
    assert subprocess.Popen(args, stderr = null).wait() == 0
    null.close()

def get_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    return port

_SSH_CONF = """ListenAddress 127.0.0.1:%d
Protocol 2
HostKey %s
UsePrivilegeSeparation no
PubkeyAuthentication yes
PasswordAuthentication no
AuthorizedKeysFile %s
UsePAM no
AllowAgentForwarding yes
PermitRootLogin yes
StrictModes no
PermitUserEnvironment yes
"""

def gen_sshd_config(filename, port, server_key, auth_keys):
    conf = open(filename, "w")
    text = _SSH_CONF % (port, server_key, auth_keys)
    conf.write(text)
    conf.close()
    return filename

def gen_auth_keys(pubkey, output, environ):
    #opts = ['from="127.0.0.1/32"'] # fails in stupid yans setup
    opts = []
    for k, v in environ.items():
        opts.append('environment="%s=%s"' % (k, v))

    lines = file(pubkey).readlines()
    pubkey = lines[0].split()[0:2]
    out = file(output, "w")
    out.write("%s %s %s\n" % (",".join(opts), pubkey[0], pubkey[1]))
    out.close()
    return output

def start_ssh_agent():
    ssh_agent = find_bin_or_die("ssh-agent")
    proc = subprocess.Popen([ssh_agent], stdout = subprocess.PIPE)
    (out, foo) = proc.communicate()
    assert proc.returncode == 0
    d = {}
    for l in out.split("\n"):
        match = re.search("^(\w+)=([^ ;]+);.*", l)
        if not match:
            continue
        k, v = match.groups()
        os.environ[k] = v
        d[k] = v
    return d

def stop_ssh_agent(data):
    # No need to gather the pid, ssh-agent knows how to kill itself; after we
    # had set up the environment
    ssh_agent = find_bin_or_die("ssh-agent")
    null = file("/dev/null", "w")
    proc = subprocess.Popen([ssh_agent, "-k"], stdout = null)
    null.close()
    assert proc.wait() == 0
    for k in data:
        del os.environ[k]

class test_environment(object):
    def __init__(self):
        sshd = find_bin_or_die("sshd")
        environ = {}
        self.dir = tempfile.mkdtemp()
        self.server_keypair = gen_ssh_keypair(
                os.path.join(self.dir, "server_key"))
        self.client_keypair = gen_ssh_keypair(
                os.path.join(self.dir, "client_key"))
        self.authorized_keys = gen_auth_keys(self.client_keypair[1],
                os.path.join(self.dir, "authorized_keys"), environ)
        self.port = get_free_port()
        self.sshd_conf = gen_sshd_config(
                os.path.join(self.dir, "sshd_config"),
                self.port, self.server_keypair[0], self.authorized_keys)

        self.sshd = subprocess.Popen([sshd, '-q', '-D', '-f', self.sshd_conf])
        self.ssh_agent_vars = start_ssh_agent()
        add_key_to_agent(self.client_keypair[0])

    def __del__(self):
        if self.sshd:
            os.kill(self.sshd.pid, signal.SIGTERM)
            self.sshd.wait()
        if self.ssh_agent_vars:
            stop_ssh_agent(self.ssh_agent_vars)
        shutil.rmtree(self.dir)

class SSHfuncsTestCase(unittest.TestCase):
    def test_rexec(self):
        env = test_environment()
        user = getpass.getuser()
        host = "localhost" 

        command = "hostname"

        plocal = subprocess.Popen(command, stdout=subprocess.PIPE, 
                stdin=subprocess.PIPE)
        outlocal, errlocal = plocal.communicate()

        (outremote, errrmote), premote = rexec(command, host, user, 
                port = env.port, agent = True)

        self.assertEquals(outlocal, outremote)

    def test_rcopy(self):
        env = test_environment()
        user = getpass.getuser()
        host = "localhost"

        # create some temp files and directories to copy
        dirpath = tempfile.mkdtemp()
        f = tempfile.NamedTemporaryFile(dir=dirpath, delete=False)
        f.close()
      
        f1 = tempfile.NamedTemporaryFile(delete=False)
        f1.close()
        f1.name

        source = [dirpath, f1.name]
        destdir = tempfile.mkdtemp()
        dest = "%s@%s:%s" % (user, host, destdir)
        rcopy(source, dest, port = env.port, agent = True)

        files = []
        def recls(files, dirname, names):
            files.extend(names)
        os.path.walk(destdir, recls, files)
        
        origfiles = map(lambda s: os.path.basename(s), [dirpath, f.name, f1.name])

        self.assertEquals(sorted(origfiles), sorted(files))

    def test_rproc_manage(self):
        env = test_environment()
        user = getpass.getuser()
        host = "localhost" 
        command = "ping localhost"
        
        f = tempfile.NamedTemporaryFile(delete=False)
        pidfile = f.name 

        (out,err), proc = rspawn(
                command, 
                pidfile,
                host = host,
                user = user,
                port = env.port,
                agent = True)

        time.sleep(2)

        (pid, ppid) = rcheck_pid(pidfile,
                host = host,
                user = user,
                port = env.port,
                agent = True)

        status = rstatus(pid, ppid,
                host = host,
                user = user, 
                port = env.port, 
                agent = True)

        self.assertEquals(status, RUNNING)

        rkill(pid, ppid,
                host = host,
                user = user, 
                port = env.port, 
                agent = True)

        status = rstatus(pid, ppid,
                host = host,
                user = user, 
                port = env.port, 
                agent = True)
        
        self.assertEquals(status, FINISHED)


if __name__ == '__main__':
    unittest.main()

