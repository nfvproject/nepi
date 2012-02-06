# -*- coding: utf-8 -*-

ADDRESS = "address"
APPLICATION = "application"
CHANNEL = "channel"
CONTROLLER = "controller"
CONTAINER = "container"
DELAY_MODEL = "delay model"
DEPLOYMENT = "deployment"
ENERGY_MODEL = "Energy model"
ERROR_MODEL = "Error model"
EXPERIMENT = "experiment"
HUB = "hub"
INTERFACE = "interface"
INTERNET = "internet"
LOSS_MODEL = "loss model"
MAC_MODEL = "MAC model"
MANAGER = "manager"
MOBILE = "mobile"
NAT = "nat"
NODE = "node"
PHY_MODEL = "PHY model"
PPP = "point-to-point"
PROTOCOL = "protocol"
QUEUE = "queue"
ROUTE = "route"
ROUTING = "routing"
SERVICE_FLOW = "service flow"
SWITCH = "switch"
TUNNEL = "tunnel"
WIRELESS = "wireless"
TRACE = "trace"

class Taggable(object):
    def __init__(self):
        super(Taggable, self).__init__()
        self._tags = set()

    @property
    def tags(self):
        return self._tags

    def add_tag(self, tag_id):
        self._tags.add(tag_id)

    def has_tag(self, tag_id):
        return tag_id in self._tags

