#!/usr/bin/env python
# vim: set fileencoding=utf-8
from distutils.core import setup, Extension, Command

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
            "nepi.util" ],
        package_dir = {"": "src"},
        package_data = {"nepi.testbeds.planetlab" : ["scripts/*.py", "scripts/*.c"],
                        "nepi.util" : ["*.tpl"] },
    )
