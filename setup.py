#!/usr/bin/env python
from nepi import __version__

from distutils.core import setup
import sys

setup(
        name        = "nepi",
        version     = __version__,
        description = "Network Experiment Management Framework",
        author      = "Alina Quereilhac, Julien Tribino, Lucia Guevgeozian",
        url         = "http://nepi.inria.fr",
        license     = "GPLv3",
        platforms   = "Linux, OSX",
        packages    = [
            "nepi",
            "nepi.design",
            "nepi.execution",
            "nepi.resources",
            "nepi.resources.all",
            "nepi.resources.linux",
            "nepi.resources.linux.ccn",
            "nepi.resources.linux.ns3",
            "nepi.resources.netns",
            "nepi.resources.ns3",
            "nepi.resources.omf",
            "nepi.resources.planetlab",
            "nepi.resources.planetlab.openvswitch",
            "nepi.util"],
        package_dir = {"": "src"},
        package_data = {
            "nepi.resources.planetlab" : [ "scripts/*.py" ],
            "nepi.resources.linux" : [ "scripts/*.py" ]
            }
    )
