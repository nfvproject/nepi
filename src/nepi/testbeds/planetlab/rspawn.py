# Utility library for spawning remote asynchronous tasks
from nepi.util import server
import getpass

class STDOUT: 
    """
    Special value that when given to remote_spawn in stderr causes stderr to 
    redirect to whatever stdout was redirected to.
    """

class RUNNING:
    """
    Process is still running
    """

class FINISHED:
    """
    Process is finished
    """

class NOT_STARTED:
    """
    Process hasn't started running yet (this should be very rare)
    """

def remote_spawn(command, pidfile, stdout='/dev/null', stderr=STDOUT, stdin='/dev/null', home=None, create_home=False, sudo=False,
        host = None, port = None, user = None, agent = None, 
        ident_key = None, server_key = None,
        tty = False):
    """
    Spawn a remote command such that it will continue working asynchronously.
    
    Parameters:
        command: the command to run - it should be a single line.
        
        pidfile: path of a (ideally unique to this task) pidfile for tracking the process.
        
        stdout: path of a file to redirect standard output to - must be a string.
            Defaults to /dev/null
        stderr: path of a file to redirect standard error to - string or the special STDOUT value
            to redirect to the same file stdout was redirected to. Defaults to STDOUT.
        stdin: path of a file with input to be piped into the command's standard input
        
        home: path of a folder to use as working directory - should exist, unless you specify create_home
        
        create_home: if True, the home folder will be created first with mkdir -p
        
        sudo: whether the command needs to be executed as root
        
        host/port/user/agent/ident_key: see nepi.util.server.popen_ssh_command
    
    Returns:
        (stdout, stderr), process
        
        Of the spawning process, which only captures errors at spawning time.
        Usually only useful for diagnostics.
    """
    # Start process in a "daemonized" way, using nohup and heavy
    # stdin/out redirection to avoid connection issues
    if stderr is STDOUT:
        stderr = '&1'
    else:
        stderr = ' ' + stderr
    
    daemon_command = '{ { %(command)s  > %(stdout)s 2>%(stderr)s < %(stdin)s & } ; echo $! 1 > %(pidfile)s ; }' % {
        'command' : command,
        'pidfile' : server.shell_escape(pidfile),
        
        'stdout' : stdout,
        'stderr' : stderr,
        'stdin' : stdin,
    }
    
    cmd = "%(create)s%(gohome)s rm -f %(pidfile)s ; %(sudo)s nohup bash -c %(command)s " % {
            'command' : server.shell_escape(daemon_command),
            
            'sudo' : 'sudo -S' if sudo else '',
            
            'pidfile' : server.shell_escape(pidfile),
            'gohome' : 'cd %s ; ' % (server.shell_escape(home),) if home else '',
            'create' : 'mkdir -p %s ; ' % (server.shell_escape,) if create_home else '',
        }
    (out,err),proc = server.popen_ssh_command(
        cmd,
        host = host,
        port = port,
        user = user,
        agent = agent,
        ident_key = ident_key,
        server_key = server_key,
        tty = tty 
        )
    
    if proc.wait():
        raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

    return (out,err),proc

def remote_check_pid(pidfile,
        host = None, port = None, user = None, agent = None, 
        ident_key = None, server_key = None):
    """
    Check the pidfile of a process spawned with remote_spawn.
    
    Parameters:
        pidfile: the pidfile passed to remote_span
        
        host/port/user/agent/ident_key: see nepi.util.server.popen_ssh_command
    
    Returns:
        
        A (pid, ppid) tuple useful for calling remote_status and remote_kill,
        or None if the pidfile isn't valid yet (maybe the process is still starting).
    """

    (out,err),proc = server.popen_ssh_command(
        "cat %(pidfile)s" % {
            'pidfile' : pidfile,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        ident_key = ident_key,
        server_key = server_key
        )
        
    if proc.wait():
        return None
    
    if out:
        try:
            return map(int,out.strip().split(' ',1))
        except:
            # Ignore, many ways to fail that don't matter that much
            return None


def remote_status(pid, ppid, 
        host = None, port = None, user = None, agent = None, 
        ident_key = None, server_key = None):
    """
    Check the status of a process spawned with remote_spawn.
    
    Parameters:
        pid/ppid: pid and parent-pid of the spawned process. See remote_check_pid
        
        host/port/user/agent/ident_key: see nepi.util.server.popen_ssh_command
    
    Returns:
        
        One of NOT_STARTED, RUNNING, FINISHED
    """

    (out,err),proc = server.popen_ssh_command(
        "ps --ppid %(ppid)d -o pid | grep -c %(pid)d ; true" % {
            'ppid' : ppid,
            'pid' : pid,
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        ident_key = ident_key,
        server_key = server_key
        )
    
    if proc.wait():
        return NOT_STARTED
    
    status = False
    if out:
        try:
            status = bool(int(out.strip()))
        except:
            # Ignore, many ways to fail that don't matter that much
            return NOT_STARTED
    return RUNNING if status else FINISHED
    

def remote_kill(pid, ppid, sudo = False,
        host = None, port = None, user = None, agent = None, 
        ident_key = None, server_key = None,
        nowait = False):
    """
    Kill a process spawned with remote_spawn.
    
    First tries a SIGTERM, and if the process does not end in 10 seconds,
    it sends a SIGKILL.
    
    Parameters:
        pid/ppid: pid and parent-pid of the spawned process. See remote_check_pid
        
        sudo: whether the command was run with sudo - careful killing like this.
        
        host/port/user/agent/ident_key: see nepi.util.server.popen_ssh_command
    
    Returns:
        
        Nothing, should have killed the process
    """
    
    cmd = """
%(sudo)s kill %(pid)d
for x in 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 ; do 
    sleep 0.2 
    if [ `ps --ppid %(ppid)d -o pid | grep -c %(pid)d` == '0' ]; then
        break
    fi
    sleep 1.8
done
if [ `ps --ppid %(ppid)d -o pid | grep -c %(pid)d` != '0' ]; then
    %(sudo)s kill -9 %(pid)d
fi
"""
    if nowait:
        cmd = "{ %s } >/dev/null 2>/dev/null </dev/null &" % (cmd,)

    (out,err),proc = server.popen_ssh_command(
        cmd % {
            'ppid' : ppid,
            'pid' : pid,
            'sudo' : 'sudo -S' if sudo else ''
        },
        host = host,
        port = port,
        user = user,
        agent = agent,
        ident_key = ident_key,
        server_key = server_key
        )
    
    # wait, don't leave zombies around
    proc.wait()
    


