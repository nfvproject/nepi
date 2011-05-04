import sys

import socket
import fcntl
import os
import select

import struct
import ctypes
import optparse
import threading
import subprocess
import re
import functools

tun_name = 'tun0'
tun_path = '/dev/net/tun'
hostaddr = socket.gethostbyname(socket.gethostname())

usage = "usage: %prog [options] <remote-endpoint>"

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
    "-p", "--port", dest="port", metavar="PORT", type="int",
    default = 15000,
    help = "Peering TCP port to connect or listen to.")

parser.add_option(
    "-m", "--mode", dest="mode", metavar="MODE",
    default = "none",
    help = 
        "Set mode. One of none, tun, tap, pl-tun, pl-tap. In any mode except none, a TUN/TAP will be created "
        "by using the proper interface (tunctl for tun/tap, /vsys/fd_tuntap.control for pl-tun/pl-tap), "
        "and it will be brought up (with ifconfig for tun/tap, with /vsys/vif_up for pl-tun/pl-tap). You have "
        "to specify an VIF_ADDRESS and VIF_MASK in any case (except for none).")
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
    "-S", "--vif-snat", dest="vif_snat", 
    action = "store_true",
    default = False,
    help = "See mode. This specifies whether SNAT will be enabled for the virtual interface. " )
