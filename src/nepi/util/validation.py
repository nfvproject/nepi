#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ipaddr
import re

def is_enum(attribute, value):
    return isinstance(value, str) and value in attribute.allowed

def is_bool(attribute, value):
    return isinstance(value, bool)

def is_double(attribute, value):
    return isinstance(value, float)

def is_integer(attribute, value, min=None, max=None):
    if not isinstance(value, int):
        return False
    if min is not None and value < min:
        return False
    if max is not None and value > max:
        return False
    return True

def is_integer_range(min=None, max=None):
    def is_integer_range(attribute, value):
        if not isinstance(value, int):
            return False
        if min is not None and value < min:
            return False
        if max is not None and value > max:
            return False
        return True
    return is_integer_range


def is_string(attribute, value):
    return isinstance(value, str)

def is_time(attribute, value):
    return isinstance(value, str) # TODO: Missing validation!

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

# TODO: Allow netrefs!
def is_ip_address(attribute, value):
    if not is_ip4_address(attribute, value) and \
            not is_ip6_address(attribute, value):
        return False
    return True

def is_mac_address(attribute, value):
    regex = r'^([0-9a-zA-Z]{0,2}:)*[0-9a-zA-Z]{0,2}'
    found = re.search(regex, value)
    if not found or value.count(':') != 5:
        return False
    return True

