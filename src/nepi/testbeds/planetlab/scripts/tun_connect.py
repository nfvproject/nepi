import sys

import socket
import fcntl
import os
import os.path
import select
import signal

import struct
import ctypes
import optparse
import threading
import subprocess
import re
import functools
import time
import base64
import traceback

import tunchannel

try:
    import iovec
    HAS_IOVEC = True
except:
    HAS_IOVEC = False

tun_name = 'tun0'
tun_path = '/dev/net/tun'
hostaddr = socket.gethostbyname(socket.gethostname())

usage = "usage: %prog [options]"

parser = optparse.OptionParser(usage=usage)

parser.add_option(
    "-i", "--iface", dest="tun_name", metavar="DEVICE",
    default = "tun0",
    help = "TUN/TAP interface to tap into")
parser.add_option(
    "-d", "--tun-path", dest="tun_path", metavar="PATH",
    default = "/dev/net/tun",
    help = "TUN/TAP device file path or file descriptor number")
parser.add_option(
    "-p", "--peer-port", dest="peer_port", metavar="PEER_PORT", type="int",
    default = 15000,
    help = "Remote TCP/UDP port to connect to.")
parser.add_option(
    "--pass-fd", dest="pass_fd", metavar="UNIX_SOCKET",
    default = None,
    help = "Path to a unix-domain socket to pass the TUN file descriptor to. "
           "If given, all other connectivity options are ignored, tun_connect will "
           "simply wait to be killed after passing the file descriptor, and it will be "
           "the receiver's responsability to handle the tunneling.")
parser.add_option(
    "-m", "--mode", dest="mode", metavar="MODE",
    default = "none",
    help = 
        "Set mode. One of none, tun, tap, pl-tun, pl-tap, pl-gre-ip, pl-gre-eth. In any mode except none, a TUN/TAP will be created "
        "by using the proper interface (tunctl for tun/tap, /vsys/fd_tuntap.control for pl-tun/pl-tap), "
        "and it will be brought up (with ifconfig for tun/tap, with /vsys/vif_up for pl-tun/pl-tap). You have "
        "to specify an VIF_ADDRESS and VIF_MASK in any case (except for none).")
parser.add_option(
    "-t", "--protocol", dest="protocol", metavar="PROTOCOL",
    default = None,
    help = 
        "Set protocol. One of tcp, udp, fd, gre. In any mode except none, a TUN/TAP will be created.")
parser.add_option(
    "-A", "--vif-address", dest="vif_addr", metavar="VIF_ADDRESS",
    default = None,
    help = 
        "See mode. This specifies the VIF_ADDRESS, "
        "the IP address of the virtual interface.")
parser.add_option(
    "-M", "--vif-mask", dest="vif_mask", type="int", metavar="VIF_MASK", 
    default = None,
    help = 
        "See mode. This specifies the VIF_MASK, "
        "a number indicating the network type (ie: 24 for a C-class network).")
parser.add_option(
    "-P", "--port", dest="port", type="int", metavar="PORT", 
    default = None,
    help = 
        "This specifies the LOCAL_PORT. This will be the local bind port for UDP/TCP.")
parser.add_option(
    "-S", "--vif-snat", dest="vif_snat", 
    action = "store_true",
    default = False,
    help = "See mode. This specifies whether SNAT will be enabled for the virtual interface. " )
parser.add_option(
    "-Z", "--vif-pointopoint", dest="vif_pointopoint",  metavar="DST_ADDR",
    default = None,
    help = 
        "See mode. This specifies the remote endpoint's virtual address, "
        "for point-to-point routing configuration. "
        "Not supported by PlanetLab" )
parser.add_option(
    "-Q", "--vif-txqueuelen", dest="vif_txqueuelen", metavar="SIZE", type="int",
    default = None,
    help = 
        "See mode. This specifies the interface's transmission queue length. " )
parser.add_option(
    "-b", "--bwlimit", dest="bwlimit", metavar="BYTESPERSECOND", type="int",
    default = None,
    help = 
        "This specifies the interface's emulated bandwidth in bytes per second." )
