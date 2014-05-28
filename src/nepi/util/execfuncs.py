#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

from nepi.util.sshfuncs import ProcStatus, STDOUT, log, shell_escape

import logging
import shlex
import subprocess

def lexec(command, 
        user = None, 
        sudo = False,
        env = None):
    """
    Executes a local command, returns ((stdout,stderr),process)
    """
    if env:
        export = ''
        for envkey, envval in env.iteritems():
            export += '%s=%s ' % (envkey, envval)
        command = "%s %s" % (export, command)

    if sudo:
        command = "sudo %s" % command
    
    # XXX: Doing 'su user' blocks waiting for a password on stdin
    #elif user:
    #    command = "su %s ; %s " % (user, command)

    proc = subprocess.Popen(command,
                shell = True, 
                stdout = subprocess.PIPE, 
                stderr = subprocess.PIPE)

    out = err = ""
    log_msg = "lexec - command %s " % command

    try:
        out, err = proc.communicate()
        log(log_msg, logging.DEBUG, out, err)
    except:
        log(log_msg, logging.ERROR, out, err)
        raise

    return ((out, err), proc)

def lcopy(source, dest, recursive = False):
    """
    Copies from/to localy.
    """
    
    args = ["cp"]
    if recursive:
        args.append("-r")
  
    if isinstance(source, list):
        args.extend(source)
    else:
        args.append(source)

    if isinstance(dest, list):
        args.extend(dest)
    else:
        args.append(dest)

    proc = subprocess.Popen(args, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE)

    out = err = ""
    command = " ".join(args)
    log_msg = " lcopy - command %s " % command

    try:
        out, err = proc.communicate()
        log(log_msg, logging.DEBUG, out, err)
    except:
        log(log_msg, logging.ERROR, out, err)
        raise

    return ((out, err), proc)
   
def lspawn(command, pidfile, 
        stdout = '/dev/null', 
        stderr = STDOUT, 
        stdin = '/dev/null', 
        home = None, 
        create_home = False, 
        sudo = False,
        user = None): 
    """
    Spawn a local command such that it will continue working asynchronously.
    
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
        'pidfile' : shell_escape(pidfile),
        'stdout' : stdout,
        'stderr' : stderr,
        'stdin' : stdin,
    }
    
    cmd = "%(create)s%(gohome)s rm -f %(pidfile)s ; %(sudo)s bash -c %(command)s " % {
            'command' : shell_escape(daemon_command),
            'sudo' : 'sudo -S' if sudo else '',
            'pidfile' : shell_escape(pidfile),
            'gohome' : 'cd %s ; ' % (shell_escape(home),) if home else '',
            'create' : 'mkdir -p %s ; ' % (shell_escape(home),) if create_home else '',
        }

    (out,err), proc = lexec(cmd)
    
    if proc.wait():
        raise RuntimeError, "Failed to set up application on host %s: %s %s" % (host, out,err,)

    return ((out,err), proc)

def lgetpid(pidfile):
    """
    Check the pidfile of a process spawned with remote_spawn.
    
    Parameters:
        pidfile: the pidfile passed to remote_span
        
    Returns:
        
        A (pid, ppid) tuple useful for calling remote_status and remote_kill,
        or None if the pidfile isn't valid yet (maybe the process is still starting).
    """

    (out,err), proc = lexec("cat %s" % pidfile )
        
    if proc.wait():
        return None
    
    if out:
        try:
            return map(int,out.strip().split(' ',1))
        except:
            # Ignore, many ways to fail that don't matter that much
            return None

def lstatus(pid, ppid): 
    """
    Check the status of a process spawned with remote_spawn.
    
    Parameters:
        pid/ppid: pid and parent-pid of the spawned process. See remote_check_pid
        
    Returns:
        
        One of NOT_STARTED, RUNNING, FINISHED
    """

    (out,err), proc = lexec(
        # Check only by pid. pid+ppid does not always work (especially with sudo) 
        " (( ps --pid %(pid)d -o pid | grep -c %(pid)d && echo 'wait')  || echo 'done' ) | tail -n 1" % {
            'ppid' : ppid,
            'pid' : pid,
        })
    
    if proc.wait():
        return ProcStatus.NOT_STARTED
    
    status = False
    if out:
        status = (out.strip() == 'wait')
    else:
        return ProcStatus.NOT_STARTED

    return ProcStatus.RUNNING if status else ProcStatus.FINISHED

def lkill(pid, ppid, sudo = False):
    """
    Kill a process spawned with lspawn.
    
    First tries a SIGTERM, and if the process does not end in 10 seconds,
    it sends a SIGKILL.
    
    Parameters:
        pid/ppid: pid and parent-pid of the spawned process. See remote_check_pid
        
        sudo: whether the command was run with sudo - careful killing like this.
    
    Returns:
        
        Nothing, should have killed the process
    """
    
    subkill = "$(ps --ppid %(pid)d -o pid h)" % { 'pid' : pid }
    cmd = """
SUBKILL="%(subkill)s" ;
%(sudo)s kill -- -%(pid)d $SUBKILL || /bin/true
%(sudo)s kill %(pid)d $SUBKILL || /bin/true
for x in 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 ; do 
    sleep 0.2 
    if [ `ps --pid %(pid)d -o pid | grep -c %(pid)d` == '0' ]; then
        break
    else
        %(sudo)s kill -- -%(pid)d $SUBKILL || /bin/true
        %(sudo)s kill %(pid)d $SUBKILL || /bin/true
    fi
    sleep 1.8
done
if [ `ps --pid %(pid)d -o pid | grep -c %(pid)d` != '0' ]; then
    %(sudo)s kill -9 -- -%(pid)d $SUBKILL || /bin/true
    %(sudo)s kill -9 %(pid)d $SUBKILL || /bin/true
fi
"""
    if nowait:
        cmd = "( %s ) >/dev/null 2>/dev/null </dev/null &" % (cmd,)

    (out,err),proc = lexec(
        cmd % {
            'ppid' : ppid,
            'pid' : pid,
            'sudo' : 'sudo -S' if sudo else '',
            'subkill' : subkill,
        })
    

