#include <stdlib.h>
#include <stdio.h>

static int plr = 50;

int init(const char* args)
{
    int seed;
    int rv;
    seed = 1234;
    rv = sscanf(args, "plr=%d,seed=%d", &plr, &seed);
    srand(seed);
    return rv;
}

int accept_packet(const char* packet, int direction)
{
    return (direction != 0) || (rand() > (RAND_MAX/100*plr));
}

