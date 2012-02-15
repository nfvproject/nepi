
ADDRESS = 0
ADDRESSABLE = 1
APPLICATION = 2 
CHANNEL = 3
EC = 4 # Experiment Controller
CONTAINER = 5
DELAY_MODEL = 6
DEPLOYMENT = 7 
ENERGY_MODEL = 8
ERROR_MODEL = 9
EXPERIMENT = 10
FILTER = 11
HUB = 12
INTERFACE = 13
INTERNET = 14
LOSS_MODEL = 15 
MAC_MODEL = 16
RATE_MANAGER = 17
MOBILE = 18
NAT = 19
NODE = 20 
PHY_MODEL = 21
PPP = 22 
PROTOCOL = 23
QUEUE = 24
ROUTE = 25
ROUTABLE = 26
ROUTING = 27
SERVICE_FLOW = 28
SWITCH = 29
TUNNEL = 30
WIRELESS = 31
TRACE = 32
TC = 33 # Testbed Controller
SIMULATION = 34
EMULATION = 35
PHYSICAL_TESTBED = 36

tag2text = dict({
    ADDRESS: "address",
    ADDRESSABLE: "addressable",
    APPLICATION: "application",
    CHANNEL: "channel",
    EC: "experiment controller",
    CONTAINER: "container",
    DELAY_MODEL: "delay model",
    DEPLOYMENT: "deployment",
    ENERGY_MODEL: "Energy model",
    ERROR_MODEL: "Error model",
    EXPERIMENT: "experiment",
    FILTER: "filter",
    HUB: "hub",
    INTERFACE: "interface",
    INTERNET: "internet",
    LOSS_MODEL: "loss model",
    MAC_MODEL: "MAC model",
    RATE_MANAGER: "Rate control manager",
    MOBILE: "mobile",
    NAT: "nat",
    NODE: "node",
    PHY_MODEL: "PHY model",
    PPP: "point-to-point",
    PROTOCOL: "protocol",
    QUEUE: "queue",
    ROUTE: "route",
    ROUTABLE: "routable",
    ROUTING: "routing",
    SERVICE_FLOW: "service flow",
    SWITCH: "switch",
    TUNNEL: "tunnel",
    WIRELESS: "wireless",
    TRACE:"trace",
    TC: "testbed controller",
    SIMULATION: "simulation",
    EMULATION: "emulation",
    PHYSICAL_TESTBED: "physical testbed",
})

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

