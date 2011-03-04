#!/usr/bin/env python
# vim:ts=4:sw=4:et:ai:sts=4

import sys
import nepi.util.environ

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