parser.add_option(
    "-a", "--peer-address", dest="peer_addr", metavar="PEER_ADDRESS",
    default = None,
    help = 
        "This specifies the PEER_ADDRESS, "
        "the IP address of the remote interface.")
parser.add_option(
    "-k", "--key", dest="cipher_key", metavar="KEY",
    default = None,
    help = 
        "Specify a symmetric encryption key with which to protect packets across "
        "the tunnel. python-crypto must be installed on the system." )
parser.add_option(
    "-K", "--gre-key", dest="gre_key", metavar="KEY", type="string",
    default = "true",
    help = 
        "Specify a demultiplexing 32-bit numeric key for GRE." )
parser.add_option(
    "-C", "--cipher", dest="cipher", metavar="CIPHER",
    default = 'AES',
    help = "One of PLAIN, AES, Blowfish, DES, DES3. " )
parser.add_option(
    "-N", "--no-capture", dest="no_capture", 
    action = "store_true",
    default = False,
    help = "If specified, packets won't be logged to standard output "
           "(default is to log them to standard output). " )
parser.add_option(
    "-c", "--pcap-capture", dest="pcap_capture", metavar="FILE",
    default = None,
    help = "If specified, packets won't be logged to standard output, "
           "but dumped to a pcap-formatted trace in the specified file. " )
parser.add_option(
    "--multicast-forwarder", dest="multicast_fwd", 
    default = None,
    help = "If specified, multicast packets will be forwarded to "
           "the specified unix-domain socket. If the device uses ethernet "
           "frames, ethernet headers will be stripped and IP packets "
           "will be forwarded, prefixed with the interface's address." )
parser.add_option(
    "--filter", dest="filter_module", metavar="PATH",
    default = None,
    help = "If specified, it should be either a .py or .so module. "
           "It will be loaded, and all incoming and outgoing packets "
           "will be routed through it. The filter will not be responsible "
           "for buffering, packet queueing is performed in tun_connect "
           "already, so it should not concern itself with it. It should "
           "not, however, block in one direction if the other is congested.\n"
           "\n"
           "Modules are expected to have the following methods:\n"
           "\tinit(**args)\n"
           "\t\tIf arguments are given, this method will be called with the\n"
           "\t\tgiven arguments (as keyword args in python modules, or a single\n"
           "\t\tstring in c modules).\n"
           "\taccept_packet(packet, direction):\n"
           "\t\tDecide whether to drop the packet. Direction is 0 for packets "
               "coming from the local side to the remote, and 1 is for packets "
               "coming from the remote side to the local. Return a boolean, "
               "true if the packet is not to be dropped.\n"
           "\tfilter_init():\n"
           "\t\tInitializes a filtering pipe (filter_run). It should "
               "return two file descriptors to use as a bidirectional "
               "pipe: local and remote. 'local' is where packets from the "
               "local side will be written to. After filtering, those packets "
               "should be written to 'remote', where tun_connect will read "
               "from, and it will forward them to the remote peer. "
               "Packets from the remote peer will be written to 'remote', "
               "where the filter is expected to read from, and eventually "
               "forward them to the local side. If the file descriptors are "
               "not nonblocking, they will be set to nonblocking. So it's "
               "better to set them from the start like that.\n"
           "\tfilter_run(local, remote):\n"
           "\t\tIf filter_init is provided, it will be called repeatedly, "
               "in a separate thread until the process is killed. It should "
               "sleep at most for a second.\n"
           "\tfilter_close(local, remote):\n"
           "\t\tCalled then the process is killed, if filter_init was provided. "
               "It should, among other things, close the file descriptors.\n"
           "\n"
           "Python modules are expected to return a tuple in filter_init, "
           "either of file descriptors or file objects, while native ones "
           "will receive two int*.\n"
           "\n"
           "Python modules can additionally contain a custom queue class "
           "that will replace the FIFO used by default. The class should "
           "be named 'queueclass' and contain an interface compatible with "
           "collections.deque. That is, indexing (especiall for q[0]), "
           "bool(q), popleft, appendleft, pop (right), append (right), "
           "len(q) and clear. When using a custom queue, queue size will "
           "have no effect, pass an effective queue size to the module "
           "by using filter_args" )
