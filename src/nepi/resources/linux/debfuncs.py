"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

# TODO: Investigate using http://nixos.org/nix/

def install_packages_command(os, packages):
    if not isinstance(packages, list):
        packages = [packages]

    cmd = ""
    for p in packages:
        cmd += " ( dpkg -s %(package)s || sudo -S apt-get -y install %(package)s ) ; " % {
                'package': p}
   
    #cmd = (dpkg -s vim || sudo dpkg -s install vim) ; (...)
    return cmd 

def remove_packages_command(os, packages):
    if not isinstance(packages, list):
        packages = [packages]

    cmd = ""
    for p in packages:
        cmd += " ( dpkg -s %(package)s && sudo -S apt-get -y purge %(package)s ) ; " % {
                'package': p}
    
    #cmd = (dpkg -s vim || sudo apt-get -y purge vim) ; (...)
    return cmd 

