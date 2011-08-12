import random

def accept_packet(packet, direction, rng=random.random):
    return rng() > 0.5


