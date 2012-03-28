import select
import sys
import os
import struct
import socket
import threading
import traceback
import errno
import fcntl
import random
import traceback
import functools
import collections
import ctypes
import time

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
        if packet[12] == "\x81" and packet[13] == "\x00":
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

def _packetReady(buf, ether_mode=False, len=len, str=str):
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
            # collapse only first two buffers
            # as needed, to mantain len(buf) meaningful
            p1 = buf.popleft()
            buf[0] = p1+str(buf[0])
        else:
            return rv
    return rv

def _pullPacket(buf, ether_mode=False, len=len, buffer=buffer):
    if ether_mode:
        return buf.popleft()
    else:
        _,totallen = struct.unpack('HH',buf[0][:4])
        totallen = socket.htons(totallen)
        if len(buf[0]) > totallen:
            rv = buffer(buf[0],0,totallen)
            buf[0] = buffer(buf[0],totallen)
        else:
            rv = buf.popleft()
        return rv

def etherStrip(buf, buffer=buffer, len=len):
    if len(buf) < 14:
        return ""
    if buf[12:14] == '\x08\x10' and buf[16:18] == '\x08\x00':
        # tagged ethernet frame
        return buffer(buf, 18)
    elif buf[12:14] == '\x08\x00':
        # untagged ethernet frame
        return buffer(buf, 14)
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
        return buffer(buf,4)
    
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
    if packet:
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

