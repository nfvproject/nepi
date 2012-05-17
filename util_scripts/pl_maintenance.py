import nepi.testbeds.planetlab.plcapi
from optparse import OptionParser, SUPPRESS_HELP
import os
import subprocess

def do_maintenance(slicename, hostnames):
    for hostname in hostnames:
        login = "%s@%s" % (slicename, hostname)
        command = 'sudo yum reinstall -y --nogpgcheck fedora-release'
        proc = subprocess.Popen(['ssh', '-t', '-o', 'StrictHostKeyChecking=no', login, command], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = False)
        retcode = proc.wait()
        print hostname
        print retcode
        if retcode > 0:
            print proc.stdout.read()
            print proc.stderr.read()

def run(slicename, plc_host, pl_user, pl_pwd, pl_ssh_key):
    api = nepi.testbeds.planetlab.plcapi.plcapi(pl_user, pl_pwd, plc_host,
        "https://%(hostname)s:443/PLCAPI/")
    node_ids = api.GetSliceNodes(slicename)
    hostnames = [d['hostname'] for d in api.GetNodes(node_ids, ['hostname'])]

    do_maintenance(slicename, hostnames)


if __name__ == '__main__':
    slicename = os.environ.get("PL_SLICE")
    pl_host = os.environ.get("PL_HOST", "www.planet-lab.eu")
    pl_ssh_key = os.environ.get(
        "PL_SSH_KEY",
        "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
    pl_user = os.environ.get('PL_USER')
    pl_pwd = os.environ.get('PL_PASS')

    usage = "usage: %prog -s <pl_slice> -H <pl_host> -k <ssh_key> -u <pl_user> -p <pl_password>"

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--slicename", dest="slicename", 
            help="PlanetLab slicename", default=slicename, type="str")
    parser.add_option("-H", "--pl-host", dest="pl_host", 
            help="PlanetLab site (e.g. www.planet-lab.eu)", 
            default=pl_host, type="str")
    parser.add_option("-k", "--ssh-key", dest="pl_ssh_key", 
            help="Path to private ssh key used for PlanetLab authentication", 
            default=pl_ssh_key, type="str")
    parser.add_option("-u", "--pl-user", dest="pl_user", 
            help="PlanetLab account user (i.e. Registration email address)", 
            default=pl_user, type="str")
    parser.add_option("-p", "--pl-pwd", dest="pl_pwd", 
            help="PlanetLab account password", default=pl_pwd, type="str")
    (options, args) = parser.parse_args()

    slicename = options.slicename
    pl_host = options.pl_host
    pl_user= options.pl_user
    pl_pwd = options.pl_pwd
    pl_ssh_key = options.pl_ssh_key

    run(slicename, pl_host, pl_user, pl_pwd, pl_ssh_key)

