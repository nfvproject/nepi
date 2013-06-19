#!/usr/bin/env python
from distutils.core import setup
import sys

setup(
        name        = "nepi",
        version     = "3.0",
        description = "Network Experiment Management Framework",
        author      = "Alina Quereilhac, Julien Tribino, Lucia Guevgeozian",
        url         = "http://nepi.inria.fr",
        license     = "GPLv3",
        platforms   = "Linux",
        packages    = [
            "nepi",
            "nepi.design",
            "nepi.execution",
            "nepi.resources",
            "nepi.resources.linux",
            "nepi.resources.linux.ccn",
            "nepi.resources.netns",
            "nepi.resources.ns3",
            "nepi.resources.omf",
            "nepi.resources.planetlab",
            "nepi.util"],
        package_dir = {"": "src"},
    )
