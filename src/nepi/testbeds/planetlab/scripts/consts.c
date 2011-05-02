#include <stdio.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/ioctl.h>
#include <linux/if_tun.h>
#include <linux/if.h>

int main()
{
	printf("ETH_P_ALL = 0x%08x\n", ETH_P_ALL);
	printf("ETH_P_IP = 0x%08x\n", ETH_P_IP);
	printf("TUNSETIFF = 0x%08x\n", TUNSETIFF);
	printf("IFF_NO_PI = 0x%08x\n", IFF_NO_PI);
	printf("IFF_TAP = 0x%08x\n", IFF_TAP);
	printf("IFF_TUN = 0x%08x\n", IFF_TUN);
	printf("IFF_VNET_HDR = 0x%08x\n", IFF_VNET_HDR);
	printf("TUN_PKT_STRIP = 0x%08x\n", TUN_PKT_STRIP);
	printf("IFHWADDRLEN = 0x%08x\n", IFHWADDRLEN);
	printf("IFNAMSIZ = 0x%08x\n", IFNAMSIZ);
	printf("IFREQ_SZ = 0x%08x\n", sizeof(struct ifreq));
	printf("FIONREAD = 0x%08x\n", FIONREAD);
	return 0;
}
