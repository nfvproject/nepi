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
from optparse import OptionParser, SUPPRESS_HELP

def get_options():
    usage = ("usage: %prog -a <action> -n <ip4-network> -p <ip4-prefix> "
        "-g <gateway> -f <if-name-file>")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-a", "--action", dest="action",
        help = "Either add or del ", type="str")

    parser.add_option("-n", "--ip4-network-address", dest="ip4_network",
        help = "IPv4 address of the network ", type="str")

    parser.add_option("-p", "--ip4-prefix", dest="ip4_prefix",
        help = "IPv4 network prefix for the interface. It must be the one "
            "given by the slice's vsys_vnet tag. ",
        type="int")

    parser.add_option("-g", "--ip4-gateway", dest="ip4_gateway",
        help="IPv4 address of the gateway")

    parser.add_option("-f", "--if-name", dest="if_name",
        help = "Interface name assigned by the OS", type="str")

    (options, args) = parser.parse_args()

    return (options.action, options.ip4_network, options.ip4_prefix,
            options.ip4_gateway, options.if_name)

if __name__ == '__main__':

    (action, ip4_network, ip4_prefix, ip4_gateway, if_name) = get_options()
    vsys.vroute(action, ip4_network, ip4_prefix, ip4_gateway, if_name)
    
  
