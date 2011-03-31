#!/usr/bin/env python

import nepi.util.environ
import ctypes
import imp
import sys

# Unittest from Python 2.6 doesn't have these decorators
def _bannerwrap(f, text):
    name = f.__name__
    def banner(*args, **kwargs):
        sys.stderr.write("*** WARNING: Skipping test %s: `%s'\n" %
                (name, text))
        return None
    return banner
def skip(text):
    return lambda f: _bannerwrap(f, text)
def skipUnless(cond, text):
    return (lambda f: _bannerwrap(f, text)) if not cond else lambda f: f
def skipIf(cond, text):
    return (lambda f: _bannerwrap(f, text)) if cond else lambda f: f

def ns3_bindings_path():
    if "NEPI_NS3BINDINGS" in os.environ:
        return os.environ["NEPI_NS3BINDINGS"]
    return None

def ns3_library_path():
    if "NEPI_NS3LIBRARY" in os.environ:
        return os.environ["NEPI_NS3LIBRARY"]
    return None

def ns3_usable():
    if ns3_library_path():
        try:
            ctypes.CDLL(ns3_library_path(), ctypes.RTLD_GLOBAL)
        except:
            return False

    if ns3_bindings_path():
        sys.path.insert(0, ns3_bindings_path())

    try:
        found = imp.find_module('ns3')
        module = imp.load_module('ns3', *found)
    except ImportError:
        return False
    finally:
        if ns3_bindings_path():
            del sys.path[0]

    return True


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

# SSH stuff

import os, os.path, re, signal, shutil, socket, subprocess, tempfile
def gen_ssh_keypair(filename):
    ssh_keygen = nepi.util.environ.find_bin_or_die("ssh-keygen")
    args = [ssh_keygen, '-q', '-N', '', '-f', filename]
    assert subprocess.Popen(args).wait() == 0
    return filename, "%s.pub" % filename

def add_key_to_agent(filename):
    ssh_add = nepi.util.environ.find_bin_or_die("ssh-add")
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
    ssh_agent = nepi.util.environ.find_bin_or_die("ssh-agent")
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
    ssh_agent = nepi.util.environ.find_bin_or_die("ssh-agent")
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
        if 'PYTHONPATH' in os.environ:
            environ['PYTHONPATH'] = ":".join(map(os.path.realpath, 
                os.environ['PYTHONPATH'].split(":")))
        if 'NEPI_NS3BINDINGS' in os.environ:
            environ['NEPI_NS3BINDINGS'] = \
                    os.path.realpath(os.environ['NEPI_NS3BINDINGS'])
        if 'NEPI_NS3LIBRARY' in os.environ:
            environ['NEPI_NS3LIBRARY'] = \
                    os.path.realpath(os.environ['NEPI_NS3LIBRARY'])

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

