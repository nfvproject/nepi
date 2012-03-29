# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import plcapi
import operator
import os
import os.path
import sys
import nepi.util.server as server
import cStringIO
import subprocess
import rspawn
import random
import time
import socket
import threading
import logging
import re

from nepi.util.constants import ApplicationStatus as AS

class Dependency(object):
    """
    A Dependency is in every respect like an application.
    
    It depends on some packages, it may require building binaries, it must deploy
    them...
    
    But it has no command. Dependencies aren't ever started, or stopped, and have
    no status.
    """

    TRACES = ('buildlog')

    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        
        # Attributes
        self.command = None
        self.sudo = False
        
        self.build = None
        self.install = None
        self.depends = None
        self.buildDepends = None
        self.sources = None
        self.rpmFusion = False
        self.env = {}
        
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.buildlog = None
        
        self.add_to_path = True
        
        # Those are filled when the app is configured
        self.home_path = None
        
        # Those are filled when an actual node is connected
        self.node = None
        
        # Those are filled when the app is started
        #   Having both pid and ppid makes it harder
        #   for pid rollover to induce tracking mistakes
        self._started = False
        self._setup = False
        self._setuper = None
        self._pid = None
        self._ppid = None

        # Spanning tree deployment
        self._master = None
        self._master_passphrase = None
        self._master_prk = None
        self._master_puk = None
        self._master_token = os.urandom(8).encode("hex")
        self._build_pid = None
        self._build_ppid = None
        
        # Logging
        self._logger = logging.getLogger('nepi.testbeds.planetlab')
        
    
    def __str__(self):
        return "%s<%s>" % (
            self.__class__.__name__,
            ' '.join(filter(bool,(self.depends, self.sources)))
        )
    
    def validate(self):
        if self.home_path is None:
            raise AssertionError, "Misconfigured application: missing home path"
        if self.node.ident_path is None or not os.access(self.node.ident_path, os.R_OK):
            raise AssertionError, "Misconfigured application: missing slice SSH key"
        if self.node is None:
            raise AssertionError, "Misconfigured application: unconnected node"
        if self.node.hostname is None:
            raise AssertionError, "Misconfigured application: misconfigured node"
        if self.node.slicename is None:
            raise AssertionError, "Misconfigured application: unspecified slice"
    
    def check_bad_host(self, out, err):
        """
        Called whenever an operation fails, it's given the output to be checked for
        telltale signs of unhealthy hosts.
        """
        return False
    
    def remote_trace_path(self, whichtrace):
        if whichtrace in self.TRACES:
            tracefile = os.path.join(self.home_path, whichtrace)
        else:
            tracefile = None
        
        return tracefile

    def remote_trace_name(self, whichtrace):
        if whichtrace in self.TRACES:
            return whichtrace
        return None

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
            raise RuntimeError, "Failed to synchronize trace"
        
        # sync files
        try:
            self._popen_scp(
                '%s@%s:%s' % (self.node.slicename, self.node.hostname,
                    tracefile),
                local_path
                )
        except RuntimeError, e:
            raise RuntimeError, "Failed to synchronize trace: %s %s" \
                    % (e.args[0], e.args[1],)
        
        return local_path
    
    def recover(self):
        # We assume a correct deployment, so recovery only
        # means we mark this dependency as deployed
        self._setup = True

    def setup(self):
        self._logger.info("Setting up %s", self)
        self._make_home()
        self._launch_build()
        self._finish_build()
        self._setup = True
    
    def async_setup(self):
        if not self._setuper:
            def setuper():
                try:
                    self.setup()
                except:
                    self._setuper._exc.append(sys.exc_info())
            self._setuper = threading.Thread(
                target = setuper)
            self._setuper._exc = []
            self._setuper.start()
    
    def async_setup_wait(self):
        if not self._setup:
            self._logger.info("Waiting for %s to be setup", self)
            if self._setuper:
                self._setuper.join()
                if not self._setup:
                    if self._setuper._exc:
                        exctyp,exval,exctrace = self._setuper._exc[0]
                        raise exctyp,exval,exctrace
                    else:
                        raise RuntimeError, "Failed to setup application"
                else:
                    self._logger.info("Setup ready: %s at %s", self, self.node.hostname)
            else:
                self.setup()
        
    def _make_home(self):
        # Make sure all the paths are created where 
        # they have to be created for deployment
        # sync files
        try:
            self._popen_ssh_command(
                "mkdir -p %(home)s && ( rm -f %(home)s/{pid,build-pid,nepi-build.sh} >/dev/null 2>&1 || /bin/true )" \
                    % { 'home' : server.shell_escape(self.home_path) },
                timeout = 120,
                retry = 3
                )
        except RuntimeError, e:
            raise RuntimeError, "Failed to set up application %s: %s %s" % (self.home_path, e.args[0], e.args[1],)
        
        if self.stdin:
            # Write program input
            try:
                self._popen_scp(
                    cStringIO.StringIO(self.stdin),
                    '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                        os.path.join(self.home_path, 'stdin') ),
                    )
            except RuntimeError, e:
                raise RuntimeError, "Failed to set up application %s: %s %s" \
                        % (self.home_path, e.args[0], e.args[1],)

    def _replace_paths(self, command):
        """
        Replace all special path tags with shell-escaped actual paths.
        """
        # need to append ${HOME} if paths aren't absolute, to MAKE them absolute.
        root = '' if self.home_path.startswith('/') else "${HOME}/"
        return ( command
            .replace("${SOURCES}", root+server.shell_escape(self.home_path))
            .replace("${BUILD}", root+server.shell_escape(os.path.join(self.home_path,'build'))) )

    def _launch_build(self, trial=0):
        if self._master is not None:
            if not trial or self._master_prk is not None:
                self._do_install_keys()
            buildscript = self._do_build_slave()
        else:
            buildscript = self._do_build_master()
            
        if buildscript is not None:
            self._logger.info("Building %s at %s", self, self.node.hostname)
            
            # upload build script
            try:
                self._popen_scp(
                    buildscript,
                    '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                        os.path.join(self.home_path, 'nepi-build.sh') )
                    )
            except RuntimeError, e:
                raise RuntimeError, "Failed to set up application %s: %s %s" \
                        % (self.home_path, e.args[0], e.args[1],)
            
            # launch build
            self._do_launch_build()
    
    def _finish_build(self):
        self._do_wait_build()
        self._do_install()

    def _do_build_slave(self):
        if not self.sources and not self.build:
            return None
            
        # Create build script
        files = set()
        
        if self.sources:
            sources = self.sources.split(' ')
            files.update(
                "%s@%s:%s" % (self._master.node.slicename, self._master.node.hostip, 
                    os.path.join(self._master.home_path, os.path.basename(source)),)
                for source in sources
            )
        
        if self.build:
            files.add(
                "%s@%s:%s" % (self._master.node.slicename, self._master.node.hostip, 
                    os.path.join(self._master.home_path, 'build.tar.gz'),)
            )
        
        sshopts = "-o ConnectTimeout=30 -o ConnectionAttempts=3 -o ServerAliveInterval=30 -o TCPKeepAlive=yes"
        
        launch_agent = "{ ( echo -e '#!/bin/sh\\ncat' > .ssh-askpass ) && chmod u+x .ssh-askpass"\
                        " && export SSH_ASKPASS=$(pwd)/.ssh-askpass "\
                        " && ssh-agent > .ssh-agent.sh ; } && . ./.ssh-agent.sh && ( echo $NEPI_MASTER_PASSPHRASE | ssh-add %(prk)s ) && rm -rf %(prk)s %(puk)s" %  \
        {
            'prk' : server.shell_escape(self._master_prk_name),
            'puk' : server.shell_escape(self._master_puk_name),
        }
        
        kill_agent = "kill $SSH_AGENT_PID"
        
        waitmaster = (
            "{ "
            "echo 'Checking master reachability' ; "
            "if ping -c 3 %(master_host)s && (. ./.ssh-agent.sh > /dev/null ; ssh -o UserKnownHostsFile=%(hostkey)s %(sshopts)s %(master)s echo MASTER SAYS HI ) ; then "
            "echo 'Master node reachable' ; "
            "else "
            "echo 'MASTER NODE UNREACHABLE' && "
            "exit 1 ; "
            "fi ; "
            ". ./.ssh-agent.sh ; "
            "while [[ $(. ./.ssh-agent.sh > /dev/null ; ssh -q -o UserKnownHostsFile=%(hostkey)s %(sshopts)s %(master)s cat %(token_path)s.retcode || /bin/true) != %(token)s ]] ; do sleep 5 ; done ; "
            "if [[ $(. ./.ssh-agent.sh > /dev/null ; ssh -q -o UserKnownHostsFile=%(hostkey)s %(sshopts)s %(master)s cat %(token_path)s || /bin/true) != %(token)s ]] ; then echo BAD TOKEN ; exit 1 ; fi ; "
            "}" 
        ) % {
            'hostkey' : 'master_known_hosts',
            'master' : "%s@%s" % (self._master.node.slicename, self._master.node.hostip),
            'master_host' : self._master.node.hostip,
            'token_path' : os.path.join(self._master.home_path, 'build.token'),
            'token' : server.shell_escape(self._master._master_token),
            'sshopts' : sshopts,
        }
        
        syncfiles = ". ./.ssh-agent.sh && scp -p -o UserKnownHostsFile=%(hostkey)s %(sshopts)s %(files)s ." % {
            'hostkey' : 'master_known_hosts',
            'files' : ' '.join(files),
            'sshopts' : sshopts,
        }
        if self.build:
            syncfiles += " && tar xzf build.tar.gz"
        syncfiles += " && ( echo %s > build.token )" % (server.shell_escape(self._master_token),)
        syncfiles += " && ( echo %s > build.token.retcode )" % (server.shell_escape(self._master_token),)
        syncfiles = "{ . ./.ssh-agent.sh ; %s ; }" % (syncfiles,)
        
        cleanup = "{ . ./.ssh-agent.sh ; kill $SSH_AGENT_PID ; rm -rf %(prk)s %(puk)s master_known_hosts .ssh-askpass ; }" % {
            'prk' : server.shell_escape(self._master_prk_name),
            'puk' : server.shell_escape(self._master_puk_name),
        }
        
        slavescript = "( ( %(launch_agent)s && %(waitmaster)s && %(syncfiles)s && %(kill_agent)s && %(cleanup)s ) || %(cleanup)s ) ; echo %(token)s > build.token.retcode" % {
            'waitmaster' : waitmaster,
            'syncfiles' : syncfiles,
            'cleanup' : cleanup,
            'kill_agent' : kill_agent,
            'launch_agent' : launch_agent,
            'home' : server.shell_escape(self.home_path),
            'token' : server.shell_escape(self._master_token),
        }
        
        return cStringIO.StringIO(slavescript)
         
    def _do_launch_build(self):
        script = "bash ./nepi-build.sh"
        if self._master_passphrase:
            script = "NEPI_MASTER_PASSPHRASE=%s %s" % (
                server.shell_escape(self._master_passphrase),
                script
            )
        (out,err),proc = rspawn.remote_spawn(
            script,
            pidfile = 'build-pid',
            home = self.home_path,
            stdin = '/dev/null',
            stdout = 'buildlog',
            stderr = rspawn.STDOUT,
            
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key,
            hostip = self.node.hostip,
            )
        
        if proc.wait():
            if self.check_bad_host(out, err):
                self.node.blacklist()
            raise RuntimeError, "Failed to set up build slave %s: %s %s" % (self.home_path, out,err,)
        
        
        pid = ppid = None
        delay = 1.0
        for i in xrange(5):
            pidtuple = rspawn.remote_check_pid(
                os.path.join(self.home_path,'build-pid'),
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key,
                hostip = self.node.hostip
                )
            
            if pidtuple:
                pid, ppid = pidtuple
                self._build_pid, self._build_ppid = pidtuple
                break
            else:
                time.sleep(delay)
                delay = min(30,delay*1.2)
        else:
            raise RuntimeError, "Failed to set up build slave %s: cannot get pid" % (self.home_path,)

        self._logger.info("Deploying %s at %s", self, self.node.hostname)
        
    def _do_wait_build(self, trial=0):
        pid = self._build_pid
        ppid = self._build_ppid
        
        if pid and ppid:
            delay = 1.0
            first = True
            bustspin = 0
            while True:
                status = rspawn.remote_status(
                    pid, ppid,
                    host = self.node.hostname,
                    port = None,
                    user = self.node.slicename,
                    agent = None,
                    ident_key = self.node.ident_path,
                    server_key = self.node.server_key,
                    hostip = self.node.hostip
                    )
                
                if status is rspawn.FINISHED:
                    self._build_pid = self._build_ppid = None
                    break
                elif status is not rspawn.RUNNING:
                    self._logger.warn("Busted waiting for %s to finish building at %s %s", self, self.node.hostname,
                            "(build slave)" if self._master is not None else "(build master)")
                    bustspin += 1
                    time.sleep(delay*(5.5+random.random()))
                    if bustspin > 12:
                        self._build_pid = self._build_ppid = None
                        break
                else:
                    if first:
                        self._logger.info("Waiting for %s to finish building at %s %s", self, self.node.hostname,
                            "(build slave)" if self._master is not None else "(build master)")
                        
                        first = False
                    time.sleep(delay*(0.5+random.random()))
                    delay = min(30,delay*1.2)
                    bustspin = 0
            
            # check build token
            slave_token = ""
            for i in xrange(3):
                (out, err), proc = self._popen_ssh_command(
                    "cat %(token_path)s" % {
                        'token_path' : os.path.join(self.home_path, 'build.token'),
                    },
                    timeout = 120,
                    noerrors = True)
                if not proc.wait() and out:
                    slave_token = out.strip()
                
                if slave_token:
                    break
                else:
                    time.sleep(2)
            
            if slave_token != self._master_token:
                # Get buildlog for the error message

                (buildlog, err), proc = self._popen_ssh_command(
                    "cat %(buildlog)s" % {
                        'buildlog' : os.path.join(self.home_path, 'buildlog'),
                        'buildscript' : os.path.join(self.home_path, 'nepi-build.sh'),
                    },
                    timeout = 120,
                    noerrors = True)
                
                proc.wait()
                
                if self.check_bad_host(buildlog, err):
                    self.node.blacklist()
                elif self._master and trial < 3 and 'BAD TOKEN' in buildlog or 'BAD TOKEN' in err:
                    # bad sync with master, may try again
                    # but first wait for master
                    self._master.async_setup_wait()
                    self._launch_build(trial+1)
                    return self._do_wait_build(trial+1)
                elif trial < 3:
                    return self._do_wait_build(trial+1)
                else:
                    # No longer need'em
                    self._master_prk = None
                    self._master_puk = None
        
                    raise RuntimeError, "Failed to set up application %s: "\
                            "build failed, got wrong token from pid %s/%s "\
                            "(expected %r, got %r), see buildlog at %s:\n%s" % (
                        self.home_path, pid, ppid, self._master_token, slave_token, self.node.hostname, buildlog)

            # No longer need'em
            self._master_prk = None
            self._master_puk = None
        
            self._logger.info("Built %s at %s", self, self.node.hostname)

    def _do_kill_build(self):
        pid = self._build_pid
        ppid = self._build_ppid
        
        if pid and ppid:
            self._logger.info("Killing build of %s", self)
            rspawn.remote_kill(
                pid, ppid,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                hostip = self.node.hostip
                )
        
        
    def _do_build_master(self):
        if not self.sources and not self.build and not self.buildDepends:
            return None
            
        if self.sources:
            sources = self.sources.split(' ')
            
            # Copy all sources
            try:
                self._popen_scp(
                    sources,
                    "%s@%s:%s" % (self.node.slicename, self.node.hostname, 
                        os.path.join(self.home_path,'.'),)
                    )
            except RuntimeError, e:
                raise RuntimeError, "Failed upload source file %r: %s %s" \
                        % (sources, e.args[0], e.args[1],)
            
        buildscript = cStringIO.StringIO()
        
        buildscript.write("(\n")
        
        if self.buildDepends:
            # Install build dependencies
            buildscript.write(
                "sudo -S yum -y install %(packages)s\n" % {
                    'packages' : self.buildDepends
                }
            )
        
            
        if self.build:
            # Build sources
            buildscript.write(
                "mkdir -p build && ( cd build && ( %(command)s ) )\n" % {
                    'command' : self._replace_paths(self.build),
                    'home' : server.shell_escape(self.home_path),
                }
            )
        
            # Make archive
            buildscript.write("tar czf build.tar.gz build\n")
        
        # Write token
        buildscript.write("echo %(master_token)s > build.token ) ; echo %(master_token)s > build.token.retcode" % {
            'master_token' : server.shell_escape(self._master_token)
        })
        
        buildscript.seek(0)

        return buildscript

    def _do_install(self):
        if self.install:
            self._logger.info("Installing %s at %s", self, self.node.hostname)
            
            # Install application
            try:
                self._popen_ssh_command(
                    "cd %(home)s && cd build && ( %(command)s ) > ${HOME}/%(home)s/installlog 2>&1 || ( tail ${HOME}/%(home)s/{install,build}log >&2 && false )" % \
                        {
                        'command' : self._replace_paths(self.install),
                        'home' : server.shell_escape(self.home_path),
                        },
                    )
            except RuntimeError, e:
                if self.check_bad_host(e.args[0], e.args[1]):
                    self.node.blacklist()
                raise RuntimeError, "Failed install build sources: %s %s" % (e.args[0], e.args[1],)

    def set_master(self, master):
        self._master = master
        
    def install_keys(self, prk, puk, passphrase):
        # Install keys
        self._master_passphrase = passphrase
        self._master_prk = prk
        self._master_puk = puk
        self._master_prk_name = os.path.basename(prk.name)
        self._master_puk_name = os.path.basename(puk.name)
        
    def _do_install_keys(self):
        prk = self._master_prk
        puk = self._master_puk
       
        try:
            self._popen_scp(
                [ prk.name, puk.name ],
                '%s@%s:%s' % (self.node.slicename, self.node.hostname, self.home_path )
                )
        except RuntimeError, e:
            raise RuntimeError, "Failed to set up application deployment keys: %s %s" \
                    % (e.args[0], e.args[1],)

        try:
            self._popen_scp(
                cStringIO.StringIO('%s,%s %s\n' % (
                    self._master.node.hostname, self._master.node.hostip, 
                    self._master.node.server_key)),
                '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                    os.path.join(self.home_path,"master_known_hosts") )
                )
        except RuntimeError, e:
            raise RuntimeError, "Failed to set up application deployment keys: %s %s" \
                    % (e.args[0], e.args[1],)
        
    
    def cleanup(self):
        # make sure there's no leftover build processes
        self._do_kill_build()
        
        # No longer need'em
        self._master_prk = None
        self._master_puk = None

    @server.eintr_retry
    def _popen_scp(self, src, dst, retry = 3):
        while 1:
            try:
                (out,err),proc = server.popen_scp(
                    src,
                    dst, 
                    port = None,
                    agent = None,
                    ident_key = self.node.ident_path,
                    server_key = self.node.server_key
                    )

                if server.eintr_retry(proc.wait)():
                    raise RuntimeError, (out, err)
                return (out, err), proc
            except:
                if retry <= 0:
                    raise
                else:
                    retry -= 1
  

    @server.eintr_retry
    def _popen_ssh_command(self, command, retry = 0, noerrors=False, timeout=None):
        (out,err),proc = server.popen_ssh_command(
            command,
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key,
            timeout = timeout,
            retry = retry
            )

        if server.eintr_retry(proc.wait)():
            if not noerrors:
                raise RuntimeError, (out, err)
        return (out, err), proc