parser.add_option(
    "--filter-args", dest="filter_args", metavar="FILE",
    default = None,
    help = "If specified, packets won't be logged to standard output, "
           "but dumped to a pcap-formatted trace in the specified file. " )

(options,args) = parser.parse_args(sys.argv[1:])

options.cipher = {
    'aes' : 'AES',
    'des' : 'DES',
    'des3' : 'DES3',
    'blowfish' : 'Blowfish',
    'plain' : None,
}[options.cipher.lower()]

ETH_P_ALL = 0x00000003
ETH_P_IP = 0x00000800
TUNSETIFF = 0x400454ca
IFF_NO_PI = 0x00001000
IFF_TAP = 0x00000002
IFF_TUN = 0x00000001
IFF_VNET_HDR = 0x00004000
TUN_PKT_STRIP = 0x00000001
IFHWADDRLEN = 0x00000006
IFNAMSIZ = 0x00000010
IFREQ_SZ = 0x00000028
FIONREAD = 0x0000541b

class HostLock(object):
    # This class is used as a lock to prevent concurrency issues with more
    # than one instance of netns running in the same machine. Both in 
    # different processes or different threads.
    taken = False
    processcond = threading.Condition()
    
    def __init__(self, lockfile):
        processcond = self.__class__.processcond
        
        processcond.acquire()
        try:
            # It's not reentrant
            while self.__class__.taken:
                processcond.wait()
            self.__class__.taken = True
        finally:
            processcond.release()
        
        self.lockfile = lockfile
        
        while True:
            try:
                fcntl.flock(self.lockfile, fcntl.LOCK_EX)
                break
            except (OSError, IOError), e:
                if e.args[0] != os.errno.EINTR:
                    raise
    
    def __del__(self):
        processcond = self.__class__.processcond
        
        processcond.acquire()
        try:
            if not self.lockfile.closed:
                fcntl.flock(self.lockfile, fcntl.LOCK_UN)
            
            # It's not reentrant
            self.__class__.taken = False
            processcond.notify()
        finally:
            processcond.release()

def ifnam(x):
    return x+'\x00'*(IFNAMSIZ-len(x))

def ifreq(iface, flags):
    # ifreq contains:
    #   char[IFNAMSIZ] : interface name
    #   short : flags
    #   <padding>
    ifreq = ifnam(iface)+struct.pack("H",flags);
    ifreq += '\x00' * (len(ifreq)-IFREQ_SZ)
    return ifreq

def tunopen(tun_path, tun_name):
    if tun_path.isdigit():
        # open TUN fd
        print >>sys.stderr, "Using tun:", tun_name, "fd", tun_path
        tun = os.fdopen(int(tun_path), 'r+b', 0)
    else:
        # open TUN path
        print >>sys.stderr, "Using tun:", tun_name, "at", tun_path
        tun = open(tun_path, 'r+b', 0)

        # bind file descriptor to the interface
        fcntl.ioctl(tun.fileno(), TUNSETIFF, ifreq(tun_name, IFF_NO_PI|IFF_TUN))
    
    return tun

def tunclose(tun_path, tun_name, tun):
    if tun_path and tun_path.isdigit():
        # close TUN fd
        os.close(int(tun_path))
        tun.close()
    elif tun:
        # close TUN object
        tun.close()

def noopen(tun_path, tun_name):
    print >>sys.stderr, "Using tun:", tun_name
    return None
def noclose(tun_path, tun_name, tun):
    pass

