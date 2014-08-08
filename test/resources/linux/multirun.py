#!/usr/bin/env python
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

from nepi.execution.ec import ExperimentController 
from nepi.execution.runner import ExperimentRunner 

from test_utils import skipIfNotAlive, skipInteractive

import functools
import glob
import os
import re
import shutil
import time
import tempfile
import unittest

_ping_re = re.compile("[^/]+rtt min/avg/max/mdev = (?P<min>\d\.\d+)/(?P<avg>\d\.\d+)/(?P<max>\d\.\d+)/(?P<mdev>\d\.\d+)[^/]+", re.MULTILINE)

class LinuxMultiRunTestCase(unittest.TestCase):
    def setUp(self):
        self.fedora_host = "nepi2.pl.sophia.inria.fr"
        self.fedora_user = "inria_nepi"

        self.ubuntu_host = "roseval.pl.sophia.inria.fr"
        self.ubuntu_user = "inria_nepi"
        
        self.target = "nepi5.pl.sophia.inria.fr"

    @skipIfNotAlive
    def t_simple_multirun(self, host, user, depends):

        dirpath = tempfile.mkdtemp()

        ec = ExperimentController(exp_id = "test-condition-multirun", 
                local_dir = dirpath)
        
        node = ec.register_resource("LinuxNode")
        ec.set(node, "hostname", host)
        ec.set(node, "username", user)
        ec.set(node, "cleanHome", True)
        ec.set(node, "cleanProcesses", True)

        ping = ec.register_resource("LinuxApplication")
        ec.set(ping, "command", "ping -c10 nepi.inria.fr")
        ec.register_connection(ping, node)

        collector = ec.register_resource("Collector")
        ec.set(collector, "traceName", "stdout")
        ec.register_connection(ping, collector)

        def compute_metric_callback(ping, ec, run):
            stdout = ec.trace(ping, "stdout")

            m = _ping_re.match(stdout)
            if not m:
                return None
            
            return float(m.groupdict()["min"])

        metric_callback = functools.partial(compute_metric_callback, ping)

        rnr = ExperimentRunner()
        runs = rnr.run(ec, min_runs = 5, 
                compute_metric_callback = metric_callback,
                wait_guids = [ping],
                wait_time = 0)

        self.assertTrue(runs >= 5)

        dircount = 0

        for d in os.listdir(ec.exp_dir):
            path = os.path.join(ec.exp_dir, d)
            if os.path.isdir(path):
                dircount += 1
                logs = glob.glob(os.path.join(path, "*.stdout"))
                self.assertEquals(len(logs), 1)
        
        self.assertEquals(runs, dircount)

        shutil.rmtree(dirpath)

    def test_simple_multirun_fedora(self):
        self.t_simple_multirun(self.fedora_host, self.fedora_user, "nc")

    def test_simple_multirun_ubuntu(self):
        self.t_simple_multirun(self.ubuntu_host, self.ubuntu_user, "netcat")

if __name__ == '__main__':
    unittest.main()

