#!/usr/bin/env python
# -*- coding: utf-8 -*-

import weakref
import os
import os.path
import rspawn
import subprocess
import threading
import base64

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
        self._pid = None
        self._ppid = None

    def _make_home(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to peering interfaces before launching"
        if not local.node:
            raise RuntimeError, "Unconnected TUN - missing node"
        
        # Make sure all the paths are created where 
        # they have to be created for deployment
        cmd = "mkdir -p %s" % (server.shell_escape(self.home_path),)
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
        
    
    def _install_scripts(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to peering interfaces before launching"
        if not local.node:
            raise RuntimeError, "Unconnected TUN - missing node"
        
        # Install the tun_connect script and tunalloc utility
        sources = [
            os.path.join(os.path.dirname(__file__), 'scripts', 'tun_connect.py'),
            os.path.join(os.path.dirname(__file__), 'scripts', 'tunalloc.c'),
        ]
        dest = "%s@%s:%s" % (
            local.node.slicename, local.node.hostname, 
            os.path.join(self.home_path,'.'),)
        (out,err),proc = server.popen_scp(
            sources,
            dest,
            ident_key = local.node.ident_path,
            server_key = local.node.server_key
            )
    
        if proc.wait():
            raise RuntimeError, "Failed upload TUN connect script %r: %s %s" % (source, out,err,)

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
        
        if check_proto != peer_proto:
            raise RuntimeError, "Peering protocol mismatch: %s != %s" % (check_proto, peer_proto)
        
        if not listen and (not peer_port or not peer_addr):
            raise RuntimeError, "Misconfigured peer: %s" % (peer,)
        
        if listen and (not local_port or not local_addr or not local_mask):
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
        if local_txq:
            args.extend(("-Q",str(local_txq)))
        if extra_args:
            args.extend(map(str,extra_args))
        if not listen and check_proto != 'fd':
            args.append(str(peer_addr))
        
        self._make_home()
        self._install_scripts()
        
        # Start process in a "daemonized" way, using nohup and heavy
        # stdin/out redirection to avoid connection issues
        (out,err),proc = rspawn.remote_spawn(
            " ".join(args),
            
            pidfile = './pid',
            home = self.home_path,
            stdin = '/dev/null',
            stdout = 'capture' if local_cap else '/dev/null',
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
    
    def async_launch(self, check_proto, listen, extra_args=[]):
        if not self._launcher:
            self._launcher = threading.Thread(
                target = self.launch,
                args = (check_proto, listen, extra_args))
            self._launcher.start()
    
    def async_launch_wait(self):
        if not self._started:
            if self._launcher:
                self._launcher.join()
                if not self._started:
                    raise RuntimeError, "Failed to launch TUN forwarder"
            else:
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
                ident_key = local.node.ident_path
                )
            return status
    
    def kill(self):
        local = self.local()
        
        if not local:
            raise RuntimeError, "Lost reference to local interface"
        
        status = self.status()
        if status == rspawn.RUNNING:
            # kill by ppid+pid - SIGTERM first, then try SIGKILL
            rspawn.remote_kill(
                self._pid, self._ppid,
                host = local.node.hostname,
                port = None,
                user = local.node.slicename,
                agent = None,
                ident_key = local.node.ident_path,
                server_key = local.node.server_key,
                sudo = True
                )
        
    def sync_trace(self, local_dir, whichtrace):
        if whichtrace != 'packets':
            return None
        
        local = self.local()
        
        if not local:
            return None
        
        local_path = os.path.join(local_dir, 'capture')
        
        # create parent local folders
        proc = subprocess.Popen(
            ["mkdir", "-p", os.path.dirname(local_path)],
            stdout = open("/dev/null","w"),
            stdin = open("/dev/null","r"))

        if proc.wait():
            raise RuntimeError, "Failed to synchronize trace: %s %s" % (out,err,)
        
        # sync files
        (out,err),proc = server.popen_scp(
            '%s@%s:%s' % (local.node.slicename, local.node.hostname, 
                os.path.join(self.home_path, 'capture')),
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
                self.launch('tcp', False)
        else:
            # make sure WE are ready
            self.async_launch_wait()
        
        self.checkpid()
    
    def shutdown(self):
        self.kill()

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