def tuntap_alloc(kind, tun_path, tun_name):
    args = ["tunctl"]
    if kind == "tun":
        args.append("-n")
    if tun_name:
        args.append("-t")
        args.append(tun_name)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out,err = proc.communicate()
    if proc.wait():
        raise RuntimeError, "Could not allocate %s device" % (kind,)
        
    match = re.search(r"Set '(?P<dev>(?:tun|tap)[0-9]*)' persistent and owned by .*", out, re.I)
    if not match:
        raise RuntimeError, "Could not allocate %s device - tunctl said: %s" % (kind, out)
    
    tun_name = match.group("dev")
    print >>sys.stderr, "Allocated %s device: %s" % (kind, tun_name)
    
    return tun_path, tun_name

def tuntap_dealloc(tun_path, tun_name):
    args = ["tunctl", "-d", tun_name]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out,err = proc.communicate()
    if proc.wait():
        print >> sys.stderr, "WARNING: error deallocating %s device" % (tun_name,)

def nmask_to_dot_notation(mask):
    mask = hex(((1 << mask) - 1) << (32 - mask)) # 24 -> 0xFFFFFF00
    mask = mask[2:] # strip 0x
    mask = mask.decode("hex") # to bytes
    mask = '.'.join(map(str,map(ord,mask))) # to 255.255.255.0
    return mask

def vif_start(tun_path, tun_name):
    args = ["ifconfig", tun_name, options.vif_addr, 
            "netmask", nmask_to_dot_notation(options.vif_mask),
            "-arp" ]
    if options.vif_pointopoint:
        args.extend(["pointopoint",options.vif_pointopoint])
    if options.vif_txqueuelen is not None:
        args.extend(["txqueuelen",str(options.vif_txqueuelen)])
    args.append("up")
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out,err = proc.communicate()
    if proc.wait():
        raise RuntimeError, "Error starting virtual interface"
    
    if options.vif_snat:
        # set up SNAT using iptables
        # TODO: stop vif on error. 
        #   Not so necessary since deallocating the tun/tap device
        #   will forcibly stop it, but it would be tidier
        args = [ "iptables", "-t", "nat", "-A", "POSTROUTING", 
                 "-s", "%s/%d" % (options.vif_addr, options.vif_mask),
                 "-j", "SNAT",
                 "--to-source", hostaddr, "--random" ]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        out,err = proc.communicate()
        if proc.wait():
            raise RuntimeError, "Error setting up SNAT"

def vif_stop(tun_path, tun_name):
    if options.vif_snat:
        # set up SNAT using iptables
        args = [ "iptables", "-t", "nat", "-D", "POSTROUTING", 
                 "-s", "%s/%d" % (options.vif_addr, options.vif_mask),
                 "-j", "SNAT",
                 "--to-source", hostaddr, "--random" ]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        out,err = proc.communicate()
    
    args = ["ifconfig", tun_name, "down"]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out,err = proc.communicate()
    if proc.wait():
        print >>sys.stderr, "WARNING: error stopping virtual interface"
    
    
def pl_tuntap_alloc(kind, tun_path, tun_name):
    tunalloc_so = ctypes.cdll.LoadLibrary("./tunalloc.so")
    c_tun_name = ctypes.c_char_p("\x00"*IFNAMSIZ) # the string will be mutated!
    kind = {"tun":IFF_TUN,
            "tap":IFF_TAP}[kind]
    fd = tunalloc_so.tun_alloc(kind, c_tun_name)
    name = c_tun_name.value
    return str(fd), name

_name_reservation = None
def pl_tuntap_namealloc(kind, tun_path, tun_name):
    global _name_reservation
    # Serialize access
    lockfile = open("/tmp/nepi-tun-connect.lock", "a")
    lock = HostLock(lockfile)
    
    # We need to do this, fd_tuntap is the only one who can
    # tell us our slice id (this script runs as root, so no uid),
    # and the pattern of device names accepted by vsys scripts
    tunalloc_so = ctypes.cdll.LoadLibrary("./tunalloc.so")
    c_tun_name = ctypes.c_char_p("\x00"*IFNAMSIZ) # the string will be mutated!
    nkind= {"tun":IFF_TUN,
            "tap":IFF_TAP}[kind]
    fd = tunalloc_so.tun_alloc(nkind, c_tun_name)
    name = c_tun_name.value
    os.close(fd)

    base = name[:name.index('-')+1]
    existing = set(map(str.strip,os.popen("ip a | grep -o '%s[0-9]*'" % (base,)).read().strip().split('\n')))
    
    for i in xrange(9000,10000):
        name = base + str(i)
        if name not in existing:
            break
    else:
        raise RuntimeError, "Could not assign interface name"
    
    _name_reservation = lock
    
    return None, name

