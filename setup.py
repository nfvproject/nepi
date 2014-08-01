#!/usr/bin/env python

from distutils.core import setup
import sys

setup(
        name        = "nepi",
        version     = "nepi-3-dev",
        description = "Network Experiment Management Framework",
        author      = "Alina Quereilhac, Julien Tribino, Lucia Guevgeozian",
        url         = "http://nepi.inria.fr",
        license     = "GPLv3",
        platforms   = "Linux, OSX",
        packages    = [
            "nepi",
            "nepi.execution",
            "nepi.resources",
            "nepi.resources.all",
            "nepi.resources.linux",
            "nepi.resources.linux.ccn",
            "nepi.resources.linux.ns3",
            "nepi.resources.linux.ns3.ccn",
            "nepi.resources.netns",
            "nepi.resources.ns3",
            "nepi.resources.ns3.classes",
            "nepi.resources.omf",
            "nepi.resources.planetlab",
            "nepi.resources.planetlab.openvswitch",
            "nepi.util",
            "nepi.util.parsers"],
        package_dir = {"": "src"},
        package_data = {
            "nepi.resources.planetlab" : [ "scripts/*.py" ],
            "nepi.resources.linux" : [ "scripts/*.py" ],
            "nepi.resources.linux.ns3" : [ "dependencies/*.tar.gz" ]
            }
    )
