#!/usr/bin/env python

from nepi.design import create_provider
import unittest

class NS3DesignBoxesTestCase(unittest.TestCase):
    def test_design(self):
        provider = create_provider()
        exp = provider.create("Experiment")
        simu = provider.create("ns3::Simulation", container = exp)

        node1 = provider.create("ns3::Node", container = simu)
        ipv41 = provider.create("ns3::Ipv4L3Protocol", container = simu)
        arp1 = provider.create("ns3::ArpL3Protocol", container = simu)
        icmp1 = provider.create("ns3::Icmpv4L3Protocol", container = simu)
        udp1 = provider.create("ns3::UdpL4Protocol", container = simu)
        node1.c.protos.connect(ipv41.c.node)
        node1.c.protos.connect(arp1.c.node)
        node1.c.protos.connect(icmp1.c.node)
        node1.c.protos.connect(udp1.c.node)
        iface1 = provider.create("ns3::PointToPointNetDevice", container = simu)
        queue1 = provider.create("ns3::DropTailQueue", container = simu)
        node1.c.devs.connect(iface1.c.node)
        iface1.c.queue.connect(queue1.c.dev)
        trace1 = provider.create("ns3::PcapTrace", container = simu)
        iface1.c.traces.connect(trace1.c.dev)
        ip1 = provider.create("ns3::PcapTrace", container = simu)
        iface1.c.addrs.connect(ip1.c.dev)
        
        node2 = provider.create("ns3::Node", container = simu)
        ipv42 = provider.create("ns3::Ipv4L3Protocol", container = simu)
        arp2 = provider.create("ns3::ArpL3Protocol", container = simu)
        icmp2 = provider.create("ns3::Icmpv4L3Protocol", container = simu)
        udp2 = provider.create("ns3::UdpL4Protocol", container = simu)
        node2.c.protos.connect(ipv42.c.node)
        node2.c.protos.connect(arp2.c.node)
        node2.c.protos.connect(icmp2.c.node)
        node2.c.protos.connect(udp2.c.node)
        iface2 = provider.create("ns3::PointToPointNetDevice", container = simu)
        queue2 = provider.create("ns3::DropTailQueue", container = simu)
        node2.c.devs.connect(iface2.c.node)
        iface2.c.queue.connect(queue2.c.dev)
        trace2 = provider.create("ns3::PcapTrace", container = simu)
        iface2.c.traces.connect(trace2.c.dev)
        ip2 = provider.create("ns3::PcapTrace", container = simu)
        iface2.c.addrs.connect(ip2.c.dev)

        chan = provider.create("ns3::PointToPointChannel", container = simu)
        iface1.c.chan.connect(chan.c.dev2)
        iface2.c.chan.connect(chan.c.dev2)

        app = provider.create("ns3::V4Ping", container = simu)
        app.a.Remote.value = "10.0.0.2"
        app.a.StartTime.value = "0s"
        app.a.StopTime.value = "20s"
        app.a.Verbose.value = False
        app.c.node.connect(node1.c.apps)

        xml = exp.xml
        exp2 = provider.from_xml(xml)
        xml2 = exp2.xml
        f = open('/tmp/xml1', 'w')
        f.write(xml)
        f.close()
        f = open('/tmp/xml2', 'w')
        f.write(xml2)
        f.close()
        self.assertTrue(xml == xml2)
        
if __name__ == '__main__':
    unittest.main()

