#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>


# Test based on ns-3 csma/examples/csma-ping.cc file
#
# Network topology
#
#       n0    n1   n2   n3
#       |     |    |    |
#       -----------------
#
#  node n0 sends IGMP traffic to node n3


from nepi.resources.ns3.ns3wrapper import NS3Wrapper

import subprocess
import time
import unittest

class NS3WrapperTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_csma_ping(self):
        wrapper = NS3Wrapper()

        ### create 4  nodes
        # NodeContainer c;
        c = wrapper.create("NodeContainer")

        # c.Create (4);
        wrapper.invoke(c, "Create", 4)

        ### connect the nodes to a shared channel
        # CsmaHelper csma;
        csma = wrapper.create("CsmaHelper")

        # csma.SetChannelAttribute ("DataRate", DataRateValue (DataRate (5000000)));
        dr = wrapper.create("DataRate", 5000000)
        drv = wrapper.create("DataRateValue", dr)
        wrapper.invoke(csma, "SetChannelAttribute", "DataRate", drv)

        # csma.SetChannelAttribute ("Delay", TimeValue (MilliSeconds (2)));
        ms = wrapper.create("MilliSeconds", 2)
        delay = wrapper.create("TimeValue", ms)
        wrapper.invoke(csma, "SetChannelAttribute", "Delay", delay)

        # csma.SetDeviceAttribute ("EncapsulationMode", StringValue ("Llc"));
        encap = wrapper.create("StringValue", "Llc")
        wrapper.invoke(csma, "SetDeviceAttribute", "EncapsulationMode", encap)

        # NetDeviceContainer devs = csma.Install (c);
        devs = wrapper.invoke(csma, "Install", c)

        ### add IP stack to all nodes
        # InternetStackHelper ipStack;
        ipStack = wrapper.create("InternetStackHelper")
        
        # ipStack.Install (c);
        wrapper.invoke(ipStack, "Install", c)

        ### assign ip addresses
        #Ipv4AddressHelper ip;
        ip = wrapper.create("Ipv4AddressHelper")

        # ip.SetBase ("192.168.1.0", "255.255.255.0");
        ip4 = wrapper.create("Ipv4Address", "192.168.1.0")
        mask4 = wrapper.create("Ipv4Mask", "255.255.255.0")
        wrapper.invoke(ip, "SetBase", ip4, mask4)

        # Ipv4InterfaceContainer addresses = ip.Assign (devs);
        addresses = wrapper.invoke(ip, "Assign", devs)

        ### Create source
        # Config::SetDefault ("ns3::Ipv4RawSocketImpl::Protocol", StringValue ("2"));
        proto = wrapper.create("StringValue", "2")
        wrapper.invoke("singleton::Config", "SetDefault", 
                "ns3::Ipv4RawSocketImpl::Protocol", proto)

        # InetSocketAddress dst = InetSocketAddress (addresses.GetAddress (3));
        addr3 = wrapper.invoke(addresses, "GetAddress", 3)
        dst = wrapper.create("InetSocketAddress", addr3)

        # OnOffHelper onoff = OnOffHelper ("ns3::Ipv4RawSocketFactory", dst);
        onoff = wrapper.create("OnOffHelper", "ns3::Ipv4RawSocketFactory", dst)

        # onoff.SetAttribute ("DataRate", DataRateValue (DataRate (15000)));
        dr2 = wrapper.create("DataRate", 15000)
        drv2 = wrapper.create("DataRateValue", dr2)
        wrapper.invoke(onoff, "SetAttribute", "DataRate", drv2)

        # onoff.SetAttribute ("PacketSize", UintegerValue (1200));
        uiv = wrapper.create("UintegerValue", 1200)
        wrapper.invoke(onoff, "SetAttribute", "PacketSize", uiv)

        # ApplicationContainer apps = onoff.Install (c.Get (0));
        n1 = wrapper.invoke(c, "Get", 0)
        apps = wrapper.invoke(onoff, "Install", n1)
        
        # apps.Start (Seconds (1.0));
        s1 = wrapper.create("Seconds", 1.0)
        wrapper.invoke(apps, "Start", s1)
        
        # apps.Stop (Seconds (10.0));
        s2 = wrapper.create("Seconds", 10.0)
        wrapper.invoke(apps, "Stop", s2)

        ### create sink
        # PacketSinkHelper sink = PacketSinkHelper ("ns3::Ipv4RawSocketFactory", dst);
        sink = wrapper.create("PacketSinkHelper", "ns3::Ipv4RawSocketFactory", dst)
        
        # apps = sink.Install (c.Get (3));
        n3 = wrapper.invoke(c, "Get", 3)
        apps = wrapper.invoke (sink, "Install", n3)
        
        # apps.Start (Seconds (0.0));
        s3 = wrapper.create ("Seconds", 0.0)
        wrapper.invoke (apps, "Start", s3)
        
        # apps.Stop (Seconds (11.0));
        s4 = wrapper.create ("Seconds", 11.0)
        wrapper.invoke (apps, "Stop", s4)

        ### create pinger
        #V4PingHelper ping = V4PingHelper (addresses.GetAddress (2));
        addr2 = wrapper.invoke(addresses, "GetAddress", 2)
        ping = wrapper.create("V4PingHelper", addr2)
        
        #NodeContainer pingers;
        pingers = wrapper.create("NodeContainer")
        
        #pingers.Add (c.Get (0));
        n0 = wrapper.invoke(c, "Get", 0)
        wrapper.invoke(pingers, "Add", n0)
        
        #pingers.Add (c.Get (1));
        n1 = wrapper.invoke(c, "Get", 1)
        wrapper.invoke(pingers, "Add", n1)
        
        #pingers.Add (c.Get (3));
        n3 = wrapper.invoke(c, "Get", 3)
        wrapper.invoke(pingers, "Add", n3)
        
        #apps = ping.Install (pingers);
        apps = wrapper.invoke(ping, "Install", pingers)
        
        #apps.Start (Seconds (2.0));
        s5 = wrapper.create ("Seconds", 2.0)
        wrapper.invoke (apps, "Start", s5)
        
        #apps.Stop (Seconds (5.0));
        s6 = wrapper.create ("Seconds", 5.0)
        wrapper.invoke (apps, "Stop", s6)

        ### configure tracing
        #csma.EnablePcapAll ("csma-ping", false);
        wrapper.invoke(csma, "EnablePcapAll", "/tmp/csma-ping-pcap", False)
 
        #csma.EnableAsciiAll ("csma-ping", false);
        wrapper.invoke(csma, "EnableAsciiAll", "/tmp/csma-ping-ascii")
 
        def SinkRx(packet, address):
            print packet

        def PingRtt(context, rtt):
            print context, rtt
      
        # XXX: No biding for MakeCallback
        #Config::ConnectWithoutContext ("/NodeList/3/ApplicationList/0/$ns3::PacketSink/Rx", 
        # MakeCallback (&SinkRx));
        #cb = wrapper.create("MakeCallback", SinkRx)
        #wrapper.invoke("singleton::Config", "ConnectWithoutContext", 
        #        "/NodeList/3/ApplicationList/0/$ns3::PacketSink/Rx", cb)

        # Config::Connect ("/NodeList/*/ApplicationList/*/$ns3::V4Ping/Rtt", 
        # MakeCallback (&PingRtt));
        #cb2 = wrapper.create("MakeCallback", PingRtt)
        #wrapper.invoke("singleton::Config", "ConnectWithoutContext", 
        #        "/NodeList/*/ApplicationList/*/$ns3::V4Ping/Rtt", 
        #        cb2)

        # Packet::EnablePrinting ();
        wrapper.invoke("singleton::Packet", "EnablePrinting")

        ### run Simulation
        # Simulator::Run ();
        wrapper.invoke("singleton::Simulator", "Run")

        # Simulator::Destroy ();
        wrapper.invoke("singleton::Simulator", "Destroy")

        p = subprocess.Popen("ls /tmp/csma-ping-* | wc -w", stdout = subprocess.PIPE, 
                stderr = subprocess.PIPE, shell = True)
        (out, err) = p.communicate()

        self.assertEquals(int(out), 8)

        p = subprocess.Popen("rm /tmp/csma-ping-*",  shell = True)
        p.communicate()

    def test_start(self):
        wrapper = NS3Wrapper()

        ### create 2  nodes
        c = wrapper.create("NodeContainer")

        # c.Create (2);
        wrapper.invoke(c, "Create", 2)

        ### connect the nodes to a shared channel
        # CsmaHelper csma;
        csma = wrapper.create("CsmaHelper")

        # csma.SetChannelAttribute ("DataRate", DataRateValue (DataRate (5000000)));
        dr = wrapper.create("DataRate", 5000000)
        drv = wrapper.create("DataRateValue", dr)
        wrapper.invoke(csma, "SetChannelAttribute", "DataRate", drv)

        # csma.SetChannelAttribute ("Delay", TimeValue (MilliSeconds (2)));
        ms = wrapper.create("MilliSeconds", 2)
        delay = wrapper.create("TimeValue", ms)
        wrapper.invoke(csma, "SetChannelAttribute", "Delay", delay)

        # NetDeviceContainer devs = csma.Install (c);
        devs = wrapper.invoke(csma, "Install", c)

        ### add IP stack to all nodes
        # InternetStackHelper ipStack;
        ipStack = wrapper.create("InternetStackHelper")
        
        # ipStack.Install (c);
        wrapper.invoke(ipStack, "Install", c)

        ### assign ip addresses
        #Ipv4AddressHelper ip;
        ip = wrapper.create("Ipv4AddressHelper")

        # ip.SetBase ("192.168.1.0", "255.255.255.0");
        ip4 = wrapper.create("Ipv4Address", "192.168.1.0")
        mask4 = wrapper.create("Ipv4Mask", "255.255.255.0")
        wrapper.invoke(ip, "SetBase", ip4, mask4)

        # Ipv4InterfaceContainer addresses = ip.Assign (devs);
        addresses = wrapper.invoke(ip, "Assign", devs)

        ### create pinger
        #V4PingHelper ping = V4PingHelper (addresses.GetAddress (1));
        addr1 = wrapper.invoke(addresses, "GetAddress", 1)
        ping = wrapper.create("V4PingHelper", addr1)
        btrue = wrapper.create("BooleanValue", True)
        wrapper.invoke(ping, "SetAttribute", "Verbose", btrue)
        
        #apps = ping.Install (pingers);
        n0 = wrapper.invoke(c, "Get", 0)
        apps = wrapper.invoke(ping, "Install", n0)
        
        #apps.Start (Seconds (0.0));
        s = wrapper.create ("Seconds", 0.0)
        wrapper.invoke (apps, "Start", s)
        
        #apps.Stop (Seconds (5.0));
        s = wrapper.create ("Seconds", 5.0)
        wrapper.invoke (apps, "Stop", s)

        ### run Simulation
        # Simulator::Stop (6.0);
        wrapper.stop(time = "6s")

        # Simulator::Run ();
        wrapper.start()

        # wait until simulation is over
        wrapper.shutdown()

    def test_runtime_attr_modify(self):
        wrapper = NS3Wrapper()
       
        # Define a real time simulation 
        stype = wrapper.create("StringValue", "ns3::RealtimeSimulatorImpl")
        wrapper.invoke("singleton::GlobalValue", "Bind", "SimulatorImplementationType", stype)
        btrue = wrapper.create("BooleanValue", True)
        wrapper.invoke("singleton::GlobalValue", "Bind", "ChecksumEnabled", btrue)

        ### create 2  nodes
        ## NODE 1
        n1 = wrapper.create("Node")

        ## Install internet stack
        ipv41 = wrapper.create("Ipv4L3Protocol")
        wrapper.invoke(n1, "AggregateObject", ipv41)

        arp1 = wrapper.create("ArpL3Protocol")
        wrapper.invoke(n1, "AggregateObject", arp1)
        
        icmp1 = wrapper.create("Icmpv4L4Protocol")
        wrapper.invoke(n1, "AggregateObject", icmp1)

        ## Add IPv4 routing
        lr1 = wrapper.create("Ipv4ListRouting")
        wrapper.invoke(ipv41, "SetRoutingProtocol", lr1)
        sr1 = wrapper.create("Ipv4StaticRouting")
        wrapper.invoke(lr1, "AddRoutingProtocol", sr1, 1)

        ## NODE 2
        n2 = wrapper.create("Node")

        ## Install internet stack
        ipv42 = wrapper.create("Ipv4L3Protocol")
        wrapper.invoke(n2, "AggregateObject", ipv42)

        arp2 = wrapper.create("ArpL3Protocol")
        wrapper.invoke(n2, "AggregateObject", arp2)
        
        icmp2 = wrapper.create("Icmpv4L4Protocol")
        wrapper.invoke(n2, "AggregateObject", icmp2)

        ## Add IPv4 routing
        lr2 = wrapper.create("Ipv4ListRouting")
        wrapper.invoke(ipv42, "SetRoutingProtocol", lr2)
        sr2 = wrapper.create("Ipv4StaticRouting")
        wrapper.invoke(lr2, "AddRoutingProtocol", sr2, 1)

        ##### Create p2p device and enable ascii tracing

        p2pHelper = wrapper.create("PointToPointHelper")
        asciiHelper = wrapper.create("AsciiTraceHelper")

        # Iface for node1
        p1 = wrapper.create("PointToPointNetDevice")
        wrapper.invoke(n1, "AddDevice", p1)
        q1 = wrapper.create("DropTailQueue")
        wrapper.invoke(p1, "SetQueue", q1)
      
        # Add IPv4 address
        ifindex1 = wrapper.invoke(ipv41, "AddInterface", p1)
        mask1 = wrapper.create("Ipv4Mask", "/30")
        addr1 = wrapper.create("Ipv4Address", "10.0.0.1")
        inaddr1 = wrapper.create("Ipv4InterfaceAddress", addr1, mask1)
        wrapper.invoke(ipv41, "AddAddress", ifindex1, inaddr1)
        wrapper.invoke(ipv41, "SetMetric", ifindex1, 1)
        wrapper.invoke(ipv41, "SetUp", ifindex1)

        # Enable collection of Ascii format to a specific file
        filepath1 = "/tmp/trace-p2p-1.tr"
        stream1 = wrapper.invoke(asciiHelper, "CreateFileStream", filepath1)
        wrapper.invoke(p2pHelper, "EnableAscii", stream1, p1)
       
        # Iface for node2
        p2 = wrapper.create("PointToPointNetDevice")
        wrapper.invoke(n2, "AddDevice", p2)
        q2 = wrapper.create("DropTailQueue")
        wrapper.invoke(p2, "SetQueue", q2)

        # Add IPv4 address
        ifindex2 = wrapper.invoke(ipv42, "AddInterface", p2)
        mask2 = wrapper.create("Ipv4Mask", "/30")
        addr2 = wrapper.create("Ipv4Address", "10.0.0.2")
        inaddr2 = wrapper.create("Ipv4InterfaceAddress", addr2, mask2)
        wrapper.invoke(ipv42, "AddAddress", ifindex2, inaddr2)
        wrapper.invoke(ipv42, "SetMetric", ifindex2, 1)
        wrapper.invoke(ipv42, "SetUp", ifindex2)

        # Enable collection of Ascii format to a specific file
        filepath2 = "/tmp/trace-p2p-2.tr"
        stream2 = wrapper.invoke(asciiHelper, "CreateFileStream", filepath2)
        wrapper.invoke(p2pHelper, "EnableAscii", stream2, p2)

        # Create channel
        chan = wrapper.create("PointToPointChannel")
        wrapper.set(chan, "Delay", "0s")
        wrapper.invoke(p1, "Attach", chan)
        wrapper.invoke(p2, "Attach", chan)

        ### create pinger
        ping = wrapper.create("V4Ping")
        wrapper.invoke(n1, "AddApplication", ping)
        wrapper.set (ping, "Remote", "10.0.0.2")
        wrapper.set (ping, "Interval", "1s")
        wrapper.set (ping, "Verbose", True)
        wrapper.set (ping, "StartTime", "0s")
        wrapper.set (ping, "StopTime", "20s")

        ### run Simulation
        wrapper.stop(time = "21s")
        wrapper.start()

        time.sleep(1)

        wrapper.set(chan, "Delay", "5s")

        time.sleep(5)

        wrapper.set(chan, "Delay", "0s")

        # wait until simulation is over
        wrapper.shutdown()

        p = subprocess.Popen("rm /tmp/trace-p2p-*",  shell = True)
        p.communicate()

if __name__ == '__main__':
    unittest.main()

