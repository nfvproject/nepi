import base64
import errno
import os
import passfd
import signal
import socket
import time
import tunchannel
import vsys

from optparse import OptionParser, SUPPRESS_HELP

PASSFD_MSG = "PASSFD"

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

def get_fd(socket_name):
    # Socket to recive the file descriptor
    fdsock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    fdsock.bind("")
    address = fdsock.getsockname()

    # Socket to connect to the pl-vif-create process 
    # and send the PASSFD message
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_name)
    emsg = base64.b64encode(PASSFD_MSG)
    eargs = base64.b64encode(address)
    encoded = "%s|%s\n" % (emsg, eargs)
    sock.send(encoded)

    # Receive fd
    (fd, msg) = passfd.recvfd(fdsock)
    
    # Receive reply
    reply = sock.recv(1024)
    reply = base64.b64decode(reply)

    sock.close()
    fdsock.close()
    return fd

def get_options():
    usage = ("usage: %prog -t <vif-type> -S <fd-socket-name> "
            "-b <bwlimit> -c <cipher> -k <cipher-key> -q <txqueuelen> " 
            "-l <local-port-file> -r <remote-port-file> -H <remote-host> "
            "-R <ret-file> ")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-t", "--vif-type", dest="vif_type",
        help = "Virtual interface type. Either IFF_TAP or IFF_TUN. "
            "Defaults to IFF_TAP. ", type="str")
    parser.add_option("-S", "--fd-socket-name", dest="fd_socket_name",
        help = "Name for the unix socket to request the TAP file descriptor", 
        default = "tap.sock", type="str")

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
       
    vif_type = vsys.IFF_TAP
    if options.vif_type and options.vif_type == "IFF_TUN":
        vif_type = vsys.IFF_TUN

    return ( vif_type, options.fd_socket_name, options.local_port_file,
            options.remote_port_file, options.remote_host, options.ret_file, 
            options.bwlimit, options.cipher, options.cipher_key,
            options.txqueuelen )

if __name__ == '__main__':

    ( vif_type, socket_name, local_port_file, remote_port_file,
      remote_host, ret_file, bwlimit, cipher, cipher_key, txqueuelen 
         ) = get_options()
   
    # Get the file descriptor of the TAP device from the process
    # that created it
    fd = get_fd(socket_name)
    tun = os.fdopen(int(fd), 'r+b', 0)

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
    #       Maybe a raise condition?
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
        ether_mode = (vif_type == vsys.IFF_TAP),
        udp = True,
        cipher_key = cipher_key,
        cipher = cipher,
        TERMINATE = TERMINATE,
        SUSPEND = SUSPEND,
        tunqueue = txqueuelen,
        tunkqueue = 500,
        bwlimit = bwlimit
    ) 
 

