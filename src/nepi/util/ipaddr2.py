#!/usr/bin/env python
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
    cksum = sum(words)
    if len(packet)&0x1:
       cksum += ord(packet[-1])
    cksum = (cksum >> 16) + (cksum & 0xffff)
    cksum += (cksum >> 16)
    return ~cksum

def iphdr(src, dst, datalen, ttl, proto):
    cksum = 0
    src = socket.inet_aton(src)
    dst = socket.inet_aton(dst)
    hdr = struct.pack('!BBHHHBBH4s4s', 
        0x45, 0, datalen + 5*32, int(random.random() * 65536) & 0xffff, 0, 
        ttl, proto, cksum & 0xffff, src, dst)
    cksum = inet_cksum(hdr)
    hdr = struct.pack('!BBHHHBBH4s4s', 
        0x45, 0, datalen + 5*32, int(random.random() * 65536) & 0xffff, 0, 
        ttl, proto, cksum & 0xffff, src, dst)
    return hdr

def igmp(type, mxrt, grp):
    cksum = 0
    grp = socket.inet_aton(grp)
    ighdr = struct.pack('!BBH4s', type, mxrt, cksum & 0xffff, grp)
    cksum = inet_cksum(ighdr)
    ighdr = struct.pack('!BBH4s', type, mxrt, cksum & 0xffff, grp)
    return ighdr


