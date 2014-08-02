import errno
import os
import time
import signal
import socket
import tunchannel
import struct
import fcntl

from optparse import OptionParser

IFF_TUN = 0x0001
IFF_TAP     = 0x0002
IFF_NO_PI   = 0x1000
TUNSETIFF   = 0x400454ca

# Trak SIGTERM, and set global termination flag instead of dying
TERMINATE = []
def _finalize(sig,frame):
    global TERMINATE
    TERMINATE.append(None)
signal.signal(signal.SIGTERM, _finalize)

# SIGUSR1 suspends forwading, SIGUSR2 resumes forwarding
SUSPEND = []
def _suspend(sig,frame):
    global SUSPEND
    if not SUSPEND:
        SUSPEND.append(None)
signal.signal(signal.SIGUSR1, _suspend)

def _resume(sig,frame):
    global SUSPEND
    if SUSPEND:
        SUSPEND.remove(None)
signal.signal(signal.SIGUSR2, _resume)

def open_tap(vif_name, vif_type, pi):
    flags = 0
    flags |= vif_type

    if not pi:
        flags |= IFF_NO_PI

    fd = os.open("/dev/net/tun", os.O_RDWR)

    err = fcntl.ioctl(fd, TUNSETIFF, struct.pack("16sH", vif_name, flags))
    if err < 0:
        os.close(fd)
        raise RuntimeError("Could not configure device %s" % vif_name)

    return fd

def get_options():
    usage = ("usage: %prog -N <vif_name> -t <vif-type> -p <pi> "
            "-b <bwlimit> -c <cipher> -k <cipher-key> -q <txqueuelen> " 
            "-l <local-port-file> -r <remote-port-file> -H <remote-host> "
            "-R <ret-file> ")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-N", "--vif-name", dest="vif_name",
        help = "The name of the virtual interface",
        type="str")

    parser.add_option("-t", "--vif-type", dest="vif_type",
        help = "Virtual interface type. Either IFF_TAP or IFF_TUN. "
            "Defaults to IFF_TAP. ", 
        default = IFF_TAP,
        type="str")

    parser.add_option("-n", "--pi", dest="pi", 
            action="store_true", 
            default = False,
            help="Enable PI header")

    parser.add_option("-b", "--bwlimit", dest="bwlimit",
        help = "Specifies the interface's emulated bandwidth in bytes ",
        default = None, type="int")

    parser.add_option("-q", "--txqueuelen", dest="txqueuelen",
        help = "Specifies the interface's transmission queue length. ",
        default = 1000, type="int")

    parser.add_option("-c", "--cipher", dest="cipher",
        help = "Cipher to encript communication. "
            "One of PLAIN, AES, Blowfish, DES, DES3. ",
        default = None, type="str")

    parser.add_option("-k", "--cipher-key", dest="cipher_key",
        help = "Specify a symmetric encryption key with which to protect "
            "packets across the tunnel. python-crypto must be installed "
            "on the system." ,
        default = None, type="str")

    parser.add_option("-l", "--local-port-file", dest="local_port_file",
        help = "File where to store the local binded UDP port number ", 
        default = "local_port_file", type="str")

    parser.add_option("-r", "--remote-port-file", dest="remote_port_file",
        help = "File where to read the remote UDP port number to connect to", 
        default = "remote_port_file", type="str")

    parser.add_option("-H", "--remote-host", dest="remote_host",
        help = "Remote host IP", 
        default = "remote_host", type="str")

    parser.add_option("-R", "--ret-file", dest="ret_file",
        help = "File where to store return code (success of connection) ", 
        default = "ret_file", type="str")

    (options, args) = parser.parse_args()
       
    if options.vif_type == "IFF_TUN":
        vif_type = IFF_TUN

    return ( options.vif_name, vif_type, options.pi, 
            options.local_port_file, options.remote_port_file, 
            options.remote_host, options.ret_file, options.bwlimit, 
            options.cipher, options.cipher_key, options.txqueuelen )

if __name__ == '__main__':

    ( vif_name, vif_type, pi, local_port_file, remote_port_file,
      remote_host, ret_file, bwlimit, cipher, cipher_key, txqueuelen 
         ) = get_options()
   
    # Get the file descriptor of the TAP device from the process
    # that created it
    fd = open_tap(vif_name, vif_type, pi)

    # Create a local socket to stablish the tunnel connection
    hostaddr = socket.gethostbyname(socket.gethostname())
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.bind((hostaddr, 0))
    (local_host, local_port) = sock.getsockname()

    # Save local port information to file
    f = open(local_port_file, 'w')
    f.write("%d\n" % local_port)
    f.close()

    # Wait until remote port information is available
    while not os.path.exists(remote_port_file):
        time.sleep(2)

    remote_port = ''
    # Read remote port from file
    # Try until something is read...
    # xxx: There seems to be a weird behavior where
    #       even if the file exists and had the port number,
    #       the read operation returns empty string!
    #       Maybe a race condition?
    for i in xrange(10):
        f = open(remote_port_file, 'r')
        remote_port = f.read()
        f.close()

        if remote_port:
            break
        
        time.sleep(2)
    
    remote_port = remote_port.strip()
    remote_port = int(remote_port)

    # Connect local socket to remote port
    sock.connect((remote_host, remote_port))
    remote = os.fdopen(sock.fileno(), 'r+b', 0)

    # TODO: Test connectivity!    

    # Create a ret_file to indicate success
    f = open(ret_file, 'w')
    f.write("0")
    f.close()

    # Establish tunnel
    tunchannel.tun_fwd(tun, remote,
        with_pi = True, # Planetlab TAP devices add PI headers 
        ether_mode = (vif_type == IFF_TAP),
        udp = True,
        cipher_key = cipher_key,
        cipher = cipher,
        TERMINATE = TERMINATE,
        SUSPEND = SUSPEND,
        tunqueue = txqueuelen,
        tunkqueue = 500,
        bwlimit = bwlimit
    ) 
 
