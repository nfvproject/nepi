#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ipaddr
import re

def is_enum(attribute, value):
    return isinstance(value, str) and value in attribute.allowed

def is_bool(attribute, value):
    return isinstance(value, bool)

def is_integer(attribute, value):
    return isinstance(value, int)

def is_string(attribute, value):
    return isinstance(value, str)

def is_ip4_address(attribute, value):
    try:
        ipaddr.IPv4Address(value)
    except ipaddr.AddressValueError:
        return False
    return True

def is_ip6_address(attribute, value):
    try:
        ipaddr.IPv6Address(value)
    except ipaddr.AddressValueError:
        return False
    return True

def is_mac_address(attribute, value):
    regex = r'^([0-9a-zA-Z]{0,2}:)*[0-9a-zA-Z]{0,2}'
    found = re.search(regex, value)
    if not found or value.count(':') != 5:
        return False
    return True

