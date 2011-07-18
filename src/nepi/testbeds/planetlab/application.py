#!/usr/bin/env python
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
        self._master_token = ''.join(map(chr,[rng.randint(0,255) 
                                      for rng in (random.SystemRandom(),)
                                      for i in xrange(8)] )).encode("hex")
        self._build_pid = None
        self._build_ppid = None
        
    
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
    
    def remote_trace_path(self, whichtrace):
        if whichtrace in self.TRACES:
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

    def setup(self):
        print >>sys.stderr, "Setting up", self
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
            print >>sys.stderr, "Waiting for", self, "to be setup"
            if self._setuper:
                self._setuper.join()
                if not self._setup:
                    if self._setuper._exc:
                        exctyp,exval,exctrace = self._setuper._exc[0]
                        raise exctyp,exval,exctrace
                    else:
                        raise RuntimeError, "Failed to setup application"
            else:
                self.setup()
        
    def _make_home(self):
        # Make sure all the paths are created where 
        # they have to be created for deployment
        # sync files
        try:
            self._popen_ssh_command(
                "mkdir -p %(home)s && ( rm -f %(home)s/{pid,build-pid,nepi-build.sh} >/dev/null 2>&1 || /bin/true )" \
                    % { 'home' : server.shell_escape(self.home_path) }
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

    def _launch_build(self):
        if self._master is not None:
            self._do_install_keys()
            buildscript = self._do_build_slave()
        else:
            buildscript = self._do_build_master()
            
        if buildscript is not None:
            print >>sys.stderr, "Building", self
            
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
                "%s@%s:%s" % (self._master.node.slicename, self._master.node.hostname, 
                    os.path.join(self._master.home_path, os.path.basename(source)),)
                for source in sources
            )
        
        if self.build:
            files.add(
                "%s@%s:%s" % (self._master.node.slicename, self._master.node.hostname, 
                    os.path.join(self._master.home_path, 'build.tar.gz'),)
            )
        
        launch_agent = "{ ( echo -e '#!/bin/sh\\ncat' > .ssh-askpass ) && chmod u+x .ssh-askpass"\
                        " && export SSH_ASKPASS=$(pwd)/.ssh-askpass "\
                        " && ssh-agent > .ssh-agent.sh ; } && . ./.ssh-agent.sh && ( echo $NEPI_MASTER_PASSPHRASE | ssh-add %(prk)s ) && rm -rf %(prk)s %(puk)s" %  \
        {
            'prk' : server.shell_escape(self._master_prk_name),
            'puk' : server.shell_escape(self._master_puk_name),
        }
        
        kill_agent = "kill $SSH_AGENT_PID"
        
        waitmaster = "{ . ./.ssh-agent.sh ; while [[ $(ssh -q -o UserKnownHostsFile=%(hostkey)s %(master)s cat %(token_path)s) != %(token)s ]] ; do sleep 5 ; done ; }" % {
            'hostkey' : 'master_known_hosts',
            'master' : "%s@%s" % (self._master.node.slicename, self._master.node.hostname),
            'token_path' : os.path.join(self._master.home_path, 'build.token'),
            'token' : server.shell_escape(self._master._master_token),
        }
        
        syncfiles = "scp -p -o UserKnownHostsFile=%(hostkey)s %(files)s ." % {
            'hostkey' : 'master_known_hosts',
            'files' : ' '.join(files),
        }
        if self.build:
            syncfiles += " && tar xzf build.tar.gz"
        syncfiles += " && ( echo %s > build.token )" % (server.shell_escape(self._master_token),)
        syncfiles = "{ . ./.ssh-agent.sh ; %s ; }" % (syncfiles,)
        
        cleanup = "{ . ./.ssh-agent.sh ; kill $SSH_AGENT_PID ; rm -rf %(prk)s %(puk)s master_known_hosts .ssh-askpass ; }" % {
            'prk' : server.shell_escape(self._master_prk_name),
            'puk' : server.shell_escape(self._master_puk_name),
        }
        
        slavescript = "( ( %(launch_agent)s && %(waitmaster)s && %(syncfiles)s && %(kill_agent)s && %(cleanup)s ) || %(cleanup)s )" % {
            'waitmaster' : waitmaster,
            'syncfiles' : syncfiles,
            'cleanup' : cleanup,
            'kill_agent' : kill_agent,
            'launch_agent' : launch_agent,
            'home' : server.shell_escape(self.home_path),
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
            server_key = self.node.server_key
            )
        
        if proc.wait():
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
                server_key = self.node.server_key
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

        print >>sys.stderr, "Deploying", self
        
    def _do_wait_build(self):
        pid = self._build_pid
        ppid = self._build_ppid
        
        if pid and ppid:
            delay = 1.0
            first = True
            while True:
                status = rspawn.remote_status(
                    pid, ppid,
                    host = self.node.hostname,
                    port = None,
                    user = self.node.slicename,
                    agent = None,
                    ident_key = self.node.ident_path,
                    server_key = self.node.server_key
                    )
                
                if status is not rspawn.RUNNING:
                    self._build_pid = self._build_ppid = None
                    break
                else:
                    if first:
                        print >>sys.stderr, "Waiting for", self, "to finish building",
                        if self._master is not None:
                            print >>sys.stderr, "(build slave)"
                        else:
                            print >>sys.stderr, "(build master)"
                        
                        first = False
                    time.sleep(delay*(0.5+random.random()))
                    delay = min(30,delay*1.2)
            
            # check build token
            (out, err), proc = self._popen_ssh_command(
                "cat %(token_path)s" % {
                    'token_path' : os.path.join(self.home_path, 'build.token'),
                },
                noerrors = True)
            slave_token = ""
            if not proc.wait() and out:
                slave_token = out.strip()
            
            if slave_token != self._master_token:
                # Get buildlog for the error message

                (buildlog, err), proc = self._popen_ssh_command(
                    "cat %(buildlog)s" % {
                        'buildlog' : os.path.join(self.home_path, 'buildlog'),
                        'buildscript' : os.path.join(self.home_path, 'nepi-build.sh'),
                    },
                    noerrors = True)
                
                proc.wait()
                
                raise RuntimeError, "Failed to set up application %s: "\
                        "build failed, got wrong token from pid %s/%s "\
                        "(expected %r, got %r), see buildlog: %s" % (
                    self.home_path, pid, ppid, self._master_token, slave_token, buildlog)

            print >>sys.stderr, "Built", self

    def _do_kill_build(self):
        pid = self._build_pid
        ppid = self._build_ppid
        
        if pid and ppid:
            print >>sys.stderr, "Killing build of", self
            rspawn.remote_kill(
                pid, ppid,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path
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
        buildscript.write("echo %(master_token)s > build.token" % {
            'master_token' : server.shell_escape(self._master_token)
        })
        
        buildscript.seek(0)

        return buildscript

    def _do_install(self):
        if self.install:
            print >>sys.stderr, "Installing", self
            
            # Install application
            try:
                self._popen_ssh_command(
                    "cd %(home)s && cd build && ( %(command)s ) > ${HOME}/%(home)s/installlog 2>&1 || ( tail ${HOME}/%(home)s/installlog >&2 && false )" % \
                        {
                        'command' : self._replace_paths(self.install),
                        'home' : server.shell_escape(self.home_path),
                        },
                    )
            except RuntimeError, e:
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
                    self._master.node.hostname, socket.gethostbyname(self._master.node.hostname), 
                    self._master.node.server_key)),
                '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                    os.path.join(self.home_path,"master_known_hosts") )
                )
        except RuntimeError, e:
            raise RuntimeError, "Failed to set up application deployment keys: %s %s" \
                    % (e.args[0], e.args[1],)
        
        # No longer need'em
        self._master_prk = None
        self._master_puk = None
    
    def cleanup(self):
        # make sure there's no leftover build processes
        self._do_kill_build()

    @server.eintr_retry
    def _popen_scp(self, src, dst, retry = True):
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
  

    @server.eintr_retry
    def _popen_ssh_command(self, command, retry = True, noerrors=False):
        (out,err),proc = server.popen_ssh_command(
            command,
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
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
    
    TRACES = ('stdout','stderr','buildlog')
    
    def __init__(self, api=None):
        super(Application,self).__init__(api)
        
        # Attributes
        self.command = None
        self.sudo = False
        
        self.stdin = None
        self.stdout = None
        self.stderr = None
        
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
        print >>sys.stderr, "Starting", self
        
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
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

        self._started = True

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
                server_key = self.node.server_key
                )
            print >>sys.stderr, "Killed", self


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
        
        self.buildDepends = 'make waf gcc gcc-c++ gccxml unzip'
        
        # We have to download the sources, untar, build...
        pybindgen_source_url = "http://pybindgen.googlecode.com/files/pybindgen-0.15.0.zip"
        pygccxml_source_url = "http://leaseweb.dl.sourceforge.net/project/pygccxml/pygccxml/pygccxml-1.0/pygccxml-1.0.0.zip"
        ns3_source_url = "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/ns-3.9-nepi/archive/tip.tar.gz"
        passfd_source_url = "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/python-passfd/archive/tip.tar.gz"
        self.build =(
            " ( "
            "  cd .. && "
            "  python -c 'import pygccxml, pybindgen, passfd' && "
            "  test -f lib/_ns3.so && "
            "  test -f lib/libns3.so "
            " ) || ( "
                # Not working, rebuild
                     "wget -q -c -O pybindgen-src.zip %(pybindgen_source_url)s && " # continue, to exploit the case when it has already been dl'ed
                     "wget -q -c -O pygccxml-1.0.0.zip %(pygccxml_source_url)s && " 
                     "wget -q -c -O passfd-src.tar.gz %(passfd_source_url)s && "
                     "wget -q -c -O ns3-src.tar.gz %(ns3_source_url)s && "  
                     "unzip -n pybindgen-src.zip && " # Do not overwrite files, to exploit the case when it has already been built
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
                     "cd ../pybindgen-0.15.0 && "
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
                     "./waf configure --prefix=${BUILD}/target -d release --disable-examples --high-precision-as-double && "
                     "./waf &&"
                     "./waf install && "
                     "./waf clean"
             " )"
                     % dict(
                        pybindgen_source_url = server.shell_escape(pybindgen_source_url),
                        pygccxml_source_url = server.shell_escape(pygccxml_source_url),
                        ns3_source_url = server.shell_escape(ns3_source_url),
                        passfd_source_url = server.shell_escape(passfd_source_url),
                     ))
        
        # Just move ${BUILD}/target
        self.install = (
            " ( "
            "  cd .. && "
            "  python -c 'import pygccxml, pybindgen, passfd' && "
            "  test -f lib/_ns3.so && "
            "  test -f lib/libns3.so "
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
        self.env['NEPI_NS3LIBRARY'] = "${SOURCES}/lib/libns3.so"
    
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


