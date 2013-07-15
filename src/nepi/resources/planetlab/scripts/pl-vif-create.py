#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

import base64
import errno
import vsys
import socket
from optparse import OptionParser, SUPPRESS_HELP

# TODO: GRE OPTION!! CONFIGURE THE VIF-UP IN GRE MODE!!

STOP_MSG = "STOP"

def create_socket(socket_name):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_name)
    return sock

def recv_msg(conn):
    msg = []
    chunk = ''

    while '\n' not in chunk:
        try:
            chunk = conn.recv(1024)
        except (OSError, socket.error), e:
            if e[0] != errno.EINTR:
                raise
            # Ignore eintr errors
            continue

        if chunk:
            msg.append(chunk)
        else:
            # empty chunk = EOF
            break

    msg = ''.join(msg).split('\n')[0]
    decoded = base64.b64decode(msg)
    return decoded.rstrip()

def send_reply(conn, reply):
    encoded = base64.b64encode(reply)
    conn.send("%s\n" % encoded)

def stop_action():
    return "STOP-ACK"

def reply_action(msg):
    return "Reply to: %s" % msg

def get_options():
    usage = ("usage: %prog -t <vif-type> -a <ip4-address> -n <net-prefix> "
        "-s <snat> -p <pointopoint> -f <if-name-file> -S <socket-name>")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-t", "--vif-type", dest="vif_type",
        help = "Virtual interface type. Either IFF_TAP or IFF_TUN. "
            "Defaults to IFF_TAP. ", type="str")

    parser.add_option("-a", "--ip4-address", dest="ip4_address",
        help = "IPv4 address to assign to interface. It must belong to the "
            "network segment owned by the slice, given by the vsys_vnet tag. ",
        type="str")

    parser.add_option("-n", "--net-prefix", dest="net_prefix",
        help = "IPv4 network prefix for the interface. It must be the one "
            "given by the slice's vsys_vnet tag. ",
        type="int")

    parser.add_option("-s", "--snat", dest="snat", default = False,
        action="store_true", help="Enable SNAT for the interface")

    parser.add_option("-p", "--pointopoint", dest="pointopoint",
        help = "Peer end point for the interface  ", default = None,
        type="str")

    parser.add_option("-f", "--if-name-file", dest="if_name_file",
        help = "File to store the interface name assigned by the OS", 
        default = "if_name", type="str")

    parser.add_option("-S", "--socket-name", dest="socket_name",
        help = "Name for the unix socket used to interact with this process", 
        default = "tap.sock", type="str")

    (options, args) = parser.parse_args()
    
    vif_type = vsys.IFF_TAP
    if options.vif_type and options.vif_type == "IFF_TUN":
        vif_type = vsys.IFF_TUN

    return (vif_type, options.ip4_address, options.net_prefix, options.snat,
            options.pointopoint, options.if_name_file, options.socket_name)

if __name__ == '__main__':

    (vif_type, ip4_address, net_prefix, snat, pointopoint,
            if_name_file, socket_name) = get_options()

    (fd, if_name) = vsys.fd_tuntap(vif_type)
    vsys.vif_up(if_name, ip4_address, net_prefix, snat, pointopoint)
    
    # Saving interface name to 'if_name_file
    f = open(if_name_file, 'w')
    f.write(if_name)
    f.close()

    # create unix socket to receive instructions
    sock = create_socket(socket_name)
    sock.listen(0)

    # wait for messages to arrive and process them
    stop = False

    while not stop:
        conn, addr = sock.accept()
        conn.settimeout(5)

        while not stop:
            try:
                msg = recv_msg(conn)
            except socket.timeout, e:
                # Ingore time-out
                continue

            if not msg:
                # Ignore - connection lost
                break

            if msg == STOP_MSG:
                stop = True
                reply = stop_action()
            else:
                reply = reply_action(msg)

            try:
                send_reply(conn, reply)
            except socket.error:
                break

