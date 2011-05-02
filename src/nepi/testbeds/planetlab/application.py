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
import rspawn

from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

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
    
    def __str__(self):
        return "%s<%s>" % (
            self.__class__.__name__,
            ' '.join(list(self.depends or [])
                   + list(self.sources or []))
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
        (out,err),proc = server.popen_scp(
            '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                tracefile),
            local_path,
            port = None,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        return local_path
    

    def setup(self):
        self._make_home()
        self._build()
        self._setup = True
    
    def async_setup(self):
        if not self._setuper:
            self._setuper = threading.Thread(
                target = self.setup)
            self._setuper.start()
    
    def async_setup_wait(self):
        if not self._setup:
            if self._setuper:
                self._setuper.join()
                if not self._setup:
                    raise RuntimeError, "Failed to setup application"
            else:
                self.setup()
        
    def _make_home(self):
        # Make sure all the paths are created where 
        # they have to be created for deployment
        (out,err),proc = server.popen_ssh_command(
            "mkdir -p %s" % (server.shell_escape(self.home_path),),
            host = self.node.hostname,
            port = None,
            user = self.node.slicename,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)
        
        
        if self.stdin:
            # Write program input
            (out,err),proc = server.popen_scp(
                cStringIO.StringIO(self.stdin),
                '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                    os.path.join(self.home_path, 'stdin') ),
                port = None,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
            
            if proc.wait():
                raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)

    def _replace_paths(self, command):
        """
        Replace all special path tags with shell-escaped actual paths.
        """
        # need to append ${HOME} if paths aren't absolute, to MAKE them absolute.
        root = '' if self.home_path.startswith('/') else "${HOME}/"
        return ( command
            .replace("${SOURCES}", root+server.shell_escape(self.home_path))
            .replace("${BUILD}", root+server.shell_escape(os.path.join(self.home_path,'build'))) )

    def _build(self):
        if self.sources:
            sources = self.sources.split(' ')
            
            # Copy all sources
            (out,err),proc = server.popen_scp(
                sources,
                "%s@%s:%s" % (self.node.slicename, self.node.hostname, 
                    os.path.join(self.home_path,'.'),),
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed upload source file %r: %s %s" % (source, out,err,)
            
        if self.buildDepends:
            # Install build dependencies
            (out,err),proc = server.popen_ssh_command(
                "sudo -S yum -y install %(packages)s" % {
                    'packages' : self.buildDepends
                },
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed instal build dependencies: %s %s" % (out,err,)
        
            
        if self.build:
            # Build sources
            (out,err),proc = server.popen_ssh_command(
                "cd %(home)s && mkdir -p build && cd build && ( %(command)s ) > ${HOME}/%(home)s/buildlog 2>&1 || ( tail ${HOME}/%(home)s/buildlog >&2 && false )" % {
                    'command' : self._replace_paths(self.build),
                    'home' : server.shell_escape(self.home_path),
                },
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed instal build sources: %s %s" % (out,err,)

            # Make archive
            (out,err),proc = server.popen_ssh_command(
                "cd %(home)s && tar czf build.tar.gz build" % {
                    'command' : self._replace_paths(self.build),
                    'home' : server.shell_escape(self.home_path),
                },
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed instal build sources: %s %s" % (out,err,)

        if self.install:
            # Install application
            (out,err),proc = server.popen_ssh_command(
                "cd %(home)s && cd build && ( %(command)s ) > ${HOME}/%(home)s/installlog 2>&1 || ( tail ${HOME}/%(home)s/installlog >&2 && false )" % {
                    'command' : self._replace_paths(self.install),
                    'home' : server.shell_escape(self.home_path),
                },
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path,
                server_key = self.node.server_key
                )
        
            if proc.wait():
                raise RuntimeError, "Failed instal build sources: %s %s" % (out,err,)

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
        
        (out,err),proc = server.popen_scp(
            command,
            '%s@%s:%s' % (self.node.slicename, self.node.hostname, 
                os.path.join(self.home_path, "app.sh")),
            port = None,
            agent = None,
            ident_key = self.node.ident_path,
            server_key = self.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up application: %s %s" % (out,err,)
        
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
            return STATUS_NOT_STARTED
        elif not self._pid or not self._ppid:
            return STATUS_NOT_STARTED
        else:
            status = rspawn.remote_status(
                self._pid, self._ppid,
                host = self.node.hostname,
                port = None,
                user = self.node.slicename,
                agent = None,
                ident_key = self.node.ident_path
                )
            
            if status is rspawn.NOT_STARTED:
                return STATUS_NOT_STARTED
            elif status is rspawn.RUNNING:
                return STATUS_RUNNING
            elif status is rspawn.FINISHED:
                return STATUS_FINISHED
            else:
                # WTF?
                return STATUS_NOT_STARTED
    
    def kill(self):
        status = self.status()
        if status == STATUS_RUNNING:
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
        self.build = "mv ${SOURCES}/%s ." % (tarname,)
        
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
        
        self.buildDepends = 'build-essential waf gcc gcc-c++ gccxml unzip'
        
        # We have to download the sources, untar, build...
        pybindgen_source_url = "http://pybindgen.googlecode.com/files/pybindgen-0.15.0.zip"
        pygccxml_source_url = "http://leaseweb.dl.sourceforge.net/project/pygccxml/pygccxml/pygccxml-1.0/pygccxml-1.0.0.zip"
        ns3_source_url = "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/ns-3-dev/archive/tip.tar.gz"
        self.build =("wget -q -c -O pybindgen-src.zip %(pybindgen_source_url)s && " # continue, to exploit the case when it has already been dl'ed
                     "wget -q -c -O pygccxml-1.0.0.zip %(pygccxml_source_url)s && " 
                     "wget -q -c -O ns3-src.tar.gz %(ns3_source_url)s && "  
                     "unzip -n pybindgen-src.zip && " # Do not overwrite files, to exploit the case when it has already been built
                     "unzip -n pygccxml-1.0.0.zip && "
                     "mkdir -p ns3-src && "
                     "tar xzf ns3-src.tar.gz --strip-components=1 -C ns3-src && "
                     "rm -rf target && "    # mv doesn't like unclean targets
                     "mkdir -p target && "
                     "cd pygccxml-1.0.0 && "
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
                     "cd ../ns3-src && "
                     "./waf configure --prefix=${BUILD}/target -d release --disable-examples && "
                     "./waf &&"
                     "./waf install && "
                     "./waf clean"
                     % dict(
                        pybindgen_source_url = server.shell_escape(pybindgen_source_url),
                        pygccxml_source_url = server.shell_escape(pygccxml_source_url),
                        ns3_source_url = server.shell_escape(ns3_source_url),
                     ))
        
        # Just move ${BUILD}/target
        self.install = (
            "( for i in ${BUILD}/target/* ; do rm -rf ${SOURCES}/${i##*/} ; done ) && " # mv doesn't like unclean targets
            "mv -f ${BUILD}/target/* ${SOURCES}"
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


