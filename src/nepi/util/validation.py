#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ipaddr
import re

def is_bool(value):
    return isinstance(value, bool)

def is_integer(value):
    return isinstance(value, int)

def is_string(value):
    return isinstance(value, str)

def is_ip4_address(value):
    try:
        ipaddr.IPv4Address(value)
    except ipaddr.AddressValueError:
        return False
    return True

def is_ip6_address(value):
    try:
        ipaddr.IPv6Address(value)
    except ipaddr.AddressValueError:
        return False
    return True

def is_mac_address(value):
    regex = r'^([0-9a-zA-Z]{0,2}:)*[0-9a-zA-Z]{0,2}'
    found = re.search(regex, value)
    if not found or value.count(':') != 5:
        return False
    return True

