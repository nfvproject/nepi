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

import vsys

from optparse import OptionParser

def get_options():
    usage = ("usage: %prog -N <vif-name> -t <vif-type> -a <ip4-address> "
                    "-n <net-prefix> -s <snat> -p <pointopoint> -q <txqueuelen> "
                    "-g <gre_key> -G <gre_remote> -f <vif-name-file> ")
 
    parser = OptionParser(usage = usage)

    parser.add_option("-N", "--vif-name", dest="vif_name",
        help = "The name of the virtual interface, or a "
                "unique numeric identifier to name the interface "
                "if GRE mode is used.",
        type="str")

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

    parser.add_option("-s", "--snat", dest="snat", 
            action="store_true", 
            default = False,
            help="Enable SNAT for the interface")

    parser.add_option("-p", "--pointopoint", dest="pointopoint",
            help = "Peer end point for the interface. ", 
            default = None,
            type="str")

    parser.add_option("-q", "--txqueuelen", dest="txqueuelen",
        help = "Size of transmision queue. Defaults to 0.",
        default = 0,
        type="int")

    parser.add_option("-g", "--gre-key", dest="gre_key",
        help = "When set, enables GRE mode with the corresponding GRE key.", 
        default = None,
        type="str")

    parser.add_option("-G", "--gre-remote", dest="gre_remote",
        help = "Remote endpoint (public IP) for the GRE tunnel.", 
        default = None,
        type="str")

    parser.add_option("-f", "--vif-name-file", dest="vif_name_file",
        help = "File to store the virtual interface name assigned by the OS", 
        default = "vif_name", type="str")

    (options, args) = parser.parse_args()
    
    vif_type = vsys.IFF_TAP
    if options.vif_type and options.vif_type == "IFF_TUN":
        vif_type = vsys.IFF_TUN

    return (options.vif_name, vif_type, options.ip4_address, 
            options.net_prefix, options.snat, options.pointopoint, 
            options.txqueuelen, options.gre_key, options.gre_remote,
            options.vif_name_file)

if __name__ == '__main__':

    (vif_name, vif_type, ip4_address, net_prefix, snat, pointopoint,
        txqueuelen, gre_key, gre_remote, vif_name_file) = get_options()

    if (gre_key):
        import pwd
        import getpass

        slicename = getpass.getuser()
        sliceid = pwd.getpwnam(slicename).pw_uid

        if vif_type == vsys.IFF_TAP:
            vif_prefix = "tap"
        else:
            vif_prefix = "tun"

        # if_name should be a unique numeric vif id
        vif_name = "%s%s-%d" % (vif_prefix, sliceid, vif_name) 

    vsys.vif_up(vif_name, ip4_address, net_prefix, snat = snat, 
            pointopoint = pointopoint, txqueuelen = txqueuelen, 
            gre_key = gre_key, gre_remote = gre_remote)

    # Saving interface name to vif_name_file
    f = open(vif_name_file, 'w')
    f.write(vif_name)
    f.close()


