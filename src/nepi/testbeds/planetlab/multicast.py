# -*- coding: utf-8 -*-

from constants import TESTBED_ID

import os
import os.path
import sys
import functools

import nepi.util.server as server
import nepi.util.ipaddr2 as ipaddr2

import logging

import application

class MulticastForwarder(application.Application):
    """
    This application installs a userspace packet forwarder
    that, when connected to a node, filters all packets
    flowing through multicast-capable virtual interfaces
    and applies custom-specified routing policies
    """
    def __init__(self, *p, **kw):
        super(MulticastForwarder, self).__init__(*p, **kw)
        
        self.sources = ' '.join([
            os.path.join( os.path.dirname(__file__),
                "scripts", "mcastfwd.py" ),
            ipaddr2.__file__.replace('.pyc','.py').replace('.pyo','.py'),
        ])
        
        self.sudo = True
        
        self.depends = "python"
        
        # Initialized when connected
        self.ifaces = []
        self.router = None
    
    def _command_get(self):
        cmd = "python mcastfwd.py "
        if not self.router:
            cmd += "-R "
        cmd += ' '.join([iface.address for iface in self.ifaces])
        return cmd
    def _command_set(self, value):
        # ignore
        return
    command = property(_command_get, _command_set)
    
        
class MulticastAnnouncer(application.Application):
    """
    This application installs a userspace daemon that
    monitors multicast membership and announces it on all
    multicast-capable interfaces.
    This does not usually happen automatically on PlanetLab slivers.
    """
    def __init__(self, *p, **kw):
        super(MulticastAnnouncer, self).__init__(*p, **kw)
        
        self.sources = ' '.join([
            os.path.join( os.path.dirname(__file__),
                "scripts", "mcastfwd.py" ),
            ipaddr2.__file__.replace('.pyc','.py').replace('.pyo','.py'),
        ])
        
        self.sudo = True
        
        self.depends = "python"
        
        self.ifaces = []
        self.router = None
    
    def _command_get(self):
        return (
            "python mcastfwd.py -A %s"
        ) % ( ' '.join([iface.address for iface in self.ifaces]), )
    def _command_set(self, value):
        # ignore
        return
    command = property(_command_get, _command_set)

class MulticastRouter(application.Application):
    """
    This application installs a userspace daemon that
    monitors multicast membership and announces it on all
    multicast-capable interfaces.
    This does not usually happen automatically on PlanetLab slivers.
    """
    ALGORITHM_MAP = {
        'dvmrp' : {
            'sources' :
                ' '.join([
                    os.path.join( os.path.dirname(__file__),
                        "scripts", "mrouted-3.9.5-pl.patch" ),
                ]) ,
            'depends' : "",
            'buildDepends' : "byacc gcc make patch",
            'build' : 
                "mkdir -p mrouted && "
                "echo '3a1c1e72c4f6f7334d72df4c50b510d7  mrouted-3.9.5.tar.bz2' > archive_sums.txt && "
                "wget -q -c -O mrouted-3.9.5.tar.bz2 ftp://ftp.vmlinux.org/pub/People/jocke/mrouted/mrouted-3.9.5.tar.bz2 && "
                "md5sum -c archive_sums.txt && "
                "tar xvjf mrouted-3.9.5.tar.bz2 -C mrouted --strip-components=1 && "
                "cd mrouted && patch -p1 < ${SOURCES}/mrouted-3.9.5-pl.patch && make"
                ,
            'install' : "cp mrouted/mrouted ${SOURCES}",
            'command' : 
                "while test \\! -e /var/run/mcastrt ; do sleep 1 ; done ; "
                "echo 'phyint eth0 disable' > ./mrouted.conf ; "
                "for iface in %(nonifaces)s ; do echo \"phyint $iface disable\" >> ./mrouted.conf ; done ; "
                "./mrouted -f %(debugbit)s -c ./mrouted.conf"
                ,
            'debugbit' : "-dpacket,igmp,routing,interface,pruning,membership,cache",
        }
    }
    
    def __init__(self, *p, **kw):
        super(MulticastRouter, self).__init__(*p, **kw)
        
        self.algorithm = 'dvmrp'
        self.sudo = True
        self.nonifaces = []
    
    def _non_set(self, value):
        # ignore
        return
    
    def _gen_get(attribute, self):
        return self.ALGORITHM_MAP[self.algorithm][attribute]
    
    def _command_get(self):
        command = self.ALGORITHM_MAP[self.algorithm]['command']
        debugbit = self.ALGORITHM_MAP[self.algorithm]['debugbit']
        
        # download rpms and pack into a tar archive
        return command % {
            'nonifaces' : ' '.join([iface.if_name for iface in self.nonifaces if iface.if_name]),
            'debugbit' : (debugbit if self.stderr else ""),
        }
    command = property(_command_get, _non_set)

    build = property(functools.partial(_gen_get, "build"), _non_set)
    install = property(functools.partial(_gen_get, "install"), _non_set)
    sources = property(functools.partial(_gen_get, "sources"), _non_set)
    depends = property(functools.partial(_gen_get, "depends"), _non_set)
    buildDepends = property(functools.partial(_gen_get, "buildDepends"), _non_set)