def pl_vif_start(tun_path, tun_name):
    global _name_reservation

    out = []
    def outreader():
        out.append(stdout.read())
        stdout.close()
        time.sleep(1)

    # Serialize access to vsys
    lockfile = open("/tmp/nepi-tun-connect.lock", "a")
    lock = _name_reservation or HostLock(lockfile)
    _name_reservation = None
    
    stdin = open("/vsys/vif_up.in","w")
    stdout = open("/vsys/vif_up.out","r")

    t = threading.Thread(target=outreader)
    t.start()
    
    stdin.write(tun_name+"\n")
    stdin.write(options.vif_addr+"\n")
    stdin.write(str(options.vif_mask)+"\n")
    if options.vif_snat:
        stdin.write("snat=1\n")
    if options.vif_pointopoint:
        stdin.write("pointopoint=%s\n" % (options.vif_pointopoint,))
    if options.vif_txqueuelen is not None:
        stdin.write("txqueuelen=%d\n" % (options.vif_txqueuelen,))
    if options.mode.startswith('pl-gre'):
        stdin.write("gre=%s\n" % (options.gre_key,))
        stdin.write("remote=%s\n" % (options.peer_addr,))
    stdin.close()
    
    t.join()
    out = ''.join(out)
    if out.strip():
        print >>sys.stderr, out
    
    del lock, lockfile

def pl_vif_stop(tun_path, tun_name):
    out = []
    def outreader():
        out.append(stdout.read())
        stdout.close()
        
        if options.mode.startswith('pl-gre'):
            lim = 120
        else:
            lim = 2
        
        for i in xrange(lim):
            ifaces = set(map(str.strip,os.popen("ip a | grep -o '%s'" % (tun_name,)).read().strip().split('\n')))
            if tun_name in ifaces:
                time.sleep(1)
            else:
                break

    # Serialize access to vsys
    lockfile = open("/tmp/nepi-tun-connect.lock", "a")
    lock = HostLock(lockfile)

    stdin = open("/vsys/vif_down.in","w")
    stdout = open("/vsys/vif_down.out","r")
    
    t = threading.Thread(target=outreader)
    t.start()
    
    stdin.write(tun_name+"\n")
    stdin.close()
    
    t.join()
    out = ''.join(out)
    if out.strip():
        print >>sys.stderr, out
    
    del lock, lockfile


def tun_fwd(tun, remote, reconnect = None, accept_local = None, accept_remote = None, slowlocal = True, bwlimit = None):
    global TERMINATE
    
    tunqueue = options.vif_txqueuelen or 1000
    tunkqueue = 500
    
    # in PL mode, we cannot strip PI structs
    # so we'll have to handle them
    tunchannel.tun_fwd(tun, remote,
        with_pi = options.mode.startswith('pl-'),
        ether_mode = tun_name.startswith('tap'),
        cipher_key = options.cipher_key,
        udp = options.protocol == 'udp',
        TERMINATE = TERMINATE,
        stderr = None,
        reconnect = reconnect,
        tunqueue = tunqueue,
        tunkqueue = tunkqueue,
        cipher = options.cipher,
        accept_local = accept_local,
        accept_remote = accept_remote,
        queueclass = queueclass,
        slowlocal = slowlocal,
        bwlimit = bwlimit
    )



