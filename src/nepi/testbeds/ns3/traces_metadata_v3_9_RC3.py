#!/usr/bin/env python
# -*- coding: utf-8 -*-

traces = dict({
    "p2ppcap": dict({
                "name": "P2PPcapTrace",
                "help": "Trace to sniff packets from a P2P network device"
              }),
    "p2pascii": dict({
                "name": "P2PAsciiTrace",
                "help": "Ascii trace from a P2P network device"
              }),
    "csmapcap_promisc": dict({
                "name": "CsmaPromiscPcapTrace",
                "help": "Trace to sniff packets from a Csma network device in promiscuous mode"
              }),
    "csmapcap": dict({
                "name": "CsmaPcapTrace",
                "help": "Trace to sniff packets from a Csma network device"
              }),
    "fdpcap": dict({
                "name": "FileDescriptorPcapTrace",
                "help": "Trace to sniff packets from a FileDescriptor network device"
              }),
    "yanswifipcap": dict({
                "name": "YansWifiPhyPcapTrace",
                "help": "Trace to sniff packets from a Wifi network device"
              }),
    "wimaxpcap": dict({
                "name": "WimaxPcapTrace",
                "help": "Trace to sniff packets from a wimax network station"
              }),
    "wimaxascii": dict({
                "name": "WimaxAsciiTrace",
                "help": "Ascii trace from a wimax network station"
              }),
})
