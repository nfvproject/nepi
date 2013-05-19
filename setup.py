#!/usr/bin/env python
from distutils.core import setup
import sys

setup(
        name        = "nepi",
        version     = "3.0",
        description = "Network Experiment Controller",
        author      = "Alina Quereilhac",
        url         = "",
        license     = "GPLv2",
        platforms   = "Linux",
        packages    = [
            "nepi",
            "nepi.design",
            "nepi.execution",
            "nepi.resources",
            "nepi.resources.linux",
            "nepi.resources.netns",
            "nepi.resources.ns3",
            "nepi.resources.omf",
            "nepi.resources.planetlab",
            "nepi.util"],
        package_dir = {"": "src"},
    )
