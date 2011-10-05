#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import re
import time
import commands
import subprocess
import collections
import signal
import traceback
import shutil
import sys
import cPickle
import gzip

sys.path.append(os.path.abspath("../../src"))

from nepi.core.execute import ExperimentController

class PopiExperiment(object):
    def run(self, duration, xml_filepath, testset, results_dir, iteration):
        app_guid = 8

        testset_dir = os.path.join(results_dir, testset)
        
        # create test results file
        test_dir = os.path.join(testset_dir, str(iteration))

        # replace results values in xml
        replacements = cPickle.loads(os.environ['POPI_REPLACEMENTS'].strip().decode("base64"))
        file = open(xml_filepath)
        xml2 = xml = file.read()
        file.close()

        for key,value in replacements.iteritems():
            xml2 = xml2.replace("##%s##" % (key,), value)

        # launch experiment
        controller = ExperimentController(xml2, results_dir)
        
        try:
            controller.start()

            t0 = time.time()
            t1 = t0
            while (t1-t0) < duration and not controller.is_finished(app_guid):
                time.sleep(10)
            
            # download results
            for testbed_guid, guids in controller.traces_info().iteritems():
                for guid, traces in guids.iteritems():
                    for name, data in traces.iteritems():
                        path = data["filepath"]
                        print >>sys.stderr, "Downloading trace", path
                        
                        filepath = os.path.join(test_dir, path)
                        
                        try:
                            trace = controller.trace(guid, name)
                        except:
                            traceback.print_exc(file=sys.stderr)
                            continue
                        try:
                            if not os.path.exists(os.path.dirname(filepath)):
                                os.makedirs(os.path.dirname(filepath))
                        except:
                            traceback.print_exc(file=sys.stderr)
                        
                        try:
                            if len(trace) >= 2**20:
                                # Bigger than 1M, compress
                                tracefile = gzip.GzipFile(filepath+".gz", "wb")
                            else:
                                tracefile = open(filepath,"wb")
                            try:
                                tracefile.write(trace)
                            finally:
                                tracefile.close()
                        except:
                            traceback.print_exc(file=sys.stderr)

        finally:
            # clean up
            try:
                controller.stop()
            except:
                pass
            try:
                controller.shutdown()
            except:
                pass

    def results_append(self, file, testset, sta_pcap, ap_pcap):
        line = "%s %s %s\n" % (testset, sta_pcap, ap_pcap)
        file.write(line)

if __name__ == '__main__':
    experiment = PopiExperiment()
    duration = int(sys.argv[1])
    xml_filepath = sys.argv[2]
    testset = sys.argv[3]
    results_dir = sys.argv[4]
    iteration = sys.argv[5]
    experiment.run(duration, xml_filepath, testset, results_dir, iteration)