def tun_fwd(tun, remote, with_pi, ether_mode, cipher_key, udp, TERMINATE, SUSPEND,
        stderr = sys.stderr, reconnect = None, rwrite = None, rread = None,
        tunqueue = 1000, tunkqueue = 1000, cipher = 'AES', accept_local = None, 
        accept_remote = None, slowlocal = True, queueclass = None, 
        bwlimit = None, len = len, max = max, min = min, buffer = buffer,
        OSError = OSError, select = select.select, selecterror = select.error, 
        os = os, socket = socket,
        retrycodes=(os.errno.EWOULDBLOCK, os.errno.EAGAIN, os.errno.EINTR) ):
    crypto_mode = False
    crypter = None

    try:
        if cipher_key and cipher:
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
    
    # Pick up TUN/TAP writing method
    if with_pi:
        try:
            import iovec
            
            # We have iovec, so we can skip PI injection
            # and use iovec which does it natively
            if ether_mode:
                twrite = iovec.ethpiwrite
                tread = iovec.piread2
            else:
                twrite = iovec.ippiwrite
                tread = iovec.piread2
        except ImportError:
            # We have to inject PI headers pythonically
            def twrite(fd, packet, oswrite=os.write, piWrap=piWrap, ether_mode=ether_mode):
                return oswrite(fd, piWrap(packet, ether_mode))
            
            # For reading, we strip PI headers with buffer slicing and that's it
            def tread(fd, maxlen, osread=os.read, piStrip=piStrip):
                return piStrip(osread(fd, maxlen))
    else:
        # No need to inject PI headers
        twrite = os.write
        tread = os.read
    
    encrypt_ = encrypt
    decrypt_ = decrypt
    xrange_ = xrange

    if accept_local is not None:
        def tread(fd, maxlen, _tread=tread, accept=accept_local):
            packet = _tread(fd, maxlen)
            if accept(packet, 0):
                return packet
            else:
                return None

    if accept_remote is not None:
        if crypto_mode:
            def decrypt_(packet, crypter, decrypt_=decrypt_, accept=accept_remote):
                packet = decrypt_(packet, crypter)
                if accept(packet, 1):
                    return packet
                else:
                    return None
        else:
            def rread(fd, maxlen, _rread=rread, accept=accept_remote):
                packet = _rread(fd, maxlen)
                if accept(packet, 1):
                    return packet
                else:
                    return None
    
    maxbkbuf = maxfwbuf = max(10,tunqueue-tunkqueue)
    tunhurry = max(0,maxbkbuf/2)
    
    if queueclass is None:
        queueclass = collections.deque
        maxbatch = 2000
        maxtbatch = 50
    else:
        maxfwbuf = maxbkbuf = 2000000000
        maxbatch = 50
        maxtbatch = 30
        tunhurry = 30
    
    fwbuf = queueclass()
    bkbuf = queueclass()
    nfwbuf = 0
    nbkbuf = 0
    
    # backwards queue functions
    # they may need packet inspection to 
    # reconstruct packet boundaries
    if ether_mode or udp:
        packetReady = bool
        pullPacket = queueclass.popleft
        reschedule = queueclass.appendleft
    else:
        packetReady = _packetReady
        pullPacket = _pullPacket
        reschedule = queueclass.appendleft
    
    # forward queue functions
    # no packet inspection needed
    fpacketReady = bool
    fpullPacket = queueclass.popleft
    freschedule = queueclass.appendleft
    
    tunfd = tun.fileno()
    os_read = os.read
    os_write = os.write
    
    tget = time.time
    maxbwfree = bwfree = 1500 * tunqueue
    lastbwtime = tget()
    
    remoteok = True
    
    
    while not TERMINATE:
        # The SUSPEND flag has been set. This means we need to wait on
        # the SUSPEND condition until it is released.
        while SUSPEND:
            time.sleep(0.5)

        wset = []
        if packetReady(bkbuf):
            wset.append(tun)
        if remoteok and fpacketReady(fwbuf) and (not bwlimit or bwfree > 0):
            wset.append(remote)
        
        rset = []
        if len(fwbuf) < maxfwbuf:
            rset.append(tun)
        if remoteok and len(bkbuf) < maxbkbuf:
            rset.append(remote)
        
        if remoteok:
            eset = (tun,remote)
        else:
            eset = (tun,)
        
        try:
            rdrdy, wrdy, errs = select(rset,wset,eset,1)
        except selecterror, e:
            if e.args[0] == errno.EINTR:
                # just retry
                continue
            else:
                traceback.print_exc(file=sys.stderr)
                # If the SUSPEND flag has been set, then the TUN will be in a bad
                # state and the select error should be ignores.
                if SUSPEND:
                    continue
                else:
                    raise

        # check for errors
        if errs:
            if reconnect is not None and remote in errs and tun not in errs:
                remote = reconnect()
                if hasattr(remote, 'fileno'):
                    remote_fd = remote.fileno()
            elif udp and remote in errs and tun not in errs:
                # In UDP mode, those are always transient errors
                # Usually, an error will imply a read-ready socket
                # that will raise an "Connection refused" error, so
                # disable read-readiness just for now, and retry
                # the select
                remoteok = False
                continue
            else:
                break
        else:
            remoteok = True
        
        # check to see if we can write
        #rr = wr = rt = wt = 0
        if remote in wrdy:
            sent = 0
            try:
                try:
                    for x in xrange(maxbatch):
                        packet = pullPacket(fwbuf)

                        if crypto_mode:
                            packet = encrypt_(packet, crypter)
                        
                        sentnow = rwrite(remote, packet)
                        sent += sentnow
                        #wr += 1
                        
                        if not udp and 0 <= sentnow < len(packet):
                            # packet partially sent
                            # reschedule the remaining part
                            # this doesn't happen ever in udp mode
                            freschedule(fwbuf, buffer(packet,sentnow))
                        
                        if not rnonblock or not fpacketReady(fwbuf):
                            break
                except OSError,e:
                    # This except handles the entire While block on PURPOSE
                    # as an optimization (setting a try/except block is expensive)
                    # The only operation that can raise this exception is rwrite
                    if e.errno in retrycodes:
                        # re-schedule packet
                        freschedule(fwbuf, packet)
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
                #traceback.print_exc(file=sys.stderr)
            
            if bwlimit:
                bwfree -= sent
        if tun in wrdy:
            try:
                for x in xrange(maxtbatch):
                    packet = pullPacket(bkbuf)
                    twrite(tunfd, packet)
                    #wt += 1
                    
                    # Do not inject packets into the TUN faster than they arrive, unless we're falling
                    # behind. TUN devices discard packets if their queue is full (tunkqueue), but they
                    # don't block either (they're always ready to write), so if we flood the device 
                    # we'll have high packet loss.
                    if not tnonblock or (slowlocal and len(bkbuf) < tunhurry) or not packetReady(bkbuf):
                        break
                else:
                    if slowlocal:
                        # Give some time for the kernel to process the packets
                        time.sleep(0)
            except OSError,e:
                # This except handles the entire While block on PURPOSE
                # as an optimization (setting a try/except block is expensive)
                # The only operation that can raise this exception is os_write
                if e.errno in retrycodes:
                    # re-schedule packet
                    reschedule(bkbuf, packet)
                else:
                    raise
        
        # check incoming data packets
        if tun in rdrdy:
            try:
                for x in xrange(maxbatch):
                    packet = tread(tunfd,2000) # tun.read blocks until it gets 2k!
                    if not packet:
                        continue
                    #rt += 1
                    fwbuf.append(packet)
                    
                    if not tnonblock or len(fwbuf) >= maxfwbuf:
                        break
            except OSError,e:
                # This except handles the entire While block on PURPOSE
                # as an optimization (setting a try/except block is expensive)
                # The only operation that can raise this exception is os_read
                if e.errno not in retrycodes:
                    raise
        if remote in rdrdy:
            try:
                try:
                    for x in xrange(maxbatch):
                        packet = rread(remote,2000)
                        
                        #rr += 1
                        
                        if crypto_mode:
                            packet = decrypt_(packet, crypter)
                            if not packet:
                                continue
                        elif not packet:
                            if not udp and packet == "":
                                # Connection broken, try to reconnect (or just die)
                                raise RuntimeError, "Connection broken"
                            else:
                                continue

                        bkbuf.append(packet)
                        
                        if not rnonblock or len(bkbuf) >= maxbkbuf:
                            break
                except OSError,e:
                    # This except handles the entire While block on PURPOSE
                    # as an optimization (setting a try/except block is expensive)
                    # The only operation that can raise this exception is rread
                    if e.errno not in retrycodes:
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

        if bwlimit:
            tnow = tget()
            delta = tnow - lastbwtime
            if delta > 0.001:
                delta = int(bwlimit * delta)
                if delta > 0:
                    bwfree = min(bwfree+delta, maxbwfree)
                    lastbwtime = tnow
        
        #print >>sys.stderr, "rr:%d\twr:%d\trt:%d\twt:%d" % (rr,wr,rt,wt)

