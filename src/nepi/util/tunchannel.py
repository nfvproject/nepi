import select
import sys
import os
import struct
import socket
import threading

def ipfmt(ip):
    ipbytes = map(ord,ip.decode("hex"))
    return '.'.join(map(str,ipbytes))

tagtype = {
    '0806' : 'arp',
    '0800' : 'ipv4',
    '8870' : 'jumbo',
    '8863' : 'PPPoE discover',
    '8864' : 'PPPoE',
    '86dd' : 'ipv6',
}
def etherProto(packet):
    packet = packet.encode("hex")
    if len(packet) > 14:
        if packet[12:14] == "\x81\x00":
            # tagged
            return packet[16:18]
        else:
            # untagged
            return packet[12:14]
    # default: ip
    return "\x08\x00"
def formatPacket(packet, ether_mode):
    if ether_mode:
        stripped_packet = etherStrip(packet)
        if not stripped_packet:
            packet = packet.encode("hex")
            if len(packet) < 28:
                return "malformed eth " + packet.encode("hex")
            else:
                if packet[24:28] == "8100":
                    # tagged
                    ethertype = tagtype.get(packet[32:36], 'eth')
                    return ethertype + " " + ( '-'.join( (
                        packet[0:12], # MAC dest
                        packet[12:24], # MAC src
                        packet[24:32], # VLAN tag
                        packet[32:36], # Ethertype/len
                        packet[36:], # Payload
                    ) ) )
                else:
                    # untagged
                    ethertype = tagtype.get(packet[24:28], 'eth')
                    return ethertype + " " + ( '-'.join( (
                        packet[0:12], # MAC dest
                        packet[12:24], # MAC src
                        packet[24:28], # Ethertype/len
                        packet[28:], # Payload
                    ) ) )
        else:
            packet = stripped_packet
    packet = packet.encode("hex")
    if len(packet) < 48:
        return "malformed ip " + packet
    else:
        return "ip " + ( '-'.join( (
            packet[0:1], #version
            packet[1:2], #header length
            packet[2:4], #diffserv/ECN
            packet[4:8], #total length
            packet[8:12], #ident
            packet[12:16], #flags/fragment offs
            packet[16:18], #ttl
            packet[18:20], #ip-proto
            packet[20:24], #checksum
            ipfmt(packet[24:32]), # src-ip
            ipfmt(packet[32:40]), # dst-ip
            packet[40:48] if (int(packet[1],16) > 5) else "", # options
            packet[48:] if (int(packet[1],16) > 5) else packet[40:], # payload
        ) ) )

def packetReady(buf, ether_mode):
    if len(buf) < 4:
        return False
    elif ether_mode:
        return True
    else:
        _,totallen = struct.unpack('HH',buf[:4])
        totallen = socket.htons(totallen)
        return len(buf) >= totallen

def pullPacket(buf, ether_mode):
    if ether_mode:
        return buf, ""
    else:
        _,totallen = struct.unpack('HH',buf[:4])
        totallen = socket.htons(totallen)
        return buf[:totallen], buf[totallen:]

def etherStrip(buf):
    if len(buf) < 14:
        return ""
    if buf[12:14] == '\x08\x10' and buf[16:18] in '\x08\x00':
        # tagged ethernet frame
        return buf[18:]
    elif buf[12:14] == '\x08\x00':
        # untagged ethernet frame
        return buf[14:]
    else:
        return ""

def etherWrap(packet):
    return (
        "\x00"*6*2 # bogus src and dst mac
        +"\x08\x00" # IPv4
        +packet # payload
        +"\x00"*4 # bogus crc
    )

def piStrip(buf):
    if len(buf) < 4:
        return buf
    else:
        return buf[4:]
    
def piWrap(buf, ether_mode):
    if ether_mode:
        proto = etherProto(buf)
    else:
        proto = "\x08\x00"
    return (
        "\x00\x00" # PI: 16 bits flags
        +proto # 16 bits proto
        +buf
    )

def encrypt(packet, crypter):
    # pad
    padding = crypter.block_size - len(packet) % crypter.block_size
    packet += chr(padding) * padding
    
    # encrypt
    return crypter.encrypt(packet)

def decrypt(packet, crypter):
    # decrypt
    packet = crypter.decrypt(packet)
    
    # un-pad
    padding = ord(packet[-1])
    if not (0 < padding <= crypter.block_size):
        # wrong padding
        raise RuntimeError, "Truncated packet"
    packet = packet[:-padding]
    
    return packet


def tun_fwd(tun, remote, with_pi, ether_mode, cipher_key, udp, TERMINATE, stderr=sys.stderr):
    crypto_mode = False
    try:
        if cipher_key:
            import Crypto.Cipher.AES
            import hashlib
            
            hashed_key = hashlib.sha256(cipher_key).digest()
            crypter = Crypto.Cipher.AES.new(
                hashed_key, 
                Crypto.Cipher.AES.MODE_ECB)
            crypto_mode = True
    except:
        import traceback
        traceback.print_exc()
        crypto_mode = False
        crypter = None

    if crypto_mode:
        print >>stderr, "Packets are transmitted in CIPHER"
    else:
        print >>stderr, "Packets are transmitted in PLAINTEXT"
    
    # Limited frame parsing, to preserve packet boundaries.
    # Which is needed, since /dev/net/tun is unbuffered
    fwbuf = ""
    bkbuf = ""
    while not TERMINATE:
        wset = []
        if packetReady(bkbuf, ether_mode):
            wset.append(tun)
        if packetReady(fwbuf, ether_mode):
            wset.append(remote)
        rdrdy, wrdy, errs = select.select((tun,remote),wset,(tun,remote),1)
        
        # check for errors
        if errs:
            break
        
        # check to see if we can write
        if remote in wrdy and packetReady(fwbuf, ether_mode):
            packet, fwbuf = pullPacket(fwbuf, ether_mode)
            try:
                if crypto_mode:
                    enpacket = encrypt(packet, crypter)
                else:
                    enpacket = packet
                os.write(remote.fileno(), enpacket)
            except:
                if not udp:
                    # in UDP mode, we ignore errors - packet loss man...
                    raise
            print >>stderr, '>', formatPacket(packet, ether_mode)
        if tun in wrdy and packetReady(bkbuf, ether_mode):
            packet, bkbuf = pullPacket(bkbuf, ether_mode)
            formatted = formatPacket(packet, ether_mode)
            if with_pi:
                packet = piWrap(packet, ether_mode)
            os.write(tun.fileno(), packet)
            print >>stderr, '<', formatted
        
        # check incoming data packets
        if tun in rdrdy:
            packet = os.read(tun.fileno(),2000) # tun.read blocks until it gets 2k!
            if with_pi:
                packet = piStrip(packet)
            fwbuf += packet
        if remote in rdrdy:
            try:
                packet = os.read(remote.fileno(),2000) # remote.read blocks until it gets 2k!
                if crypto_mode:
                    packet = decrypt(packet, crypter)
            except:
                if not udp:
                    # in UDP mode, we ignore errors - packet loss man...
                    raise
            bkbuf += packet



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

