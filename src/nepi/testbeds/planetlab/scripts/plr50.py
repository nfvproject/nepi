import random

_plr = 0.5

random.seed(1234)

def init(plr):
    global _plr
    _plr = float(plr) / 100.0

def accept_packet(packet, direction, rng=random.random):
    return direction or rng() > _plr


