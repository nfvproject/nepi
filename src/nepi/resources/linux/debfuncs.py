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

