import select
import sys
import os
import struct
import socket
import threading
import errno

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

    if stderr is not None:
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
        
        try:
            rdrdy, wrdy, errs = select.select((tun,remote),wset,(tun,remote),1)
        except select.error, e:
            if e.args[0] == errno.EINTR:
                # just retry
                continue
        
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
            if stderr is not None:
                print >>stderr, '>', formatPacket(packet, ether_mode)
        if tun in wrdy and packetReady(bkbuf, ether_mode):
            packet, bkbuf = pullPacket(bkbuf, ether_mode)
            if stderr is not None:
                formatted = formatPacket(packet, ether_mode)
            if with_pi:
                packet = piWrap(packet, ether_mode)
            os.write(tun.fileno(), packet)
            if stderr is not None:
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



