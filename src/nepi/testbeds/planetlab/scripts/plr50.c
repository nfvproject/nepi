#include <stdlib.h>

int accept_packet(const char* packet, int direction)
{
    return (direction != 0) || (rand() > (RAND_MAX/2));
}

