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
import socket
import vsys

from optparse import OptionParser

STOP_MSG = "STOP"

def get_options():
    usage = ("usage: %prog -u <slicename> -N <vif-name> -t <vif-type> "
            "-D <delete> -S <socket-name>")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-u", "--slicename", dest="slicename",
        help = "The name of the PlanetLab slice ",
        type="str")

    parser.add_option("-N", "--vif-name", dest="vif_name",
        help = "The name of the virtual interface, or a "
                "unique numeric identifier to name the interface "
                "if GRE mode is used.",
        type="str")

    parser.add_option("-t", "--vif-type", dest="vif_type",
            help = "Virtual interface type. Either IFF_TAP or IFF_TUN. "
            "Defaults to IFF_TAP. ", type="str")

    parser.add_option("-D", "--delete", dest="delete", 
            action="store_true", 
            default = False,
            help="Removes virtual interface if GRE mode was used")

    parser.add_option("-S", "--socket-name", dest="socket_name",
        help = "Name for the unix socket used to interact with this process", 
        type="str")

    (options, args) = parser.parse_args()
   
    vif_type = vsys.IFF_TAP
    if options.vif_type and options.vif_type == "IFF_TUN":
        vif_type = vsys.IFF_TUN

    return (options.socket_name, options.vif_name, options.slicename, 
            vif_type, options.delete)

if __name__ == '__main__':

    (socket_name, vif_name, slicename, vif_type, delete) = get_options()

    # If a socket name is sent, send the STOP message and wait for a reply
    if socket_name:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_name)
        encoded = base64.b64encode(STOP_MSG)
        sock.send("%s\n" % encoded)
        reply = sock.recv(1024)
        reply = base64.b64decode(reply)
        print reply

    # If a slicename is provided, use it to remove a GRE device
    elif slicename:
        import pwd
        import getpass

        sliceid = pwd.getpwnam(slicename).pw_uid

        if vif_type == vsys.IFF_TAP:
            vif_prefix = "tap"
        else:
            vif_prefix = "tun"

        # if_name should be a unique numeric vif id
        vif_name = "%s%s-%s" % (vif_prefix, sliceid, vif_name) 

        vsys.vif_down(vif_name, delete = True)

    # Else, use the vsys interface to set the virtual interface down
    else:
        vsys.vif_down(vif_name)


