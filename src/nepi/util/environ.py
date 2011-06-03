# vim:ts=4:sw=4:et:ai:sts=4

import os, subprocess

__all__ =  ["python", "ssh_path"]
__all__ += ["rsh", "tcpdump_path", "sshd_path"]
__all__ += ["execute", "backticks"]

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

