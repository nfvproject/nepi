RPM_FUSION_URL = 'http://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-stable.noarch.rpm'
RPM_FUSION_URL_F12 = 'http://download1.rpmfusion.org/free/fedora/releases/12/Everything/x86_64/os/rpmfusion-free-release-12-1.noarch.rpm'

# TODO: Investigate using http://nixos.org/nix/

def install_packages_command(os, packages):
    if not isinstance(packages, list):
        packages = [packages]

    cmd = "( %s )" % install_rpmfusion_command(os)
    for p in packages:
        cmd += " ; ( rpm -q %(package)s || sudo yum -y install %(package)s ) " % {
            'package': p}
    
    #cmd = ((rpm -q rpmfusion-free-release || sudo -s rpm -i ...) ; (rpm -q vim || sudo yum -y install vim))
    return " ( %s )" % cmd 

def remove_packages_command(os, packages):
    if not isinstance(packages, list):
        packages = [packages]

    cmd = ""
    for p in packages:
        cmd += " ( rpm -q %(package)s && sudo yum -y remove %(package)s ) ; " % {
                    'package': p}
    
    #cmd = (rpm -q vim || sudo yum -y remove vim) ; (...)
    return cmd 

def install_rpmfusion_command(os):
    cmd = "rpm -q rpmfusion-free-release || sudo -S rpm -i %(package)s"

    if os == "f12":
        cmd =  cmd %  {'package': RPM_FUSION_URL_F12}
    elif os == "f14":
        # This one works for f13+
        cmd = cmd %  {'package': RPM_FUSION_URL}
    else:
        cmd = ""

    return cmd
 
