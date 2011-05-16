import os

class TunChannel(object):
    """
    Helper box class that implements most of the required boilerplate
    for tunnelling cross connections.
    
    The class implements a threaded forwarder that runs in the
    testbed controller process. It takes several parameters that
    can be given by directly setting attributes:
    
        tun_port/addr/proto: information about the local endpoint.
            The addresses here should be externally-reachable,
            since when listening or when using the UDP protocol,
            connections to this address/port will be attempted
            by remote endpoitns.
        
        peer_port/addr/proto: information about the remote endpoint.
            Usually, you set these when the cross connection 
            initializer/completion functions are invoked (both).
        
        tun_key: the agreed upon encryption key.
        
        listen: if set to True (and in TCP mode), it marks a
            listening endpoint. Be certain that any TCP connection
            is made between a listening and a non-listening
            endpoint, or it won't work.
        
        with_pi: set if the incoming packet stream (see tun_socket)
            contains PI headers - if so, they will be stripped.
        
        ethernet_mode: set if the incoming packet stream is
            composed of ethernet frames (as opposed of IP packets).
        
        tun_socket: a socket or file object that can be read
            from and written to. Packets will be read when available,
            remote packets will be forwarded as writes.
            A socket should be of type SOCK_SEQPACKET (or SOCK_DGRAM
            if not possible), a file object should preserve packet
            boundaries (ie, a pipe or TUN/TAP device file descriptor).
        
        trace_target: a file object where trace output will be sent.
            It cannot be changed after launch.
            By default, it's sys.stderr
    """
    
    def __init__(self):
        # These get initialized when the channel is configured
        # They're part of the TUN standard attribute set
        self.tun_port = None
        self.tun_addr = None
        
        # These get initialized when the channel is connected to its peer
        self.peer_proto = None
        self.peer_addr = None
        self.peer_port = None
        
        # These get initialized when the channel is connected to its iface
        self.tun_socket = None

        # same as peer proto, but for execute-time standard attribute lookups
        self.tun_proto = None 
        
        # some state
        self.prepared = False
        self.listen = False
        self._terminate = [] # terminate signaller
        self._connected = threading.Event()
        self._forwarder_thread = None
        
        # trace to stderr
        self.stderr = sys.stderr
        
        # Generate an initial random cryptographic key to use for tunnelling
        # Upon connection, both endpoints will agree on a common one based on
        # this one.
        self.tun_key = ( ''.join(map(chr, [ 
                    r.getrandbits(8) 
                    for i in xrange(32) 
                    for r in (random.SystemRandom(),) ])
                ).encode("base64").strip() )        
        

    def __str__(self):
        return "%s<ip:%s/%s %s%s>" % (
            self.__class__.__name__,
            self.address, self.netprefix,
            " up" if self.up else " down",
            " snat" if self.snat else "",
        )

    def Prepare(self):
        if not self.udp and self.listen and not self._forwarder_thread:
            if self.listen or (self.peer_addr and self.peer_port and self.peer_proto):
                self._launch()
    
    def Setup(self):
        if not self._forwarder_thread:
            self._launch()
    
    def Cleanup(self):
        if self._forwarder_thread:
            self.Kill()

    def Wait(self):
        if self._forwarder_thread:
            self._connected.wait()

    def Kill(self):    
        if self._forwarder_thread:
            if not self._terminate:
                self._terminate.append(None)
            self._forwarder_thread.join()

    def _launch(self):
        # Launch forwarder thread with a weak reference
        # to self, so that we don't create any strong cycles
        # and automatic refcounting works as expected
        self._forwarder_thread = threading.Thread(
            self._forwarder,
            args = (weakref.ref(self),) )
        self._forwarder_thread.start()
    
    @staticmethod
    def _forwarder(weak_self):
        # grab strong reference
        self = weak_self()
        if not self:
            return
        
        peer_port = self.peer_port
        peer_addr = self.peer_addr
        peer_proto= self.peer_proto

        local_port = self.tun_port
        local_addr = self.tun_addr
        local_proto = self.tun_proto
        
        stderr = self.stderr
        
        if local_proto != peer_proto:
            raise RuntimeError, "Peering protocol mismatch: %s != %s" % (local_proto, peer_proto)
        
        udp = local_proto == 'udp'
        listen = self.listen

        if (udp or not listen) and (not peer_port or not peer_addr):
            raise RuntimeError, "Misconfigured peer for: %s" % (self,)

        if (udp or listen) and (not local_port or not local_addr):
            raise RuntimeError, "Misconfigured TUN: %s" % (self,)
        
        TERMINATE = self._terminate
        cipher_key = self.tun_key
        tun = self.tun_socket
        
        if not tun:
            raise RuntimeError, "Unconnected TUN channel %s" % (self,)
        
        if udp:
            # listen on udp port
            if remaining_args and not remaining_args[0].startswith('-'):
                rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
                rsock.bind((local_addr,local_port))
                rsock.connect((peer_addr,peer_port))
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        elif listen:
            # accept tcp connections
            lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            lsock.bind((local_addr,local_port))
            lsock.listen(1)
            rsock,raddr = lsock.accept()
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        else:
            # connect to tcp server
            rsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            for i in xrange(30):
                try:
                    rsock.connect((peer_addr,peer_port))
                    break
                except socket.error:
                    # wait a while, retry
                    time.sleep(1)
            else:
                rsock.connect((peer_addr,peer_port))
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        
        # notify that we're ready
        self._connected.set()
        
        # drop strong reference
        del self
        
        tun_fwd(tun, remote,
            with_pi = False, 
            ether_mode = True, 
            cipher_key = cipher_key, 
            udp = udp, 
            TERMINATE = TERMINATE,
            stderr = stderr
        )
        
        tun.close()
        remote.close()


