#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct

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

