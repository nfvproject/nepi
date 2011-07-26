#!/usr/bin/env python
# -*- coding: utf-8 -*-

import weakref
import os
import os.path
import rspawn
import subprocess
import threading
import base64
import time
import re
import sys
import logging

from nepi.util import server

class TunProtoBase(object):
    def __init__(self, local, peer, home_path, key):
        # Weak references, since ifaces do have a reference to the
        # tunneling protocol implementation - we don't want strong
        # circular references.
        self.peer = weakref.ref(peer)
        self.local = weakref.ref(local)
        
        self.port = 15000
        self.mode = 'pl-tun'
        self.key = key
        
        self.home_path = home_path
        
        self._launcher = None
        self._started = False
        self._starting = False
        self._pid = None
        self._ppid = None
        self._if_name = None

        # Logging
        self._logger = logging.getLogger('nepi.testbeds.planetlab')
    
    def __str__(self):
        local = self.local()
        if local:
            return '<%s for %s>' % (self.__class__.__name__, local)
        else:
            return super(TunProtoBase,self).__str__()

    def _make_home(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to peering interfaces before launching"
        if not local.node:
            raise RuntimeError, "Unconnected TUN - missing node"
        
        # Make sure all the paths are created where 
        # they have to be created for deployment
        # Also remove pidfile, if there is one.
        # Old pidfiles from previous runs can be troublesome.
        cmd = "mkdir -p %(home)s ; rm -f %(home)s/pid" % {
            'home' : server.shell_escape(self.home_path)
        }
        (out,err),proc = server.eintr_retry(server.popen_ssh_command)(
            cmd,
            host = local.node.hostname,
            port = None,
            user = local.node.slicename,
            agent = None,
            ident_key = local.node.ident_path,
            server_key = local.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up TUN forwarder: %s %s" % (out,err,)
        
    
    def _install_scripts(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to peering interfaces before launching"
        if not local.node:
            raise RuntimeError, "Unconnected TUN - missing node"
        
        # Install the tun_connect script and tunalloc utility
        from nepi.util import tunchannel
        sources = [
            os.path.join(os.path.dirname(__file__), 'scripts', 'tun_connect.py'),
            os.path.join(os.path.dirname(__file__), 'scripts', 'tunalloc.c'),
            re.sub(r"([.]py)[co]$", r'\1', tunchannel.__file__, 1), # pyc/o files are version-specific
        ]
        dest = "%s@%s:%s" % (
            local.node.slicename, local.node.hostname, 
            os.path.join(self.home_path,'.'),)
        (out,err),proc = server.eintr_retry(server.popen_scp)(
            sources,
            dest,
            ident_key = local.node.ident_path,
            server_key = local.node.server_key
            )
    
        if proc.wait():
            raise RuntimeError, "Failed upload TUN connect script %r: %s %s" % (sources, out,err,)
        
        # Make sure all dependencies are satisfied
        local.node.wait_dependencies()

        cmd = ( (
            "cd %(home)s && gcc -fPIC -shared tunalloc.c -o tunalloc.so"
            + ( " && "
                "wget -q -c -O python-passfd-src.tar.gz %(passfd_url)s && "
                "mkdir -p python-passfd && "
                "cd python-passfd && "
                "tar xzf ../python-passfd-src.tar.gz --strip-components=1 && "
                "python setup.py build && "
                "python setup.py install --install-lib .. "
                
                if local.tun_proto == "fd" else ""
            ) )
        % {
            'home' : server.shell_escape(self.home_path),
            'passfd_url' : "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/python-passfd/archive/2a6472c64c87.tar.gz",
        } )
        (out,err),proc = server.popen_ssh_command(
            cmd,
            host = local.node.hostname,
            port = None,
            user = local.node.slicename,
            agent = None,
            ident_key = local.node.ident_path,
            server_key = local.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up TUN forwarder: %s %s" % (out,err,)
        
    def launch(self, check_proto, listen, extra_args=[]):
        if self._starting:
            raise AssertionError, "Double start"
        
        self._starting = True
        
        peer = self.peer()
        local = self.local()
        
        if not peer or not local:
            raise RuntimeError, "Lost reference to peering interfaces before launching"
        
        peer_port = peer.tun_port
        peer_addr = peer.tun_addr
        peer_proto= peer.tun_proto
        
        local_port = self.port
        local_cap  = local.capture
        local_addr = local.address
        local_mask = local.netprefix
        local_snat = local.snat
        local_txq  = local.txqueuelen
        local_p2p  = local.pointopoint
        
        if not local_p2p and hasattr(peer, 'address'):
            local_p2p = peer.address

        if check_proto != peer_proto:
            raise RuntimeError, "Peering protocol mismatch: %s != %s" % (check_proto, peer_proto)
        
        if not listen and ((peer_proto != 'fd' and not peer_port) or not peer_addr):
            raise RuntimeError, "Misconfigured peer: %s" % (peer,)
        
        if listen and ((peer_proto != 'fd' and not local_port) or not local_addr or not local_mask):
            raise RuntimeError, "Misconfigured TUN: %s" % (local,)
        
        args = ["python", "tun_connect.py", 
            "-m", str(self.mode),
            "-A", str(local_addr),
            "-M", str(local_mask)]
        
        if check_proto == 'fd':
            passfd_arg = str(peer_addr)
            if passfd_arg.startswith('\x00'):
                # cannot shell_encode null characters :(
                passfd_arg = "base64:"+base64.b64encode(passfd_arg)
            else:
                passfd_arg = '$HOME/'+server.shell_escape(passfd_arg)
            args.extend([
                "--pass-fd", passfd_arg
            ])
        else:
            args.extend([
                "-p", str(local_port if listen else peer_port),
                "-k", str(self.key)
            ])
        
        if local_snat:
            args.append("-S")
        if local_p2p:
            args.extend(("-P",str(local_p2p)))
        if local_txq:
            args.extend(("-Q",str(local_txq)))
        if not local_cap:
            args.append("-N")
        elif local_cap == 'pcap':
            args.extend(('-c','pcap'))
        if extra_args:
            args.extend(map(str,extra_args))
        if not listen and check_proto != 'fd':
            args.append(str(peer_addr))

        self._logger.info("Starting %s", self)
        
        self._make_home()
        self._install_scripts()

        # Start process in a "daemonized" way, using nohup and heavy
        # stdin/out redirection to avoid connection issues
        (out,err),proc = rspawn.remote_spawn(
            " ".join(args),
            
            pidfile = './pid',
            home = self.home_path,
            stdin = '/dev/null',
            stdout = 'capture',
            stderr = rspawn.STDOUT,
            sudo = True,
            
            host = local.node.hostname,
            port = None,
            user = local.node.slicename,
            agent = None,
            ident_key = local.node.ident_path,
            server_key = local.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to set up TUN: %s %s" % (out,err,)
        
        self._started = True
    
    def _launch_and_wait(self, *p, **kw):
        try:
            self.__launch_and_wait(*p, **kw)
        except:
            if self._launcher:
                import sys
                self._launcher._exc.append(sys.exc_info())
            else:
                raise
            
    def __launch_and_wait(self, *p, **kw):
        local = self.local()
        
        self.launch(*p, **kw)
        
        # Wait for the process to be started
        while self.status() == rspawn.NOT_STARTED:
            time.sleep(1.0)
        
        # Wait for the connection to be established
        for spin in xrange(30):
            if self.status() != rspawn.RUNNING:
                self._logger.warn("FAILED TO CONNECT! %s", self)
                break
            
            (out,err),proc = server.eintr_retry(server.popen_ssh_command)(
                "cd %(home)s ; grep -c Connected capture" % dict(
                    home = server.shell_escape(self.home_path)),
                host = local.node.hostname,
                port = None,
                user = local.node.slicename,
                agent = None,
                ident_key = local.node.ident_path,
                server_key = local.node.server_key
                )
            
            if proc.wait():
                break
            
            if out.strip() != '0':
                break
            
            time.sleep(1.0)
        else:
            self._logger.warn("FAILED TO CONNECT! %s", self)
    
    @property
    def if_name(self):
        if not self._if_name:
            # Inspect the trace to check the assigned iface
            local = self.local()
            if local:
                for spin in xrange(30):
                    (out,err),proc = server.eintr_retry(server.popen_ssh_command)(
                        "cd %(home)s ; grep 'Using tun:' capture | head -1" % dict(
                            home = server.shell_escape(self.home_path)),
                        host = local.node.hostname,
                        port = None,
                        user = local.node.slicename,
                        agent = None,
                        ident_key = local.node.ident_path,
                        server_key = local.node.server_key
                        )
                    
                    if proc.wait():
                        return
                    
                    out = out.strip()
                    
                    match = re.match(r"Using +tun: +([-a-zA-Z0-9]*) +.*",out)
                    if match:
                        self._if_name = match.group(1)
        return self._if_name
    
    def async_launch(self, check_proto, listen, extra_args=[]):
        if not self._launcher:
            self._launcher = threading.Thread(
                target = self._launch_and_wait,
                args = (check_proto, listen, extra_args))
            self._launcher._exc = []
            self._launcher.start()
    
    def async_launch_wait(self):
        if self._launcher:
            self._launcher.join()
            if not self._started:
                if self._launcher._exc:
                    exctyp,exval,exctrace = self._launcher._exc[0]
                    raise exctyp,exval,exctrace
                else:
                    raise RuntimeError, "Failed to launch TUN forwarder"
        elif not self._started:
            self.launch()

    def checkpid(self):            
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to local interface"
        
        # Get PID/PPID
        # NOTE: wait a bit for the pidfile to be created
        if self._started and not self._pid or not self._ppid:
            pidtuple = rspawn.remote_check_pid(
                os.path.join(self.home_path,'pid'),
                host = local.node.hostname,
                port = None,
                user = local.node.slicename,
                agent = None,
                ident_key = local.node.ident_path,
                server_key = local.node.server_key
                )
            
            if pidtuple:
                self._pid, self._ppid = pidtuple
    
    def status(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to local interface"
        
        self.checkpid()
        if not self._started:
            return rspawn.NOT_STARTED
        elif not self._pid or not self._ppid:
            return rspawn.NOT_STARTED
        else:
            status = rspawn.remote_status(
                self._pid, self._ppid,
                host = local.node.hostname,
                port = None,
                user = local.node.slicename,
                agent = None,
                ident_key = local.node.ident_path,
                server_key = local.node.server_key
                )
            return status
    
    def kill(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to local interface"
        
        status = self.status()
        if status == rspawn.RUNNING:
            self._logger.info("Stopping %s", self)
            
            # kill by ppid+pid - SIGTERM first, then try SIGKILL
            rspawn.remote_kill(
                self._pid, self._ppid,
                host = local.node.hostname,
                port = None,
                user = local.node.slicename,
                agent = None,
                ident_key = local.node.ident_path,
                server_key = local.node.server_key,
                sudo = True,
                nowait = True
                )
    
    def waitkill(self):
        interval = 1.0
        for i in xrange(30):
            status = self.status()
            if status != rspawn.RUNNING:
                self._logger.info("Stopped %s", self)
                break
            time.sleep(interval)
            interval = min(30.0, interval * 1.1)
    
    _TRACEMAP = {
        # tracename : (remotename, localname)
        'packets' : ('capture','capture'),
        'pcap' : ('pcap','capture.pcap'),
    }
    
    def remote_trace_path(self, whichtrace):
        tracemap = self._TRACEMAP
        
        if whichtrace not in tracemap:
            return None
        
        return os.path.join(self.home_path, tracemap[whichtrace][1])
        
    def sync_trace(self, local_dir, whichtrace):
        tracemap = self._TRACEMAP
        
        if whichtrace not in tracemap:
            return None
        
        local = self.local()
        
        if not local:
            return None
        
        local_path = os.path.join(local_dir, tracemap[whichtrace][1])
        
        # create parent local folders
        if os.path.dirname(local_path):
            proc = subprocess.Popen(
                ["mkdir", "-p", os.path.dirname(local_path)],
                stdout = open("/dev/null","w"),
                stdin = open("/dev/null","r"))

            if proc.wait():
                raise RuntimeError, "Failed to synchronize trace"
        
        # sync files
        (out,err),proc = server.popen_scp(
            '%s@%s:%s' % (local.node.slicename, local.node.hostname, 
                os.path.join(self.home_path, tracemap[whichtrace][0])),
            local_path,
            port = None,
            agent = None,
            ident_key = local.node.ident_path,
            server_key = local.node.server_key
            )
        
        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        return local_path
        
        
    def prepare(self):
        """
        First-phase setup
        
        eg: set up listening ports
        """
        raise NotImplementedError
    
    def setup(self):
        """
        Second-phase setup
        
        eg: connect to peer
        """
        raise NotImplementedError
    
    def shutdown(self):
        """
        Cleanup
        """
        raise NotImplementedError
    
    def destroy(self):
        """
        Second-phase cleanup
        """
        pass
        

class TunProtoUDP(TunProtoBase):
    def __init__(self, local, peer, home_path, key, listening):
        super(TunProtoUDP, self).__init__(local, peer, home_path, key)
        self.listening = listening
    
    def prepare(self):
        pass
    
    def setup(self):
        self.async_launch('udp', False, ("-u",str(self.port)))
    
    def shutdown(self):
        self.kill()

    def destroy(self):
        self.waitkill()

    def launch(self, check_proto='udp', listen=False, extra_args=None):
        if extra_args is None:
            extra_args = ("-u",str(self.port))
        super(TunProtoUDP, self).launch(check_proto, listen, extra_args)

class TunProtoFD(TunProtoBase):
    def __init__(self, local, peer, home_path, key, listening):
        super(TunProtoFD, self).__init__(local, peer, home_path, key)
        self.listening = listening
    
    def prepare(self):
        pass
    
    def setup(self):
        self.async_launch('fd', False)
    
    def shutdown(self):
        self.kill()

    def destroy(self):
        self.waitkill()

    def launch(self, check_proto='fd', listen=False, extra_args=[]):
        super(TunProtoFD, self).launch(check_proto, listen, extra_args)

class TunProtoTCP(TunProtoBase):
    def __init__(self, local, peer, home_path, key, listening):
        super(TunProtoTCP, self).__init__(local, peer, home_path, key)
        self.listening = listening
    
    def prepare(self):
        if self.listening:
            self.async_launch('tcp', True)
    
    def setup(self):
        if not self.listening:
            # make sure our peer is ready
            peer = self.peer()
            if peer and peer.peer_proto_impl:
                peer.peer_proto_impl.async_launch_wait()
            
            if not self._started:
                self.async_launch('tcp', False)
        
        self.checkpid()
    
    def shutdown(self):
        self.kill()

    def destroy(self):
        self.waitkill()

    def launch(self, check_proto='tcp', listen=None, extra_args=[]):
        if listen is None:
            listen = self.listening
        super(TunProtoTCP, self).launch(check_proto, listen, extra_args)

class TapProtoUDP(TunProtoUDP):
    def __init__(self, local, peer, home_path, key, listening):
        super(TapProtoUDP, self).__init__(local, peer, home_path, key, listening)
        self.mode = 'pl-tap'

class TapProtoTCP(TunProtoTCP):
    def __init__(self, local, peer, home_path, key, listening):
        super(TapProtoTCP, self).__init__(local, peer, home_path, key, listening)
        self.mode = 'pl-tap'

class TapProtoFD(TunProtoFD):
    def __init__(self, local, peer, home_path, key, listening):
        super(TapProtoFD, self).__init__(local, peer, home_path, key, listening)
        self.mode = 'pl-tap'



TUN_PROTO_MAP = {
    'tcp' : TunProtoTCP,
    'udp' : TunProtoUDP,
    'fd'  : TunProtoFD,
}

TAP_PROTO_MAP = {
    'tcp' : TapProtoTCP,
    'udp' : TapProtoUDP,
    'fd'  : TapProtoFD,
}


