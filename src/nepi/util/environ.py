
import os, subprocess, os.path

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

def homepath(path, app='.nepi', mode = 0500, directory = False):
    home = os.environ.get('HOME')
    if home is None:
        home = os.path.join(os.sep, 'home', os.getlogin())
    
    path = os.path.join(home, app, path)
    if directory:
        dirname = path
    else:
        dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    
    return path

def find_testbed(testbed_id):
    mod_name = None
    
    # look for environment-specified testbeds
    if 'NEPI_TESTBEDS' in os.environ:
        try:
            # parse testbed map
            #   split space-separated items, filter empty items
            testbed_map = filter(bool,os.environ['NEPI_TESTBEDS'].strip().split(' '))
            #   split items, keep pairs only, build map
            testbed_map = dict([map(str.strip,i.split(':',1)) for i in testbed_map if ':' in i])
        except:
            import traceback, sys
            traceback.print_exc(file=sys.stderr)
            
            # ignore malformed environment
            testbed_map = {}
        
        mod_name = testbed_map.get(testbed_id)
    
    if mod_name is None:
        # no explicit map, load built-in testbeds
        mod_name = "nepi.testbeds.%s" % (testbed_id.lower())

    return mod_name

