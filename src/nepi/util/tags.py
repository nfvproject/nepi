#!/usr/bin/env python
# -*- coding: utf-8 -*-

MOBILE = "mobile"
NODE = "node"
INTERFACE = "interface"
WIRELESS = "wireless"
APPLICATION = "application"
NAT = "nat"
ROUTER = "router" 
SWITCH = "switch"
PPP = "point-to-point"
PROTOCOL = "protocol"
TUNNEL = "tunnel"
INTERNET = "internet"
HUB = "hub"
ALLOW_ADDRESSES = "allow_addresses"
ALLOW_ROUTES = "allow_routes"
HAS_ADDRESSES = "has_addresses"
HAS_ROUTES = "has_routes"

class Taggable(object):
    def __init__(self):
        super(Taggable, self).__init__()
        self._tags = list()

    @property
    def tags(self):
        return self._tags

    def add_tag(self, tag_id):
        self._tags.append(tag_id)

    def has_tag(self, tag_id):
        return tag_id in self._tags

