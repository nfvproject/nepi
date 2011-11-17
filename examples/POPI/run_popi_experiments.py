#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.execute import ExperimentController
from optparse import OptionParser, SUPPRESS_HELP
import collections
import commands
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
import getpass
import cPickle

class PopiExample(object):
    _testsets = dict({
        "popi":  "./popi-tun-classfilter-2MB-q500-pl.xml",
        "popi_hibw":  "./popi-tun-classfilter-2MB-q500-pl-hibw.xml",
        })
    
    classes = {
        'tcpx4' : 'udp:tcp*4:icmp:',
        'icmpx4' : 'udp:tcp:icmp*4:',
        'udpx4' : 'udp*4:tcp:icmp:',
        'u1t4i16' : 'udp:tcp*4:icmp*16:',
        'u4t4i16' : 'udp*4:tcp*4:icmp*16:',
        'u1t16i16' : 'udp*4:tcp*16:icmp*16:',
        'u1t1t1' : 'udp:tcp:icmp:',
    }
    
    bwlimits = {
        '32K' : '32',
        '64K' : '64',
        '128K' : '128',
        '256K' : '256',
        '384K' : '384',
    #    '512K' : '512',
    #    '768K' : '768',
    #    '1M' : '1024',
    #    '2M' : '2048',
    }
    
    testsets = dict([
        ("%s-%s-%s" % (tset,clsname,bwname), (xml, {'classes':cls, 'bwlimit':bw}))
        for tset,xml in _testsets.iteritems()
        for clsname,cls in classes.iteritems()
        for bwname,bw in bwlimits.iteritems()
    ])

    def __init__(self):
        usage = "usage: %prog -u user -t times -d results_dir -f remove -e experiment -s start"
        parser = OptionParser(usage=usage)
        parser.add_option("-u", "--user", dest="pluser", help="PlanetLab PLC user (email)", type="str")
        parser.add_option("-p", "--pass", dest="plpass", help="PlanetLab PLC user (password) - leave empty for interactive prompt", type="str")
        parser.add_option("-k", "--key", dest="plkey", help="PlanetLab PLC private key to use", type="str")
        parser.add_option("-S", "--slice", dest="plslice", help="PlanetLab slice into which to deploy experiments", type="str")
        parser.add_option("-t", "--times", dest="times", help="Number of times to run each scenario", type="int")
        parser.add_option("-d", "--dir", dest="results_dir", help="Results directory", type="str")
        parser.add_option("-f", "--remove", dest="remove", help="Remove previous results directory",  action="store_true", default=False)
        parser.add_option("-e", "--experiment", dest="experiment", help="Experiment to execute [%s]" % ('|'.join(self._testsets.keys()),),  type="str")
        parser.add_option("-s", "--start", dest="start", help="Start experiment at specific iteration",  type="int")
        (options, args) = parser.parse_args()
        
        if not options.pluser:
            print >>sys.stderr, "Must specify --user"
            sys.exit(1)
        else:
            self.pluser = options.pluser
            
        if not options.plslice:
            print >>sys.stderr, "Must specify --slice"
            sys.exit(1)
        else:
            self.plslice = options.plslice
            
        if not options.plkey:
            print >>sys.stderr, "Must specify --key"
            sys.exit(1)
        else:
            self.plkey = options.plkey
            
        if not options.plpass:
            self.plpass = getpass.getpass("Password for %s: " % (self.pluser,))
            
        self.times = options.times if options.times else 5
        self.results_dir = options.results_dir if options.results_dir else "results"
        self.remove = options.remove
        if options.experiment:
            if ',' in options.experiment:
                options.experiment = options.experiment.split(',')
            else:
                options.experiment = [ options.experiment ]
        else:
            options.experiment = self.testsets.keys()
        self.experiments = [x for x in options.experiment if x in self.testsets]
        self.start = options.start if options.start else 0

    def run(self):
        duration = 3600

        if self.remove:
            try:
                shutil.rmtree(self.results_dir)
            except:
                traceback.print_exc(file=sys.stderr)

        try:
            os.mkdir(self.results_dir)
        except:
            traceback.print_exc(file=sys.stderr)

        for j,testset in enumerate(self.experiments):
            xml_filepath, replacements = self.testsets[testset]
            replacements = dict(replacements)
            replacements['pluser'] = self.pluser
            replacements['plpass'] = self.plpass
            replacements['plslice'] = self.plslice
            replacements['plkey'] = self.plkey
            
            for i in xrange(self.start, self.times):
                testset_dir = os.path.join(self.results_dir, testset, str(i))
                os.makedirs(testset_dir)

                print >>sys.stderr, "%3d%% - " % ((j+i*1.0/(self.times-self.start))*100/len(self.experiments),), testset, "...",
                
                # launch experiment
                command = "python run_one_experiment.py %d '%s' '%s' '%s' %d" % \
                        (duration, xml_filepath, testset, self.results_dir, i)
                # send by environment, we don't want passwords in the commandline
                env = dict(os.environ)
                env['POPI_REPLACEMENTS'] = cPickle.dumps(replacements,2).encode("base64").strip()
                
                for trials in xrange(5):
                    logfile = open(os.path.join(testset_dir,"log"), "w")
                    p = subprocess.Popen(
                        command, 
                        shell = True, 
                        env = env,
                        stdout = logfile,
                        stderr = logfile,
                        stdin = open("/dev/null","rb") )
                    
                    # we wait two time the estimated dirantion of the movie (120s)
                    for i in xrange(0, duration * 2, 10):
                        time.sleep(10)
                        returncode = p.poll()
                        if returncode is not None:
                            break
                    time.sleep(10)
                    try:
                        os.kill(p.pid, signal.SIGKILL)
                    except:
                        pass
                    
                    logfile.close()
                    retfile = open(os.path.join(testset_dir,"retcode"), "w")
                    if returncode:
                        rettext = "FAIL %s" % (returncode,)
                    else:
                        rettext = "SUCCESS"
                    retfile.write(rettext)
                    retfile.close()

                    print >>sys.stderr, rettext,
                    
                    if not returncode:
                        print >>sys.stderr
                        break
                    else:
                        time.sleep(60)
                else:
                    print >>sys.stderr, "Giving up"

if __name__ == '__main__':
    example = PopiExample()
    example.run()