nop = lambda tun_path, tun_name : (tun_path, tun_name)
MODEINFO = {
    'none' : dict(alloc=nop,
                  tunopen=tunopen, tunclose=tunclose,
                  dealloc=nop,
                  start=nop,
                  stop=nop),
    'tun'  : dict(alloc=functools.partial(tuntap_alloc, "tun"),
                  tunopen=tunopen, tunclose=tunclose,
                  dealloc=tuntap_dealloc,
                  start=vif_start,
                  stop=vif_stop),
    'tap'  : dict(alloc=functools.partial(tuntap_alloc, "tap"),
                  tunopen=tunopen, tunclose=tunclose,
                  dealloc=tuntap_dealloc,
                  start=vif_start,
                  stop=vif_stop),
    'pl-tun'  : dict(alloc=functools.partial(pl_tuntap_alloc, "tun"),
                  tunopen=tunopen, tunclose=tunclose,
                  dealloc=nop,
                  start=pl_vif_start,
                  stop=pl_vif_stop),
    'pl-tap'  : dict(alloc=functools.partial(pl_tuntap_alloc, "tap"),
                  tunopen=tunopen, tunclose=tunclose,
                  dealloc=nop,
                  start=pl_vif_start,
                  stop=pl_vif_stop),
    'pl-gre-ip' : dict(alloc=functools.partial(pl_tuntap_namealloc, "tun"),
                  tunopen=noopen, tunclose=tunclose,
                  dealloc=nop,
                  start=pl_vif_start,
                  stop=pl_vif_stop),
    'pl-gre-eth': dict(alloc=functools.partial(pl_tuntap_namealloc, "tap"),
                  tunopen=noopen, tunclose=noclose,
                  dealloc=nop,
                  start=pl_vif_start,
                  stop=pl_vif_stop),
}
    
tun_path = options.tun_path
tun_name = options.tun_name

modeinfo = MODEINFO[options.mode]

# Try to load filter module
filter_thread = None
if options.filter_module:
    print >>sys.stderr, "Loading module", options.filter_module, "with args", options.filter_args
    if options.filter_module.endswith('.py'):
        sys.path.append(os.path.dirname(options.filter_module))
        filter_module = __import__(os.path.basename(options.filter_module).rsplit('.',1)[0])
        if options.filter_args:
            try:
                filter_args = dict(map(lambda x:x.split('=',1),options.filter_args.split(',')))
                filter_module.init(**filter_args)
            except:
                traceback.print_exc()
    elif options.filter_module.endswith('.so'):
        filter_module = ctypes.cdll.LoadLibrary(options.filter_module)
        if options.filter_args:
            try:
                filter_module.init(options.filter_args)
            except:
                traceback.print_exc()
    try:
        accept_packet = filter_module.accept_packet
        print >>sys.stderr, "Installing packet filter (accept_packet)"
    except:
        accept_packet = None
    
    try:
        queueclass = filter_module.queueclass
        print >>sys.stderr, "Installing custom queue"
    except:
        queueclass = None
    
    try:
        _filter_init = filter_module.filter_init
        filter_run = filter_module.filter_run
        filter_close = filter_module.filter_close
        
        def filter_init():
            filter_local = ctypes.c_int(0)
            filter_remote = ctypes.c_int(0)
            _filter_init(filter_local, filter_remote)
            return filter_local, filter_remote

        print >>sys.stderr, "Installing packet filter (stream filter)"
    except:
        filter_init = None
        filter_run = None
        filter_close = None
else:
    accept_packet = None
    filter_init = None
    filter_run = None
    filter_close = None
    queueclass = None

# install multicast forwarding hook
if options.multicast_fwd:
    print >>sys.stderr, "Connecting to mcast filter"
    mcfwd_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    tunchannel.nonblock(mcfwd_sock.fileno())

# be careful to roll back stuff on exceptions
tun_path, tun_name = modeinfo['alloc'](tun_path, tun_name)
try:
    modeinfo['start'](tun_path, tun_name)
    try:
        tun = modeinfo['tunopen'](tun_path, tun_name)
    except:
        modeinfo['stop'](tun_path, tun_name)
        raise
