#!/usr/bin/env python
# vim: set fileencoding=utf-8
from distutils.core import setup
import sys

# CHECK dependencies
# Python >= 2.6
if sys.hexversion < 0x2060000:
    raise RuntimeError("Python version >= 2.6 required")
# ipaddr >= 2.1.7
try:
    import ipaddr
    l = ipaddr.__version__.split('.')
    l.reverse()
    if sum( int(l[i])*pow(10,i) for i in xrange(len(l))) < 217:
        raise RuntimeError("ipaddr >= 2.1.7 is required")
except:
    raise RuntimeError("ipaddr >= 2.1.7 is required. You can download from http://ipaddr-py.googlecode.com/files/ipaddr-2.1.7.tar.gz")

setup(
        name        = "nepi",
        version     = "0.2",
        description = "High-level abstraction for running network experiments",
        author      = "Mathieu Lacage, Alina Quereilhac, Martín Ferrari and Claudio Freire",
        url         = "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/nepi/",
        license     = "GPLv2",
        platforms   = "Linux",
        packages    = [
            "nepi",
            "nepi.testbeds",
            "nepi.testbeds.netns",
            "nepi.testbeds.ns3",
            "nepi.testbeds.planetlab",
            "nepi.core",
            "nepi.util.parser",
            "nepi.util.settools",
            "nepi.util.graphtools",
            "nepi.util" ],
        package_dir = {"": "src"},
        package_data = {"nepi.testbeds.planetlab" : [
                                "scripts/*.py", "scripts/*.c", "scripts/*.patch", 
                        ],
                        "nepi.util" : ["*.tpl"] },
    )
