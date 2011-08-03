import select
import sys
import os
import struct
import socket
import threading
import errno
import fcntl
import traceback
import functools
import collections

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
def etherProto(packet, len=len):
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

def _packetReady(buf, ether_mode=False, len=len):
    if not buf:
        return False
        
    rv = False
    while not rv:
        if len(buf[0]) < 4:
            rv = False
        elif ether_mode:
            rv = True
        else:
            _,totallen = struct.unpack('HH',buf[0][:4])
            totallen = socket.htons(totallen)
            rv = len(buf[0]) >= totallen
        if not rv and len(buf) > 1:
            nbuf = ''.join(buf)
            buf.clear()
            buf.append(nbuf)
        else:
            return rv
    return rv

def _pullPacket(buf, ether_mode=False, len=len):
    if ether_mode:
        return buf.popleft()
    else:
        _,totallen = struct.unpack('HH',buf[0][:4])
        totallen = socket.htons(totallen)
        if len(buf[0]) < totallen:
            rv = buf[0][:totallen]
            buf[0] = buf[0][totallen:]
        else:
            rv = buf.popleft()
        return rv

def etherStrip(buf):
    if len(buf) < 14:
        return ""
    if buf[12:14] == '\x08\x10' and buf[16:18] == '\x08\x00':
        # tagged ethernet frame
        return buf[18:]
    elif buf[12:14] == '\x08\x00':
        # untagged ethernet frame
        return buf[14:]
    else:
        return ""

def etherWrap(packet):
    return ''.join((
        "\x00"*6*2 # bogus src and dst mac
        +"\x08\x00", # IPv4
        packet, # payload
        "\x00"*4, # bogus crc
    ))

def piStrip(buf, len=len):
    if len(buf) < 4:
        return buf
    else:
        return buf[4:]
    
def piWrap(buf, ether_mode, etherProto=etherProto):
    if ether_mode:
        proto = etherProto(buf)
    else:
        proto = "\x08\x00"
    return ''.join((
        "\x00\x00", # PI: 16 bits flags
        proto, # 16 bits proto
        buf,
    ))

_padmap = [ chr(padding) * padding for padding in xrange(127) ]
del padding

def encrypt(packet, crypter, len=len, padmap=_padmap):
    # pad
    padding = crypter.block_size - len(packet) % crypter.block_size
    packet += padmap[padding]
    
    # encrypt
    return crypter.encrypt(packet)

def decrypt(packet, crypter, ord=ord):
    # decrypt
    packet = crypter.decrypt(packet)
    
    # un-pad
    padding = ord(packet[-1])
    if not (0 < padding <= crypter.block_size):
        # wrong padding
        raise RuntimeError, "Truncated packet"
    packet = packet[:-padding]
    
    return packet

def nonblock(fd):
    try:
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fl |= os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, fl)
        return True
    except:
        traceback.print_exc(file=sys.stderr)
        # Just ignore
        return False

