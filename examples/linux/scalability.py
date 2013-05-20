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

#!/usr/bin/env python
from nepi.execution.ec import ExperimentController, ECState 
from nepi.execution.resource import ResourceState, ResourceAction, \
        populate_factory

from optparse import OptionParser, SUPPRESS_HELP

import os
import time

def add_node(ec, host, user):
    node = ec.register_resource("LinuxNode")
    ec.set(node, "hostname", host)
    ec.set(node, "username", user)
    ec.set(node, "cleanHome", True)
    ec.set(node, "cleanProcesses", True)
    return node

def add_app(ec):
    app = ec.register_resource("LinuxApplication")
    ec.set(app, "command", "sleep 30; echo 'HOLA'")
    return app

def get_options():
    slicename = os.environ.get("PL_SLICE")

    usage = "usage: %prog -s <pl-slice>"

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--pl-slice", dest="pl_slice", 
            help="PlanetLab slicename", default=slicename, type="str")
    parser.add_option("-l", "--exp-id", dest="exp_id", 
            help="Label to identify experiment", type="str")

    (options, args) = parser.parse_args()

    return (options.pl_slice, options.exp_id)

if __name__ == '__main__':
    ( pl_slice, exp_id ) = get_options()

    # Search for available RMs
    populate_factory()
    
    apps = []
  
    hostnames = [
             "planetlab-2.research.netlab.hut.fi",
             "planetlab2.willab.fi",
             "planetlab3.hiit.fi",
             "planetlab4.hiit.fi",
             "planetlab1.willab.fi",
             "planetlab1.s3.kth.se",
             "itchy.comlab.bth.se",
             "planetlab-1.ida.liu.se",
             "planetlab2.s3.kth.se",
             "planetlab1.sics.se",
             "planetlab1.tlm.unavarra.es",
             "planetlab2.uc3m.es",
             "planetlab1.uc3m.es",
             "planetlab2.um.es",
             "planet1.servers.ua.pt",
             "planetlab2.fct.ualg.pt",
             "planetlab-1.tagus.ist.utl.pt",
             "planetlab-2.tagus.ist.utl.pt",
             "planetlab-um00.di.uminho.pt",
             "planet2.servers.ua.pt",
             "planetlab1.mini.pw.edu.pl",
             "roti.mimuw.edu.pl",
             "planetlab1.ci.pwr.wroc.pl",
             "planetlab1.pjwstk.edu.pl",
             "ple2.tu.koszalin.pl",
             "planetlab2.ci.pwr.wroc.pl",
             "planetlab2.cyfronet.pl",
             "plab2.ple.silweb.pl",
             "planetlab1.cyfronet.pl",
             "plab4.ple.silweb.pl",
             "ple2.dmcs.p.lodz.pl",
             "planetlab2.pjwstk.edu.pl",
             "ple1.dmcs.p.lodz.pl",
             "gschembra3.diit.unict.it",
             "planetlab1.science.unitn.it",
             "planetlab-1.ing.unimo.it",
             "gschembra4.diit.unict.it",
             "iraplab1.iralab.uni-karlsruhe.de",
             "planetlab-1.fokus.fraunhofer.de",
             "iraplab2.iralab.uni-karlsruhe.de",
             "planet2.zib.de",
             "pl2.uni-rostock.de",
             "onelab-1.fhi-fokus.de",
             "planet2.l3s.uni-hannover.de",
             "planetlab1.exp-math.uni-essen.de",
             "planetlab-2.fokus.fraunhofer.de",
             "planetlab02.tkn.tu-berlin.de",
             "planetlab1.informatik.uni-goettingen.de",
             "planetlab1.informatik.uni-erlangen.de",
             "planetlab2.lkn.ei.tum.de",
             "planetlab1.wiwi.hu-berlin.de",
             "planet1.l3s.uni-hannover.de",
             "planetlab1.informatik.uni-wuerzburg.de",
             "host3-plb.loria.fr",
             "inriarennes1.irisa.fr",
             "inriarennes2.irisa.fr",
             "peeramide.irisa.fr",
             "planetlab-1.imag.fr",
             "planetlab-2.imag.fr",
             "ple2.ipv6.lip6.fr",
             "planetlab1.u-strasbg.fr",
             "planetlab1.ionio.gr",
             "planetlab2.ionio.gr",
             "stella.planetlab.ntua.gr",
             "vicky.planetlab.ntua.gr",
             "planetlab1.cs.uoi.gr",
             "pl002.ece.upatras.gr",
             "planetlab04.cnds.unibe.ch",
             "lsirextpc01.epfl.ch",
             "planetlab2.csg.uzh.ch",
             "planetlab1.csg.uzh.ch",
             "planetlab-2.cs.unibas.ch",
             "planetlab-1.cs.unibas.ch",
             "planetlab4.cs.st-andrews.ac.uk",
             "planetlab3.xeno.cl.cam.ac.uk",
             "planetlab1.xeno.cl.cam.ac.uk",
             "planetlab2.xeno.cl.cam.ac.uk",
             "planetlab3.cs.st-andrews.ac.uk",
             "planetlab1.aston.ac.uk",
             "planetlab1.nrl.eecs.qmul.ac.uk",
             "chimay.infonet.fundp.ac.be",
             "orval.infonet.fundp.ac.be",
             "rochefort.infonet.fundp.ac.be",
            ]
 
    ec = ExperimentController(exp_id = exp_id)

    for host in hostnames:
        node = add_node(ec, host, pl_slice)
        for i in xrange(20):
            app = add_app(ec)
            ec.register_connection(app, node)
            apps.append(app)

    ec.deploy()

    ec.wait_finished(apps)

    ec.shutdown()