parser.add_option(
    "-P", "--vif-pointopoint", dest="vif_pointopoint",  metavar="DST_ADDR",
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

(options, remaining_args) = parser.parse_args(sys.argv[1:])


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
    if tun_path.isdigit():
        # close TUN fd
        os.close(int(tun_path))
        tun.close()
    else:
        # close TUN object
        tun.close()

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

def pl_vif_start(tun_path, tun_name):
    stdin = open("/vsys/vif_up.in","w")
    stdout = open("/vsys/vif_up.out","r")
    stdin.write(tun_name+"\n")
    stdin.write(options.vif_addr+"\n")
    stdin.write(str(options.vif_mask)+"\n")
    if options.vif_snat:
        stdin.write("snat=1\n")
    if options.vif_txqueuelen is not None:
        stdin.write("txqueuelen=%d\n" % (options.vif_txqueuelen,))
    stdin.close()
    out = stdout.read()
    stdout.close()
    if out.strip():
        print >>sys.stderr, out


def ipfmt(ip):
    ipbytes = map(ord,ip.decode("hex"))
    return '.'.join(map(str,ipbytes))

tagtype = {
    '0806' : 'arp ',
    '0800' : 'ipv4 ',
    '8870' : 'jumbo ',
    '8863' : 'PPPoE discover ',
    '8864' : 'PPPoE ',
}
def etherProto(packet):
    packet = packet.encode("hex")
    if len(packet) > 14:
        if packet[12:14] == "\x81\x00":
            # tagged
            return packet[16:18]
        else:
            # untagged
            return packet[12:14]
    # default: ip
    return "\x08\x00"
def formatPacket(packet, ether_mode):
    if ether_mode:
        stripped_packet = etherStrip(packet)
        if not stripped_packet:
            packet = packet.encode("hex")
            if len(packet) < 28:
                return "malformed eth " + packet.encode("hex")
            else:
                if packet[24:28] == "8100":
                    # tagged
                    ethertype = tagtype.get(packet[32:36], 'eth')
                    return ethertype + " " + ( '-'.join( (
                        packet[0:12], # MAC dest
                        packet[12:24], # MAC src
                        packet[24:32], # VLAN tag
                        packet[32:36], # Ethertype/len
                        packet[36:], # Payload
                    ) ) )
                else:
                    # untagged
                    ethertype = tagtype.get(packet[24:28], 'eth')
                    return ethertype + " " + ( '-'.join( (
                        packet[0:12], # MAC dest
                        packet[12:24], # MAC src
                        packet[24:28], # Ethertype/len
                        packet[28:], # Payload
                    ) ) )
        else:
            packet = stripped_packet
    packet = packet.encode("hex")
    if len(packet) < 48:
        return "malformed ip " + packet
    else:
        return "ip " + ( '-'.join( (
            packet[0:1], #version
            packet[1:2], #header length
            packet[2:4], #diffserv/ECN
            packet[4:8], #total length
            packet[8:12], #ident
            packet[12:16], #flags/fragment offs
            packet[16:18], #ttl
            packet[18:20], #ip-proto
            packet[20:24], #checksum
            ipfmt(packet[24:32]), # src-ip
            ipfmt(packet[32:40]), # dst-ip
            packet[40:48] if (int(packet[1],16) > 5) else "", # options
            packet[48:] if (int(packet[1],16) > 5) else packet[40:], # payload
        ) ) )

def packetReady(buf, ether_mode):
    if len(buf) < 4:
        return False
    elif ether_mode:
        return True
    else:
        _,totallen = struct.unpack('HH',buf[:4])
        totallen = socket.htons(totallen)
        return len(buf) >= totallen

def pullPacket(buf, ether_mode):
    if ether_mode:
        return buf, ""
    else:
        _,totallen = struct.unpack('HH',buf[:4])
        totallen = socket.htons(totallen)
        return buf[:totallen], buf[totallen:]

def etherStrip(buf):
    if len(buf) < 14:
        return ""
    if buf[12:14] == '\x08\x10' and buf[16:18] == '\x08\x00':
        # tagged ethernet frame
        return buf[18:-4]
    elif buf[12:14] == '\x08\x00':
        # untagged ethernet frame
        return buf[14:-4]
    else:
        return ""

def etherWrap(packet):
    return (
        "\x00"*6*2 # bogus src and dst mac
        +"\x08\x00" # IPv4
        +packet # payload
        +"\x00"*4 # bogus crc
    )

def piStrip(buf):
    if len(buf) < 4:
        return buf
    else:
        return buf[4:]
    
def piWrap(buf, ether_mode):
    if ether_mode:
        proto = etherProto(buf)
    else:
        proto = "\x08\x00"
    return (
        "\x00\x00" # PI: 16 bits flags
        +proto # 16 bits proto
        +buf
    )

abortme = False
def tun_fwd(tun, remote):
    global abortme
    
    # in PL mode, we cannot strip PI structs
    # so we'll have to handle them
    with_pi = options.mode.startswith('pl-')
    ether_mode = tun_name.startswith('tap')
    
    # Limited frame parsing, to preserve packet boundaries.
    # Which is needed, since /dev/net/tun is unbuffered
    fwbuf = ""
    bkbuf = ""
    while not abortme:
        wset = []
        if packetReady(bkbuf, ether_mode):
            wset.append(tun)
        if packetReady(fwbuf, ether_mode):
            wset.append(remote)
        rdrdy, wrdy, errs = select.select((tun,remote),wset,(tun,remote),1)
        
        # check for errors
        if errs:
            break
        
        # check to see if we can write
        if remote in wrdy and packetReady(fwbuf, ether_mode):
            packet, fwbuf = pullPacket(fwbuf, ether_mode)
            os.write(remote.fileno(), packet)
            print >>sys.stderr, '>', formatPacket(packet, ether_mode)
        if tun in wrdy and packetReady(bkbuf, ether_mode):
            packet, bkbuf = pullPacket(bkbuf, ether_mode)
            formatted = formatPacket(packet, ether_mode)
            if with_pi:
                packet = piWrap(packet, ether_mode)
            os.write(tun.fileno(), packet)
            print >>sys.stderr, '<', formatted
        
        # check incoming data packets
        if tun in rdrdy:
            packet = os.read(tun.fileno(),2000) # tun.read blocks until it gets 2k!
            if with_pi:
                packet = piStrip(packet)
            fwbuf += packet
        if remote in rdrdy:
            packet = os.read(remote.fileno(),2000) # remote.read blocks until it gets 2k!
            bkbuf += packet



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
                  stop=nop),
    'pl-tap'  : dict(alloc=functools.partial(pl_tuntap_alloc, "tap"),
                  tunopen=tunopen, tunclose=tunclose,
                  dealloc=nop,
                  start=pl_vif_start,
                  stop=nop),
}
    
tun_path = options.tun_path
tun_name = options.tun_name

modeinfo = MODEINFO[options.mode]

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


try:
    # connect to remote endpoint
    if remaining_args and not remaining_args[0].startswith('-'):
        print >>sys.stderr, "Connecting to: %s:%d" % (remaining_args[0],options.port)
        rsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        rsock.connect((remaining_args[0],options.port))
    else:
        print >>sys.stderr, "Listening at: %s:%d" % (hostaddr,options.port)
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        lsock.bind((hostaddr,options.port))
        lsock.listen(1)
        rsock,raddr = lsock.accept()
    remote = os.fdopen(rsock.fileno(), 'r+b', 0)

    print >>sys.stderr, "Connected"

    tun_fwd(tun, remote)
finally:
    try:
        print >>sys.stderr, "Shutting down..."
    except:
        # In case sys.stderr is broken
        pass
    
    # tidy shutdown in every case - swallow exceptions
    try:
        modeinfo['tunclose'](tun_path, tun_name, tun)
    except:
        pass
        
    try:
        modeinfo['stop'](tun_path, tun_name)
    except:
        pass

    try:
        modeinfo['dealloc'](tun_path, tun_name)
    except:
        pass


