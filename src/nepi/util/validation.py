#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ipaddr

def is_bool(value):
    return isinstance(value, bool)

def is_integer(value):
    return isinstance(value, int)

def is_string(value):
    return isinstance(value, str)

def is_ip4_address(value):
    try:
        ipaddr.IPv4(value)
    except ipaddr.Error:
        return False
    return True

def is_ip6_address(value):
    try:
        ipaddr.IPv6(value)
    except ipaddr.Error:
        return False
    return True

