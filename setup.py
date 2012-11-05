#!/usr/bin/env python
from distutils.core import setup
import sys

setup(
        name        = "neco",
        version     = "0.01",
        description = "Network Experiment Controller",
        author      = "Alina Quereilhac",
        url         = "",
        license     = "GPLv2",
        platforms   = "Linux",
        packages    = [
            "neco",
            "neco.design",
            "neco.execution",
            "neco.resources",
            "neco.resources.base",
            "neco.resources.netns",
            "neco.resources.ns3",
            "neco.tags",
            "neco.util"],
        package_dir = {"": "src"},
    )