class Application(Dependency):
    """
    An application also has dependencies, but also a command to be ran and monitored.
    
    It adds the output of that command as traces.
    """
    
    TRACES = ('stdout','stderr','buildlog', 'output')
    
    def __init__(self, api=None):
        super(Application,self).__init__(api)
        
        # Attributes
        self.command = None
        self.sudo = False
        
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.output = None
        
        # Those are filled when the app is started
        #   Having both pid and ppid makes it harder
        #   for pid rollover to induce tracking mistakes
        self._started = False
        self._pid = None
        self._ppid = None

        # Do not add to the python path of nodes
        self.add_to_path = False
    
    def __str__(self):
        return "%s<command:%s%s>" % (
            self.__class__.__name__,
            "sudo " if self.sudo else "",
            self.command,
        )
    
    def start(self):
        self._logger.info("Starting %s", self)
        
        # Create shell script with the command
        # This way, complex commands and scripts can be ran seamlessly
        # sync files
        command = cStringIO.StringIO()
        command.write('export PYTHONPATH=$PYTHONPATH:%s\n' % (
            ':'.join(["${HOME}/"+server.shell_escape(s) for s in self.node.pythonpath])
        ))
        command.write('export PATH=$PATH:%s\n' % (
            ':'.join(["${HOME}/"+server.shell_escape(s) for s in self.node.pythonpath])
        ))
        if self.node.env:
            for envkey, envvals in self.node.env.iteritems():
                for envval in envvals:
                    command.write('export %s=%s\n' % (envkey, envval))
        command.write(self.command)
        command.seek(0)

        try:
            self._popen_scp(
                command,
                '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                    os.path.join(self.home_path, "app.sh"))
                )
        except RuntimeError, e:
            raise RuntimeError, "Failed to set up application: %s %s" \
                    % (e.args[0], e.args[1],)
        
        # Start process in a "daemonized" way, using nohup and heavy
        # stdin/out redirection to avoid connection issues
        (out,err),proc = rspawn.remote_spawn(
            self._replace_paths("bash ./app.sh"),
            
            pidfile = './pid',
            home = self.home_path,
            stdin = 'stdin' if self.stdin is not None else '/dev/null',
            stdout = 'stdout' if self.stdout else '/dev/null',
            stderr = 'stderr' if self.stderr else '/dev/null',
            sudo = self.sudo,
            
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
            )
        
        if proc.wait():
            if self.check_bad_host(out, err):
                self.node.blacklist()
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

        self._started = True
    
    def recover(self):
        # Assuming the application is running on PlanetLab,
        # proper pidfiles should be present at the app's home path.
        # So we mark this application as started, and check the pidfiles
        self._started = True
        self.checkpid()

    def checkpid(self):            
        # Get PID/PPID
        # NOTE: wait a bit for the pidfile to be created
        if self._started and not self._pid or not self._ppid:
            pidtuple = rspawn.remote_check_pid(
                os.path.join(self.home_path,'pid'),
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
            
            if pidtuple:
                self._pid, self._ppid = pidtuple
    
    def status(self):
        self.checkpid()
        if not self._started:
            return AS.STATUS_NOT_STARTED
        elif not self._pid or not self._ppid:
            return AS.STATUS_NOT_STARTED
        else:
            status = rspawn.remote_status(
                self._pid, self._ppid,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
            
            if status is rspawn.NOT_STARTED:
                return AS.STATUS_NOT_STARTED
            elif status is rspawn.RUNNING:
                return AS.STATUS_RUNNING
            elif status is rspawn.FINISHED:
                return AS.STATUS_FINISHED
            else:
                # WTF?
                return AS.STATUS_NOT_STARTED
    
    def kill(self):
        status = self.status()
        if status == AS.STATUS_RUNNING:
            # kill by ppid+pid - SIGTERM first, then try SIGKILL
            rspawn.remote_kill(
                self._pid, self._ppid,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key,
                sudo = self.sudo
                )
            self._logger.info("Killed %s", self)


class NepiDependency(Dependency):
    """
    This dependency adds nepi itself to the python path,
    so that you may run testbeds within PL nodes.
    """
    
    # Class attribute holding a *weak* reference to the shared NEPI tar file
    # so that they may share it. Don't operate on the file itself, it would
    # be a mess, just use its path.
    _shared_nepi_tar = None
    
    def __init__(self, api = None):
        super(NepiDependency, self).__init__(api)
        
        self._tarball = None
        
        self.depends = 'python python-ipaddr python-setuptools'
        
        # our sources are in our ad-hoc tarball
        self.sources = self.tarball.name
        
        tarname = os.path.basename(self.tarball.name)
        
        # it's already built - just move the tarball into place
        self.build = "mv -f ${SOURCES}/%s ." % (tarname,)
        
        # unpack it into sources, and we're done
        self.install = "tar xzf ${BUILD}/%s -C .." % (tarname,)
    
    @property
    def tarball(self):
        if self._tarball is None:
            shared_tar = self._shared_nepi_tar and self._shared_nepi_tar()
            if shared_tar is not None:
                self._tarball = shared_tar
            else:
                # Build an ad-hoc tarball
                # Prebuilt
                import nepi
                import tempfile
                
                shared_tar = tempfile.NamedTemporaryFile(prefix='nepi-src-', suffix='.tar.gz')
                
                proc = subprocess.Popen(
                    ["tar", "czf", shared_tar.name, 
                        '-C', os.path.join(os.path.dirname(os.path.dirname(nepi.__file__)),'.'), 
                        'nepi'],
                    stdout = open("/dev/null","w"),
                    stdin = open("/dev/null","r"))

                if proc.wait():
                    raise RuntimeError, "Failed to create nepi tarball"
                
                self._tarball = self._shared_nepi_tar = shared_tar
                
        return self._tarball

class NS3Dependency(Dependency):
    """
    This dependency adds NS3 libraries to the library paths,
    so that you may run the NS3 testbed within PL nodes.
    
    You'll also need the NepiDependency.
    """
    
    def __init__(self, api = None):
        super(NS3Dependency, self).__init__(api)
        
        self.depends = 'bzr'
        
        self.buildDepends = 'make waf gcc gcc-c++ gccxml unzip'
        
        # We have to download the sources, untar, build...
        pygccxml_source_url = "http://leaseweb.dl.sourceforge.net/project/pygccxml/pygccxml/pygccxml-1.0/pygccxml-1.0.0.zip"
        ns3_source_url = "http://nepi.pl.sophia.inria.fr/code/nepi-ns3.13/archive/tip.tar.gz"
        passfd_source_url = "http://nepi.pl.sophia.inria.fr/code/python-passfd/archive/tip.tar.gz"
        
        pybindgen_version = "797"

        self.build =(
            " ( "
            "  cd .. && "
            "  python -c 'import pygccxml, pybindgen, passfd' && "
            "  test -f lib/ns/_core.so && "
            "  test -f lib/ns/__init__.py && "
            "  test -f lib/ns/core.py && "
            "  test -f lib/libns3-core.so && "
            "  LD_LIBRARY_PATH=lib PYTHONPATH=lib python -c 'import ns.core' "
            " ) || ( "
                # Not working, rebuild
                     # Archive SHA1 sums to check
                     "echo '7158877faff2254e6c094bf18e6b4283cac19137  pygccxml-1.0.0.zip' > archive_sums.txt && "
                     " ( " # check existing files
                     " sha1sum -c archive_sums.txt && "
                     " test -f passfd-src.tar.gz && "
                     " test -f ns3-src.tar.gz "
                     " ) || ( " # nope? re-download
                     " rm -rf pybindgen pygccxml-1.0.0.zip passfd-src.tar.gz ns3-src.tar.gz && "
                     " bzr checkout lp:pybindgen -r %(pybindgen_version)s && " # continue, to exploit the case when it has already been dl'ed
                     " wget -q -c -O pygccxml-1.0.0.zip %(pygccxml_source_url)s && " 
                     " wget -q -c -O passfd-src.tar.gz %(passfd_source_url)s && "
                     " wget -q -c -O ns3-src.tar.gz %(ns3_source_url)s && "  
                     " sha1sum -c archive_sums.txt " # Check SHA1 sums when applicable
                     " ) && "
                     "unzip -n pygccxml-1.0.0.zip && "
                     "mkdir -p ns3-src && "
                     "mkdir -p passfd-src && "
                     "tar xzf ns3-src.tar.gz --strip-components=1 -C ns3-src && "
                     "tar xzf passfd-src.tar.gz --strip-components=1 -C passfd-src && "
                     "rm -rf target && "    # mv doesn't like unclean targets
                     "mkdir -p target && "
                     "cd pygccxml-1.0.0 && "
                     "rm -rf unittests docs && " # pygccxml has ~100M of unit tests - excessive - docs aren't needed either
                     "python setup.py build && "
                     "python setup.py install --install-lib ${BUILD}/target && "
                     "python setup.py clean && "
                     "cd ../pybindgen && "
                     "export PYTHONPATH=$PYTHONPATH:${BUILD}/target && "
                     "./waf configure --prefix=${BUILD}/target -d release && "
                     "./waf && "
                     "./waf install && "
                     "./waf clean && "
                     "mv -f ${BUILD}/target/lib/python*/site-packages/pybindgen ${BUILD}/target/. && "
                     "rm -rf ${BUILD}/target/lib && "
                     "cd ../passfd-src && "
                     "python setup.py build && "
                     "python setup.py install --install-lib ${BUILD}/target && "
                     "python setup.py clean && "
                     "cd ../ns3-src && "
                     "./waf configure --prefix=${BUILD}/target --with-pybindgen=../pybindgen-src -d release --disable-examples --disable-tests && "
                     "./waf &&"
                     "./waf install && "
                     "rm -f ${BUILD}/target/lib/*.so && "
                     "cp -a ${BUILD}/ns3-src/build/libns3*.so ${BUILD}/target/lib && "
                     "cp -a ${BUILD}/ns3-src/build/bindings/python/ns ${BUILD}/target/lib &&"
                     "./waf clean "
             " )"
                     % dict(
                        pybindgen_version = server.shell_escape(pybindgen_version),
                        pygccxml_source_url = server.shell_escape(pygccxml_source_url),
                        ns3_source_url = server.shell_escape(ns3_source_url),
                        passfd_source_url = server.shell_escape(passfd_source_url),
                     ))
        
        # Just move ${BUILD}/target
        self.install = (
            " ( "
            "  cd .. && "
            "  python -c 'import pygccxml, pybindgen, passfd' && "
            "  test -f lib/ns/_core.so && "
            "  test -f lib/ns/__init__.py && "
            "  test -f lib/ns/core.py && "
            "  test -f lib/libns3-core.so && "
            "  LD_LIBRARY_PATH=lib PYTHONPATH=lib python -c 'import ns.core' "
            " ) || ( "
                # Not working, reinstall
                    "test -d ${BUILD}/target && "
                    "[[ \"x\" != \"x$(find ${BUILD}/target -mindepth 1 -print -quit)\" ]] &&"
                    "( for i in ${BUILD}/target/* ; do rm -rf ${SOURCES}/${i##*/} ; done ) && " # mv doesn't like unclean targets
                    "mv -f ${BUILD}/target/* ${SOURCES}"
            " )"
        )
        
        # Set extra environment paths
        self.env['NEPI_NS3BINDINGS'] = "${SOURCES}/lib"
        self.env['NEPI_NS3LIBRARY'] = "${SOURCES}/lib"
    
    @property
    def tarball(self):
        if self._tarball is None:
            shared_tar = self._shared_nepi_tar and self._shared_nepi_tar()
            if shared_tar is not None:
                self._tarball = shared_tar
            else:
                # Build an ad-hoc tarball
                # Prebuilt
                import nepi
                import tempfile
                
                shared_tar = tempfile.NamedTemporaryFile(prefix='nepi-src-', suffix='.tar.gz')
                
                proc = subprocess.Popen(
                    ["tar", "czf", shared_tar.name, 
                        '-C', os.path.join(os.path.dirname(os.path.dirname(nepi.__file__)),'.'), 
                        'nepi'],
                    stdout = open("/dev/null","w"),
                    stdin = open("/dev/null","r"))

                if proc.wait():
                    raise RuntimeError, "Failed to create nepi tarball"
                
                self._tarball = self._shared_nepi_tar = shared_tar
                
        return self._tarball

class YumDependency(Dependency):
    """
    This dependency is an internal helper class used to
    efficiently distribute yum-downloaded rpms.
    
    It temporarily sets the yum cache as persistent in the
    build master, and installs all the required packages.
    
    The rpm packages left in the yum cache are gathered and
    distributed by the underlying Dependency in an efficient
    manner. Build slaves will then install those rpms back in
    the cache before issuing the install command.
    
    When packages have been installed already, nothing but an
    empty tar is distributed.
    """
    
    # Class attribute holding a *weak* reference to the shared NEPI tar file
    # so that they may share it. Don't operate on the file itself, it would
    # be a mess, just use its path.
    _shared_nepi_tar = None
    
    def _build_get(self):
        # canonical representation of dependencies
        depends = ' '.join( sorted( (self.depends or "").split(' ') ) )
        
        # download rpms and pack into a tar archive
        return (
            "sudo -S nice yum -y makecache && "
            "sudo -S sed -i -r 's/keepcache *= *0/keepcache=1/' /etc/yum.conf && "
            " ( ( "
                "sudo -S nice yum -y install %s ; "
                "rm -f ${BUILD}/packages.tar ; "
                "tar -C /var/cache/yum -rf ${BUILD}/packages.tar $(cd /var/cache/yum ; find -iname '*.rpm')"
            " ) || /bin/true ) && "
            "sudo -S sed -i -r 's/keepcache *= *1/keepcache=0/' /etc/yum.conf && "
            "( sudo -S nice yum -y clean packages || /bin/true ) "
        ) % ( depends, )
    def _build_set(self, value):
        # ignore
        return
    build = property(_build_get, _build_set)
    
    def _install_get(self):
        # canonical representation of dependencies
        depends = ' '.join( sorted( (self.depends or "").split(' ') ) )
        
        # unpack cached rpms into yum cache, install, and cleanup
        return (
            "sudo -S tar -k --keep-newer-files -C /var/cache/yum -xf packages.tar && "
            "sudo -S nice yum -y install %s && "
            "( sudo -S nice yum -y clean packages || /bin/true ) "
        ) % ( depends, )
    def _install_set(self, value):
        # ignore
        return
    install = property(_install_get, _install_set)
        
    def check_bad_host(self, out, err):
        badre = re.compile(r'(?:'
                           r'The GPG keys listed for the ".*" repository are already installed but they are not correct for this package'
                           r'|Error: Cannot retrieve repository metadata (repomd.xml) for repository: .*[.] Please verify its path and try again'
                           r'|Error: disk I/O error'
                           r'|MASTER NODE UNREACHABLE'
                           r')', 
                           re.I)
        return badre.search(out) or badre.search(err) or self.node.check_bad_host(out,err)
