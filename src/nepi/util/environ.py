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

import ctypes
import imp
import sys

import os, os.path, re, signal, shutil, socket, subprocess, tempfile

__all__ =  ["python", "ssh_path"]
__all__ += ["rsh", "tcpdump_path", "sshd_path"]
__all__ += ["execute", "backticks"]


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

ssh_path = find_bin_or_die("ssh")
python_path = find_bin_or_die("python")

# Optional tools
rsh_path = find_bin("rsh")
tcpdump_path = find_bin("tcpdump")
sshd_path = find_bin("sshd")

def execute(cmd):
    # FIXME: create a global debug variable
    #print "[pid %d]" % os.getpid(), " ".join(cmd)
    null = open("/dev/null", "r+")
    p = subprocess.Popen(cmd, stdout = null, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError("Error executing `%s': %s" % (" ".join(cmd), err))

def backticks(cmd):
    p = subprocess.Popen(cmd, stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError("Error executing `%s': %s" % (" ".join(cmd), err))
    return out


# SSH stuff

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

