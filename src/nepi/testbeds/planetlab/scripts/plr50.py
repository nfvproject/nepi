import random

random.seed(1234)

def accept_packet(packet, direction, rng=random.random):
    return direction or rng() > 0.5


