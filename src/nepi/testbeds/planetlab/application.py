#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import plcapi
import operator
import os
import os.path
import nepi.util.server as server
import cStringIO
import subprocess

from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

class Application(object):
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        
        # Attributes
        self.command = None
        self.sudo = False
        
        self.stdin = None
        self.stdout = None
        self.stderr = None
        
        # Those are filled when the app is configured
        self.home_path = None
        self.ident_path = None
        self.slicename = None
        
        # Those are filled when an actual node is connected
        self.node = None
        
        # Those are filled when the app is started
        #   Having both pid and ppid makes it harder
        #   for pid rollover to induce tracking mistakes
        self._started = False
        self._pid = None
        self._ppid = None
    
    def __str__(self):
        return "%s<command:%s%s>" % (
            self.__class__.__name__,
            "sudo " if self.sudo else "",
            self.command,
        )
    
    def validate(self):
        if self.home_path is None:
            raise AssertionError, "Misconfigured application: missing home path"
        if self.ident_path is None or not os.access(self.ident_path, os.R_OK):
            raise AssertionError, "Misconfigured application: missing slice SSH key"
        if self.node is None:
            raise AssertionError, "Misconfigured application: unconnected node"
        if self.node.hostname is None:
            raise AssertionError, "Misconfigured application: misconfigured node"
        if self.slicename is None:
            raise AssertionError, "Misconfigured application: unspecified slice"

    def start(self):
        # Start process in a "daemonized" way, using nohup and heavy
        # stdin/out redirection to avoid connection issues
        (out,err),proc = server.popen_ssh_command(
            "cd %(home)s ; rm -f ./pid ; ( echo $$ $PPID > ./pid ; %(sudo)s nohup %(command)s > %(stdout)s 2> %(stderr)s < %(stdin)s ) &" % {
                'home' : server.shell_escape(self.home_path),
                'command' : self.command,
                'stdout' : 'stdout' if self.stdout else '/dev/null' ,
                'stderr' : 'stderr' if self.stderr else '/dev/null' ,
                'stdin' : 'stdin' if self.stdin is not None else '/dev/null' ,
                'sudo' : 'sudo' if self.sudo else '',
            },
            host = self.node.hostname,
            port = None,
            user = self.slicename,
            agent = None,
            ident_key = self.ident_path
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

        self._started = True

    def checkpid(self):            
        # Get PID/PPID
        # NOTE: wait a bit for the pidfile to be created
        if self._started and not self._pid or not self._ppid:
            (out,err),proc = server.popen_ssh_command(
                "cat %(pidfile)s" % {
                    'pidfile' : server.shell_escape(os.path.join(self.home_path,'pid')),
                },
                host = self.node.hostname,
                port = None,
                user = self.slicename,
                agent = None,
                ident_key = self.ident_path
                )
            if out:
                try:
                    self._pid, self._ppid = map(int,out.strip().split(' ',1))
                except:
                    # Ignore, many ways to fail that don't matter that much
                    pass
    
    def status(self):
        self.checkpid()
        if not self._started:
            return STATUS_NOT_STARTED
        elif not self._pid or not self._ppid:
            return STATUS_NOT_STARTED
        else:
            (out,err),proc = server.popen_ssh_command(
                "ps --ppid $(ppid)d -o pid | grep -c $(pid)d" % {
                    'ppid' : self._ppid,
                    'pid' : self._pid,
                },
                host = self.node.hostname,
                port = None,
                user = self.slicename,
                agent = None,
                ident_key = self.ident_path
                )
            
            status = False
            if out:
                try:
                    status = bool(int(out.strip()))
                except:
                    # Ignore, many ways to fail that don't matter that much
                    pass
            return STATUS_RUNNING if status else STATUS_FINISHED
    
    def kill(self):
        status = self.status()
        if status == STATUS_RUNNING:
            # kill by ppid+pid - SIGTERM first, then try SIGKILL
            (out,err),proc = server.popen_ssh_command(
                """
kill $(pid)d $(ppid)d 
for x in 1 2 3 4 5 6 7 8 9 0 ; do 
    sleep 0.1 
    if [ `ps --pid $(ppid)d -o pid | grep -c $(pid)d` == `0` ]; then
        break
    fi
    sleep 0.9
done
if [ `ps --pid $(ppid)d -o pid | grep -c $(pid)d` != `0` ]; then
    kill -9 $(pid)d $(ppid)d
fi
""" % {
                    'ppid' : self._ppid,
                    'pid' : self._pid,
                },
                host = self.node.hostname,
                port = None,
                user = self.slicename,
                agent = None,
                ident_key = self.ident_path
                )
            
            status = False
            if out:
                try:
                    status = bool(int(out.strip()))
                except:
                    # Ignore, many ways to fail that don't matter that much
                    pass
            return STATUS_RUNNING if status else STATUS_FINISHED
    
    def remote_trace_path(self, whichtrace):
        if whichtrace in ('stdout','stderr'):
            tracefile = os.path.join(self.home_path, whichtrace)
        else:
            tracefile = None
        
        return tracefile
    
    def sync_trace(self, local_dir, whichtrace):
        tracefile = self.remote_trace_path(whichtrace)
        if not tracefile:
            return None
        
        local_path = os.path.join(local_dir, tracefile)
        
        # create parent local folders
        proc = subprocess.Popen(
            ["mkdir", "-p", os.path.dirname(local_path)],
            stdout = open("/dev/null","w"),
            stdin = open("/dev/null","r"))

        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        # sync files
        (out,err),proc = server.popen_scp(
            '%s@%s:%s' % (self.slicename, self.node.hostname, 
                tracefile),
            local_path,
            port = None,
            agent = None,
            ident_key = self.ident_path
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        return local_path
    

    def setup(self):
        # Make sure all the paths are created where 
        # they have to be created for deployment
        (out,err),proc = server.popen_ssh_command(
            "mkdir -p %s" % (server.shell_escape(self.home_path),),
            host = self.node.hostname,
            port = None,
            user = self.slicename,
            agent = None,
            ident_key = self.ident_path
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)
        
        
        if self.stdin:
            # Write program input
            (out,err),proc = server.popen_scp(
                cStringIO.StringIO(self.stdin),
                '%s@%s:%s' % (self.slicename, self.node.hostname, 
                    os.path.join(self.home_path, 'stdin') ),
                port = None,
                agent = None,
                ident_key = self.ident_path
                )
            
            if proc.wait():
                raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

        
