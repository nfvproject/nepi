#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

