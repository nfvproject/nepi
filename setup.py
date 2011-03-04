#!/usr/bin/env python
# vim: set fileencoding=utf-8
from distutils.core import setup, Extension, Command

setup(
        name        = "nepi",
        version     = "0.1",
        description = "High-level abstraction for running network experiments",
#        long_description = longdesc,
        author      = "Alina Quereilhac and Martín Ferrari",
        url         = "http://yans.pl.sophia.inria.fr/code/hgwebdir.cgi/nepi/",
        license     = "GPLv2",
        platforms   = "Linux",
        packages    = [
            "nepi",
            "nepi.testbeds",
            "nepi.testbeds.netns",
            "nepi.core",
            "nepi.util" ],
        package_dir = {"": "src"}
    )