def udp_connect(TERMINATE, local_addr, local_port, peer_addr, peer_port):
    rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    retrydelay = 1.0
    for i in xrange(30):
        # TERMINATE is a array. An item can be added to TERMINATE, from
        # outside this function to force termination of the loop
        if TERMINATE:
            raise OSError, "Killed"
        try:
            rsock.bind((local_addr, local_port))
            break
        except socket.error:
            # wait a while, retry
            print >>sys.stderr, "%s: Could not bind. Retrying in a sec..." % (time.strftime('%c'),)
            time.sleep(min(30.0,retrydelay))
            retrydelay *= 1.1
    else:
        rsock.bind((local_addr, local_port))
    print >>sys.stderr, "Listening UDP at: %s:%d" % (local_addr, local_port)
    print >>sys.stderr, "Connecting UDP to: %s:%d" % (peer_addr, peer_port)
    rsock.connect((peer_addr, peer_port))
    return rsock

def udp_handshake(TERMINATE, rsock):
    endme = False
    def keepalive():
        while not endme and not TERMINATE:
            try:
                rsock.send('')
            except:
                pass
            time.sleep(1)
        try:
            rsock.send('')
        except:
            pass
    keepalive_thread = threading.Thread(target=keepalive)
    keepalive_thread.start()
    for i in xrange(900):
        if TERMINATE:
            raise OSError, "Killed"
        try:
            heartbeat = rsock.recv(10)
            break
        except:
            time.sleep(1)
    else:
        heartbeat = rsock.recv(10)
    endme = True
    keepalive_thread.join()

def udp_establish(TERMINATE, local_addr, local_port, peer_addr, peer_port):
    rsock = udp_connect(TERMINATE, local_addr, local_port, peer_addr,
            peer_port)
    udp_handshake(TERMINATE, rsock)
    return rsock 

def tcp_connect(TERMINATE, stop, rsock, peer_addr, peer_port):
    sock = None
    retrydelay = 1.0
    # The peer has a firewall that prevents a response to the connect, we 
    # will be forever blocked in the connect, so we put a reasonable timeout.
    rsock.settimeout(10) 
    # We wait for 
    for i in xrange(30):
        if stop:
            break
        if TERMINATE:
            raise OSError, "Killed"
        try:
            rsock.connect((peer_addr, peer_port))
            sock = rsock
            break
        except socket.error:
            # wait a while, retry
            print >>sys.stderr, "%s: Could not connect. Retrying in a sec..." % (time.strftime('%c'),)
            time.sleep(min(30.0,retrydelay))
            retrydelay *= 1.1
    else:
        rsock.connect((peer_addr, peer_port))
        sock = rsock
    if sock:
        print >>sys.stderr, "tcp_connect: TCP sock connected to remote %s:%s" % (peer_addr, peer_port)
        sock.settimeout(0) 
        
        print >>sys.stderr, "tcp_connect: disabling NAGLE"
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock

