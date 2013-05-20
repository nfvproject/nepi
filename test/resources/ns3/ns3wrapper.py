"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

#!/usr/bin/env python
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

import os.path
import time
import tempfile
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
        config = wrapper.singleton("Config")
        
        # Config::SetDefault ("ns3::Ipv4RawSocketImpl::Protocol", StringValue ("2"));
        proto = wrapper.create("StringValue", "2")
        wrapper.invoke(config, "SetDefault", "ns3::Ipv4RawSocketImpl::Protocol", proto)

        # InetSocketAddress dst = InetSocketAddress (addresses.GetAddress (3));
        addr3 = wrapper.invoke(addresses, "GetAddress", 3)
        dst = wrapper.create("InetSocketAddress", addr3)

        # OnOffHelper onoff = OnOffHelper ("ns3::Ipv4RawSocketFactory", dst);
        onoff = wrapper.create("OnOffHelper", "ns3::Ipv4RawSocketFactory", dst)

        # onoff.SetAttribute ("OnTime", RandomVariableValue (ConstantVariable (1.0)));
        cv1 = wrapper.create("ConstantVariable", 1.0)
        rand1 = wrapper.create("RandomVariableValue", cv1)
        wrapper.invoke(onoff, "SetAttribute", "OnTime", rand1)

        # onoff.SetAttribute ("OffTime", RandomVariableValue (ConstantVariable (0.0)));
        cv2 = wrapper.create("ConstantVariable", 0.0)
        rand2 = wrapper.create("RandomVariableValue", cv2)
        wrapper.invoke(onoff, "SetAttribute", "OffTime", rand2)

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

        def SinkRx(packet, address):
            print packet

        def PingRtt(context, rtt):
            print context, rtt

        ### configure tracing
        #csma.EnablePcapAll ("csma-ping", false);
        wrapper.invoke(csma, "EnablePcapAll", "csma-ping", False)
       
        # No binging for callback
        #Config::ConnectWithoutContext ("/NodeList/3/ApplicationList/0/$ns3::PacketSink/Rx", 
        # MakeCallback (&SinkRx));
        #cb = wrapper.create("MakeCallback", SinkRx)
        #wrapper.invoke(config, "ConnectWithoutContext", 
        #        "/NodeList/3/ApplicationList/0/$ns3::PacketSink/Rx", cb)

        # Config::Connect ("/NodeList/*/ApplicationList/*/$ns3::V4Ping/Rtt", 
        # MakeCallback (&PingRtt));
        #cb2 = wrapper.create("MakeCallback", PingRtt)
        #wrapper.invoke(config, "ConnectWithoutContext", 
        #        "/NodeList/*/ApplicationList/*/$ns3::V4Ping/Rtt", 
        #        cb2)

        # Packet::EnablePrinting ();
        packet = wrapper.singleton("Packet")
        wrapper.invoke(packet, "EnablePrinting")

        ### run Simulation
        # Simulator::Run ();
        simulator = wrapper.singleton("Simulator")
        wrapper.invoke(simulator, "Run")

        # Simulator::Destroy ();
        wrapper.invoke(simulator, "Destroy")

if __name__ == '__main__':
    unittest.main()

