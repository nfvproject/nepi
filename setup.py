#!/usr/bin/env python
# vim: set fileencoding=utf-8
from distutils.core import setup, Extension, Command

setup(
        name        = "nepi",
        version     = "0.1",
        description = "High-level abstraction for running network experiments",
        author      = "Alina Quereilhac and Martín Ferrari",
        url         = "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/nepi/",
        license     = "GPLv2",
        platforms   = "Linux",
        packages    = [
            "nepi",
            "nepi.testbeds",
            "nepi.testbeds.netns",
            "nepi.testbeds.ns3",
            "nepi.core",
            "nepi.util.parser",
            "nepi.util" ],
        package_dir = {"": "src"}
    )
