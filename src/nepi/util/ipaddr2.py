# -*- coding: utf-8 -*-

import struct
import random
import socket
import array

def ipv4_dot2mask(mask):
    mask = mask.split('.',4) # a.b.c.d -> [a,b,c,d]
    mask = map(int,mask) # to ints
    
    n = 0
    while mask and mask[0] == 0xff:
        n += 8
        del mask[0]
    
    if mask:
        mask = mask[0]
        while mask:
            n += 1
            mask = (mask << 1) & 0xff
    
    return n

def ipv4_mask2dot(mask):
    mask = ((1L << mask)-1) << (32 - mask)
    mask = struct.pack(">I",mask)
    mask = '.'.join(map(str,map(ord,mask)))
    return mask

def ipdist(a,b):
    a = struct.unpack('!L',socket.inet_aton(a))[0]
    b = struct.unpack('!L',socket.inet_aton(b))[0]
    d = 32
    while d and (b&0x80000000)==(a&0x80000000):
        a <<= 1
        b <<= 1
        d -= 1
    return d

def ipdistn(a,b):
    d = 32
    while d and (b&0x80000000)==(a&0x80000000):
        a <<= 1
        b <<= 1
        d -= 1
    return d

def inet_cksum(packet):
    words = array.array('H')
    words.fromstring(packet[:len(packet)&~0x1])
    htons = socket.htons
    cksum = 0
    for word in words:
        cksum += htons(word)
    if len(packet)&0x1:
        cksum += ord(packet[-1])
    cksum &= 0xffffffff
    cksum = (cksum >> 16) + (cksum & 0xffff)
    cksum += (cksum >> 16)
    return ~cksum

def iphdr(src, dst, datalen, ttl, proto, tos=0, nocksum=False, ipid=0):
    cksum = 0
    src = socket.inet_aton(src)
    dst = socket.inet_aton(dst)
    hdr = struct.pack('!BBHHHBBH4s4s', 
        0x45, tos, datalen + 5*4, ipid, 0, 
        ttl, proto, cksum & 0xffff, src, dst)
    if not nocksum:
        cksum = inet_cksum(hdr)
        hdr = struct.pack('!BBHHHBBH4s4s', 
            0x45, tos, datalen + 5*4, ipid, 0, 
            ttl, proto, cksum & 0xffff, src, dst)
    return hdr

def igmp(type, mxrt, grp, nocksum=False):
    cksum = 0
    grp = socket.inet_aton(grp)
    ighdr = struct.pack('!BBH4s', type, mxrt, cksum & 0xffff, grp)
    if not nocksum:
        cksum = inet_cksum(ighdr)
        ighdr = struct.pack('!BBH4s', type, mxrt, cksum & 0xffff, grp)
    return ighdr

def ipigmp(src, dst, ttl, type, mxrt, grp, noipcksum=False, noigmpcksum=False):
    igmpp = igmp(type, mxrt, grp, nocksum=noigmpcksum)
    iph = iphdr(src, dst, len(igmpp), ttl, 2, tos=0xc0, nocksum=noipcksum)
    return iph+igmpp