def create_tunchannel(testbed_instance, guid, devnull = []):
    """
    TunChannel factory for metadata.
    By default, silences traceing.
    
    You can override the created element's attributes if you will.
    """
    if not devnull:
        # just so it's not open if not needed
        devnull.append(open("/dev/null","w"))
    element = TunChannel()
    element.stderr = devnull[0] # silence tracing
    testbed_instance._elements[guid] = element

def preconfigure_tunchannel(testbed_instance, guid):
    """
    TunChannel preconfiguration.
    
    It initiates the forwarder thread for listening tcp channels.
    
    Takes the public address from the operating system, so it should be adequate
    for most situations when the TunChannel forwarder thread runs in the same
    process as the testbed controller.
    """
    element = testbed_instance._elements[guid]
    
    # Find external interface, if any
    public_addr = os.popen(
        "/sbin/ifconfig "
        "| grep $(ip route | grep default | awk '{print $3}' "
                "| awk -F. '{print $1\"[.]\"$2}') "
        "| head -1 | awk '{print $2}' "
        "| awk -F : '{print $2}'").read().rstrip()
    element.tun_addr = public_addr

    # Set standard TUN attributes
    if not element.tun_port and element.tun_addr:
        element.tun_port = 15000 + int(guid)

    # First-phase setup
    if element.peer_proto:
        # cross tun
        if not element.tun_addr or not element.tun_port:
            listening = True
        elif not element.peer_addr or not element.peer_port:
            listening = True
        else:
            # both have addresses...
            # ...the one with the lesser address listens
            listening = element.tun_addr < element.peer_addr
        element.listen = listening
        element.Prepare()

def postconfigure_tunchannel(testbed_instance, guid):
    """
    TunChannel preconfiguration.
    
    Initiates the forwarder thread for connecting tcp channels or 
    udp channels in general.
    
    Should be adequate for most implementations.
    """
    element = testbed_instance._elements[guid]
    
    # Second-phase setup
    element.Setup()


def crossconnect_tunchannel_peer_init(proto, testbed_instance, tun_guid, peer_data,
        preconfigure_tunchannel = preconfigure_tunchannel):
    """
    Cross-connection initialization.
    Should be adequate for most implementations.
    
    For use in metadata, bind the first "proto" argument with the connector type. Eg:
    
        conn_init = functools.partial(crossconnect_tunchannel_peer_init, "tcp")
    
    If you don't use the stock preconfigure function, specify your own as a keyword argument.
    """
    tun = testbed_instance._elements[tun_guid]
    tun.peer_addr = peer_data.get("tun_addr")
    tun.peer_proto = peer_data.get("tun_proto") or proto
    tun.peer_port = peer_data.get("tun_port")
    tun.tun_key = min(tun.tun_key, peer_data.get("tun_key"))
    tun.tun_proto = proto
    
    preconfigure_tunchannel(testbed_instance, tun_guid)

def crossconnect_tunchannel_peer_compl(proto, testbed_instance, tun_guid, peer_data,
        postconfigure_tunchannel = postconfigure_tunchannel):
    """
    Cross-connection completion.
    Should be adequeate for most implementations.
    
    For use in metadata, bind the first "proto" argument with the connector type. Eg:
    
        conn_init = functools.partial(crossconnect_tunchannel_peer_compl, "tcp")
    
    If you don't use the stock postconfigure function, specify your own as a keyword argument.
    """
    # refresh (refreshable) attributes for second-phase
    tun = testbed_instance._elements[tun_guid]
    tun.peer_addr = peer_data.get("tun_addr")
    tun.peer_proto = peer_data.get("tun_proto") or proto
    tun.peer_port = peer_data.get("tun_port")
    
    postconfigure_tunchannel(testbed_instance, tun_guid)

    

def wait_tunchannel(testbed_instance, guid):
    """
    Wait for the channel forwarder to be up and running.
    
    Useful as a start function to assure proper startup synchronization,
    be certain to start TunChannels before applications that might require them.
    """
    element = testbed_instance.elements[guid]
    element.Wait()