def tcp_listen(TERMINATE, stop, lsock, local_addr, local_port):
    sock = None
    retrydelay = 1.0
    # We try to bind to the local virtual interface. 
    # It might not exist yet so we wait in a loop.
    for i in xrange(30):
        if stop:
            break
        if TERMINATE:
            raise OSError, "Killed"
        try:
            lsock.bind((local_addr, local_port))
            break
        except socket.error:
            # wait a while, retry
            print >>sys.stderr, "%s: Could not bind. Retrying in a sec..." % (time.strftime('%c'),)
            time.sleep(min(30.0,retrydelay))
            retrydelay *= 1.1
    else:
        lsock.bind((local_addr, local_port))

    print >>sys.stderr, "tcp_listen: TCP sock listening in local sock %s:%s" % (local_addr, local_port)
    # Now we wait until the other side connects. 
    # The other side might not be ready yet, so we also wait in a loop for timeouts.
    timeout = 1
    lsock.listen(1)
    for i in xrange(30):
        if TERMINATE:
            raise OSError, "Killed"
        rlist, wlist, xlist = select.select([lsock], [], [], timeout)
        if stop:
            break
        if lsock in rlist:
            sock,raddr = lsock.accept()
            print >>sys.stderr, "tcp_listen: TCP connection accepted in local sock %s:%s" % (local_addr, local_port)
            break
        timeout += 5
    return sock

def tcp_handshake(rsock, listen, hand):
    # we are going to use a barrier algorithm to decide wich side listen.
    # each side will "roll a dice" and send the resulting value to the other 
    # side. 
    win = False
    rsock.settimeout(10)
    try:
        rsock.send(hand)
        peer_hand = rsock.recv(4)
        if not peer_hand:
            print >>sys.stderr, "tcp_handshake: connection reset by peer"
            return False
        else:
            print >>sys.stderr, "tcp_handshake: hand %r, peer_hand %r" % (hand, peer_hand)
        if hand < peer_hand:
            if listen:
                win = True
        elif hand > peer_hand:
            if not listen:
                win = True
    finally:
        rsock.settimeout(0)
    return win

def tcp_establish(TERMINATE, local_addr, local_port, peer_addr, peer_port):
    def listen(stop, hand, lsock, lresult):
        win = False
        rsock = tcp_listen(TERMINATE, stop, lsock, local_addr, local_port)
        if rsock:
            win = tcp_handshake(rsock, True, hand)
            stop.append(True)
        lresult.append((win, rsock))

    def connect(stop, hand, rsock, rresult):
        win = False
        rsock = tcp_connect(TERMINATE, stop, rsock, peer_addr, peer_port)
        if rsock:
            win = tcp_handshake(rsock, False, hand)
            stop.append(True)
        rresult.append((win, rsock))
  
    end = False
    sock = None
    for i in xrange(0, 50):
        if end:
            break
        if TERMINATE:
            raise OSError, "Killed"
        hand = struct.pack("!L", random.randint(0, 2**30))
        stop = []
        lresult = []
        rresult = []
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        rsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        listen_thread = threading.Thread(target=listen, args=(stop, hand, lsock, lresult))
        connect_thread = threading.Thread(target=connect, args=(stop, hand, rsock, rresult))
        connect_thread.start()
        listen_thread.start()
        connect_thread.join()
        listen_thread.join()
        (lwin, lrsock) = lresult[0]
        (rwin, rrsock) = rresult[0]
        if not lrsock or not rrsock:
            if not lrsock:
                sock = rrsock
            if not rrsock:
                sock = lrsock
            end = True
        # both socket are connected
        else:
           if lwin:
                sock = lrsock
                end = True
           elif rwin: 
                sock = rrsock
                end = True

    if not sock:
        raise OSError, "Error: tcp_establish could not establish connection."
    return sock


