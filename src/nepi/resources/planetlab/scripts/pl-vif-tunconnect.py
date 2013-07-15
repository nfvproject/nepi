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
import passfd
import vsys
import socket
from optparse import OptionParser, SUPPRESS_HELP

PASSFD_MSG = "PASSFD"

def get_options():
    usage = ("usage: %prog -S <socket-name>")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-S", "--socket-name", dest="socket_name",
        help = "Name for the unix socket used to interact with this process", 
        default = "tap.sock", type="str")

    (options, args) = parser.parse_args()
    
    return (options.socket_name)

if __name__ == '__main__':

    (socket_name) = get_options()

    # Socket to recive the file descriptor
    fdsock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    fdsock.bind("")
    address = fdsock.getsockname()

    # vif-create-socket to send the PASSFD message
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

    print reply, fd