except:
    modeinfo['dealloc'](tun_path, tun_name)
    raise


# Trak SIGTERM, and set global termination flag instead of dying
TERMINATE = []
def _finalize(sig,frame):
    global TERMINATE
    TERMINATE.append(None)
signal.signal(signal.SIGTERM, _finalize)

try:
    tcpdump = None
    reconnect = None
    mcastthread = None

    # install multicast forwarding hook
    if options.multicast_fwd:
        print >>sys.stderr, "Installing mcast filter"
        
        if HAS_IOVEC:
            writev = iovec.writev
        else:
            os_write = os.write
            map_ = map
            str_ = str
            def writev(fileno, *stuff):
                os_write(''.join(map_(str_,stuff)))
        
        def accept_packet(packet, direction, 
                _up_accept=accept_packet, 
                sock=mcfwd_sock, 
                sockno=mcfwd_sock.fileno(),
                etherProto=tunchannel.etherProto,
                etherStrip=tunchannel.etherStrip,
                etherMode=tun_name.startswith('tap'),
                multicast_fwd = options.multicast_fwd,
                vif_addr = socket.inet_aton(options.vif_addr),
                connected = [], writev=writev,
                len=len, ord=ord):
            if _up_accept:
                rv = _up_accept(packet, direction)
                if not rv:
                    return rv

            if direction == 1:
                # Incoming... what?
                if etherMode:
                    if etherProto(packet)=='\x08\x00':
                        fwd = etherStrip(packet)
                    else:
                        fwd = None
                else:
                    fwd = packet
                if fwd is not None and len(fwd) >= 20:
                    if (ord(fwd[16]) & 0xf0) == 0xe0:
                        # Forward it
                        if not connected:
                            try:
                                sock.connect(multicast_fwd)
                                connected.append(None)
                            except:
                                traceback.print_exc(file=sys.stderr)
                        if connected:
                            try:
                                writev(sockno, vif_addr,fwd)
                            except:
                                traceback.print_exc(file=sys.stderr)
            return 1

    
    if options.protocol == 'fd':
        if accept_packet or filter_init:
            raise NotImplementedError, "--pass-fd and --filter are not compatible"
        
        if options.pass_fd.startswith("base64:"):
            options.pass_fd = base64.b64decode(
                options.pass_fd[len("base64:"):])
            options.pass_fd = os.path.expandvars(options.pass_fd)
        
        print >>sys.stderr, "Sending FD to: %r" % (options.pass_fd,)
        
        # send FD to whoever wants it
        import passfd
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        retrydelay = 1.0
        for i in xrange(30):
            if TERMINATE:
                raise OSError, "Killed"
            try:
                sock.connect(options.pass_fd)
                break
            except socket.error:
                # wait a while, retry
                print >>sys.stderr, "%s: Could not connect. Retrying in a sec..." % (time.strftime('%c'),)
                time.sleep(min(30.0,retrydelay))
                retrydelay *= 1.1
        else:
            sock.connect(options.pass_fd)
        passfd.sendfd(sock, tun.fileno(), '0')
        
        # just wait forever
        def tun_fwd(tun, remote, **kw):
            global TERMINATE
            TERM = TERMINATE
            while not TERM:
                time.sleep(1)
        remote = None
    elif options.protocol == "gre":
        if accept_packet or filter_init:
            raise NotImplementedError, "--mode %s and --filter are not compatible" % (options.mode,)
        
        # just wait forever
        def tun_fwd(tun, remote, **kw):
            global TERMINATE
            TERM = TERMINATE
            while not TERM:
                time.sleep(1)
        remote = options.peer_addr
    elif options.protocol == "udp":
        # connect to remote endpoint
        if options.peer_addr and options.peer_port:
            rsock = tunchannel.udp_establish(TERMINATE, hostaddr, options.port, 
                    options.peer_addr, options.peer_port)
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        else:
            print >>sys.stderr, "Error: need a remote endpoint in UDP mode"
            raise AssertionError, "Error: need a remote endpoint in UDP mode"
    elif options.protocol == "tcp":
        # connect to remote endpoint
        if options.peer_addr and options.peer_port:
            rsock = tunchannel.tcp_establish(TERMINATE, hostaddr, options.port,
                    options.peer_addr, options.peer_port)
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        else:
            print >>sys.stderr, "Error: need a remote endpoint in TCP mode"
            raise AssertionError, "Error: need a remote endpoint in TCP mode"
    else:
        msg = "Error: Invalid protocol %s" % options.protocol
        print >>sys.stderr, msg 
        raise AssertionError, msg

    if filter_init:
        filter_local, filter_remote = filter_init()
        
        def filter_loop():
            global TERMINATE
            TERM = TERMINATE
            run = filter_run
            local = filter_local
            remote = filter_remote
            while not TERM:
                run(local, remote)
            filter_close(local, remote)
            
        filter_thread = threading.Thread(target=filter_loop)
        filter_thread.start()
    
    print >>sys.stderr, "Connected"

    if not options.no_capture:
        # Launch a tcpdump subprocess, to capture and dump packets.
        # Make sure to catch sigterm and kill the tcpdump as well
        tcpdump = subprocess.Popen(
            ["tcpdump","-l","-n","-i",tun_name, "-s", "4096"]
            + ["-w",options.pcap_capture,"-U"] * bool(options.pcap_capture) )
    
    # Try to give us high priority
    try:
        os.nice(-20)
    except:
        # Ignore errors, we might not have enough privileges,
        # or perhaps there is no os.nice support in the system
        pass
    
    if not filter_init:
        tun_fwd(tun, remote,
            reconnect = reconnect,
            accept_local = accept_packet,
            accept_remote = accept_packet,
            bwlimit = options.bwlimit,
            slowlocal = True)
    else:
        # Hm...
        # ...ok, we need to:
        #  1. Forward packets from tun to filter
        #  2. Forward packets from remote to filter
        #
        # 1. needs TUN rate-limiting, while 
        # 2. needs reconnection
        #
        # 1. needs ONLY TUN-side acceptance checks, while
        # 2. needs ONLY remote-side acceptance checks
        if isinstance(filter_local, ctypes.c_int):
            filter_local_fd = filter_local.value
        else:
            filter_local_fd = filter_local
        if isinstance(filter_remote, ctypes.c_int):
            filter_remote_fd = filter_remote.value
        else:
            filter_remote_fd = filter_remote

        def localside():
            tun_fwd(tun, filter_local_fd,
                accept_local = accept_packet,
                slowlocal = True)
        
        def remoteside():
            tun_fwd(filter_remote_fd, remote,
                reconnect = reconnect,
                accept_remote = accept_packet,
                bwlimit = options.bwlimit,
                slowlocal = False)
        
        localthread = threading.Thread(target=localside)
        remotethread = threading.Thread(target=remoteside)
        localthread.start()
        remotethread.start()
        localthread.join()
        remotethread.join()

finally:
    try:
        print >>sys.stderr, "Shutting down..."
    except:
        # In case sys.stderr is broken
        pass
    
    # tidy shutdown in every case - swallow exceptions
    TERMINATE.append(None)
    
    if mcastthread:
        try:
            mcastthread.stop()
        except:
            pass
    
    if filter_thread:
        try:
            filter_thread.join()
        except:
            pass

    try:
        if tcpdump:
            os.kill(tcpdump.pid, signal.SIGTERM)
            tcpdump.wait()
    except:
        pass

    try:
        modeinfo['stop'](tun_path, tun_name)
    except:
        traceback.print_exc()

    try:
        modeinfo['tunclose'](tun_path, tun_name, tun)
    except:
        traceback.print_exc()
        
    try:
        modeinfo['dealloc'](tun_path, tun_name)
    except:
        traceback.print_exc()
    
    print >>sys.stderr, "TERMINATED GRACEFULLY"

