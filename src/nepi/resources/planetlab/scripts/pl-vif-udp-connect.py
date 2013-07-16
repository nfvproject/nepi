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
        "-l <local-port-file> -r <remote-port-file> -H <remote-host> "
        "-R <ret-file> ")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-t", "--vif-type", dest="vif_type",
        help = "Virtual interface type. Either IFF_TAP or IFF_TUN. "
            "Defaults to IFF_TAP. ", type="str")
    parser.add_option("-S", "--fd-socket-name", dest="fd_socket_name",
        help = "Name for the unix socket to request the TAP file descriptor", 
        default = "tap.sock", type="str")
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
            options.remote_port_file, options.remote_host,
            options.ret_file )

if __name__ == '__main__':

    ( vif_type, socket_name, local_port_file, remote_port_file,
            remote_host, ret_file ) = get_options()
   
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

    # Read remote port from file
    f = open(remote_port_file, 'r')
    remote_port = f.read()
    f.close()
    
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
    # TODO: ADD parameters tunqueue, tunkqueue, cipher_key
    tunchannel.tun_fwd(tun, remote,
        # Planetlab TAP devices add PI headers 
        with_pi = True,
        ether_mode = (vif_type == vsys.IFF_TAP),
        cipher_key = None,
        udp = True,
        TERMINATE = TERMINATE,
        SUSPEND = SUSPEND,
        tunqueue = 1000,
        tunkqueue = 500,
    ) 
 