def tun_fwd(tun, remote, with_pi, ether_mode, cipher_key, udp, TERMINATE, stderr=sys.stderr, reconnect=None, rwrite=None, rread=None, tunqueue=1000, tunkqueue=1000,
        len=len, max=max, OSError=OSError, cipher='AES'):
    crypto_mode = False
    try:
        if cipher_key:
            import Crypto.Cipher
            import hashlib
            __import__('Crypto.Cipher.'+cipher)
            
            ciphername = cipher
            cipher = getattr(Crypto.Cipher, cipher)
            hashed_key = hashlib.sha256(cipher_key).digest()
            if getattr(cipher, 'key_size'):
                hashed_key = hashed_key[:cipher.key_size]
            elif ciphername == 'DES3':
                hashed_key = hashed_key[:24]
            crypter = cipher.new(
                hashed_key, 
                cipher.MODE_ECB)
            crypto_mode = True
    except:
        traceback.print_exc(file=sys.stderr)
        crypto_mode = False
        crypter = None

    if stderr is not None:
        if crypto_mode:
            print >>stderr, "Packets are transmitted in CIPHER"
        else:
            print >>stderr, "Packets are transmitted in PLAINTEXT"
    
    if hasattr(remote, 'fileno'):
        remote_fd = remote.fileno()
        if rwrite is None:
            def rwrite(remote, packet, os_write=os.write):
                return os_write(remote_fd, packet)
        if rread is None:
            def rread(remote, maxlen, os_read=os.read):
                return os_read(remote_fd, maxlen)
    
    rnonblock = nonblock(remote)
    tnonblock = nonblock(tun)
    
    # Limited frame parsing, to preserve packet boundaries.
    # Which is needed, since /dev/net/tun is unbuffered
    maxbkbuf = maxfwbuf = max(10,tunqueue-tunkqueue)
    tunhurry = max(0,maxbkbuf/2)
    fwbuf = collections.deque()
    bkbuf = collections.deque()
    if ether_mode:
        packetReady = bool
        pullPacket = collections.deque.popleft
    else:
        packetReady = _packetReady
        pullPacket = _pullPacket
    tunfd = tun.fileno()
    os_read = os.read
    os_write = os.write
    while not TERMINATE:
        wset = []
        if packetReady(bkbuf):
            wset.append(tun)
        if packetReady(fwbuf):
            wset.append(remote)
        
        rset = []
        if len(fwbuf) < maxfwbuf:
            rset.append(tun)
        if len(bkbuf) < maxbkbuf:
            rset.append(remote)
        
        try:
            rdrdy, wrdy, errs = select.select(rset,wset,(tun,remote),1)
        except select.error, e:
            if e.args[0] == errno.EINTR:
                # just retry
                continue

        # check for errors
        if errs:
            if reconnect is not None and remote in errs and tun not in errs:
                remote = reconnect()
                if hasattr(remote, 'fileno'):
                    remote_fd = remote.fileno()
            elif udp and remote in errs and tun not in errs:
                # In UDP mode, those are always transient errors
                pass
            else:
                break
        
        # check to see if we can write
        #rr = wr = rt = wt = 0
        if remote in wrdy:
            try:
                try:
                    while True:
                        packet = pullPacket(fwbuf)

                        if crypto_mode:
                            enpacket = encrypt(packet, crypter)
                        else:
                            enpacket = packet
                        
                        # try twice - sometimes it barks the first time,
                        # due to ICMP Port Unreachable packets from previous writes
                        try:
                            rwrite(remote, enpacket)
                        except socket.error:
                            rwrite(remote, enpacket)
                        #wr += 1
                        
                        if stderr is not None:
                            print >>stderr, '>', formatPacket(packet, ether_mode)
                        
                        if not rnonblock or not packetReady(fwbuf):
                            break
                except OSError,e:
                    # This except handles the entire While block on PURPOSE
                    # as an optimization (setting a try/except block is expensive)
                    # The only operation that can raise this exception is rwrite
                    if e.errno == os.errno.EWOULDBLOCK:
                        # re-schedule packet
                        fwbuf.insert(0, packet)
                    else:
                        raise
            except:
                if reconnect is not None:
                    # in UDP mode, sometimes connected sockets can return a connection refused.
                    # Give the caller a chance to reconnect
                    remote = reconnect()
                    if hasattr(remote, 'fileno'):
                        remote_fd = remote.fileno()
                elif not udp:
                    # in UDP mode, we ignore errors - packet loss man...
                    raise
                traceback.print_exc(file=sys.stderr)
        if tun in wrdy:
            try:
                while True:
                    packet = pullPacket(bkbuf)
                    if stderr is not None:
                        formatted = formatPacket(packet, ether_mode)
                    if with_pi:
                        packet = piWrap(packet, ether_mode)
                    os_write(tunfd, packet)
                    #wt += 1
                    if stderr is not None:
                        print >>stderr, '<', formatted
                    
                    # Do not inject packets into the TUN faster than they arrive, unless we're falling
                    # behind. TUN devices discard packets if their queue is full (tunkqueue), but they
                    # don't block either (they're always ready to write), so if we flood the device 
                    # we'll have high packet loss.
                    if not tnonblock or len(bkbuf) < tunhurry or not packetReady(bkbuf):
                        break
            except OSError,e:
                # This except handles the entire While block on PURPOSE
                # as an optimization (setting a try/except block is expensive)
                # The only operation that can raise this exception is os_write
                if e.errno == os.errno.EWOULDBLOCK:
                    # re-schedule packet
                    bkbuf.insert(0, packet)
                else:
                    raise
        
        # check incoming data packets
        if tun in rdrdy:
            try:
                while True:
                    packet = os_read(tunfd,2000) # tun.read blocks until it gets 2k!
                    #rt += 1
                    if with_pi:
                        packet = piStrip(packet)
                    fwbuf.append(packet)
                    
                    if not tnonblock or len(fwbuf) >= maxfwbuf:
                        break
            except OSError,e:
                # This except handles the entire While block on PURPOSE
                # as an optimization (setting a try/except block is expensive)
                # The only operation that can raise this exception is os_read
                if e.errno != os.errno.EWOULDBLOCK:
                    raise
        if remote in rdrdy:
            try:
                try:
                    while True:
                        # Try twice, sometimes it barks the first time, 
                        # due to ICMP Port Unreachable packets from previous writes
                        try:
                            packet = rread(remote,2000)
                        except socket.error:
                            packet = rread(remote,2000)
                        #rr += 1
                        
                        if crypto_mode:
                            packet = decrypt(packet, crypter)
                        bkbuf.append(packet)
                        
                        if not rnonblock or len(bkbuf) >= maxbkbuf:
                            break
                except OSError,e:
                    # This except handles the entire While block on PURPOSE
                    # as an optimization (setting a try/except block is expensive)
                    # The only operation that can raise this exception is rread
                    if e.errno != os.errno.EWOULDBLOCK:
                        raise
            except Exception, e:
                if reconnect is not None:
                    # in UDP mode, sometimes connected sockets can return a connection refused
                    # on read. Give the caller a chance to reconnect
                    remote = reconnect()
                    if hasattr(remote, 'fileno'):
                        remote_fd = remote.fileno()
                elif not udp:
                    # in UDP mode, we ignore errors - packet loss man...
                    raise
                traceback.print_exc(file=sys.stderr)
        
        #print >>sys.stderr, "rr:%d\twr:%d\trt:%d\twt:%d" % (rr,wr,rt,wt)



