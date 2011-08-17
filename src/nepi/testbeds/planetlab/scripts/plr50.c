#include <stdlib.h>
#include <stdio.h>

static int plr = 50;

int init(const char* args)
{
    sscanf(args, "plr=%d", &plr);
}

int accept_packet(const char* packet, int direction)
{
    return (direction != 0) || (rand() > (RAND_MAX*100/plr));
}

