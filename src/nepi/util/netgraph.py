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

import ipaddr
import networkx
import random

class TopologyType:
    LINEAR = "linear"
    LADDER = "ladder"
    MESH = "mesh"
    TREE = "tree"
    STAR = "star"
    ADHOC = "adhoc"

## TODO: 
##      - AQ: Add support for hypergraphs (to be able to add hyper edges to 
##        model CSMA or wireless networks)

class NetGraph(object):
    """ NetGraph represents a network topology. 
    Network graphs are internally using the networkx library.

    """

    def __init__(self, *args, **kwargs):
        """ A graph can be generated using a specified pattern 
        (LADDER, MESH, TREE, etc), or provided as an argument.

            :param graph: Undirected graph to use as internal representation 
            :type graph: networkx.Graph

            :param topo_type: One of TopologyType.{LINEAR,LADDER,MESH,TREE,STAR}
            used to automatically generate the topology graph. 
            :type topo_type: TopologyType

            :param node_count: Number of nodes in the topology to be generated. 
            :type node_count: int

            :param branches: Number of branches (arms) for the STAR topology. 
            :type branches: int


            :param assign_ips: Automatically assign IP addresses to each node. 
            :type assign_ips: bool

            :param network: Base network segment for IP address assignment.
            :type network: str

            :param prefix: Base network prefix for IP address assignment.
            :type prefix: int

            :param version: IP version for IP address assignment.
            :type version: int


            :param assign_st: Select source and target nodes on the graph.
            :type assign_st: bool

        NOTE: Only point-to-point like network topologies are supported for now.
                (Wireless and Ethernet networks were several nodes share the same
                edge (hyperedge) can not be modeled for the moment).

        """
        self._graph = kwargs.get("graph") 
        self._topo_type = TopologyType.ADHOC

        if not self._graph and kwargs.get("topo_type") and \
                kwargs.get("node_count"):
            topo_type = kwargs["topo_type"]
            node_count = kwargs["node_count"]
            branches = kwargs.get("branches")

            self._topo_type = topo_type
            self._graph = self.generate_grap(topo_type, node_count, 
                    branches = branches)

        if kwargs.get("assign_ips"):
            network = kwargs.get("network", "10.0.0.0")
            prefix = kwargs.get("prefix", 8)
            version = kwargs.get("version", 4)

            self.assign_p2p_ips(self, network = network, prefix = prefix, 
                    version = version)

        if kwargs.get("assign_st"):
            self.select_target_zero()
            self.select_random_leaf_source()

    @property
    def graph(self):
        return self._graph

    @property
    def topo_type(self):
        return self._topo_type

    @property
    def order(self):
        return self.graph.order()

    @property
    def nodes(self):
        return self.graph.nodes()

    @property
    def edges(self):
        return self.graph.edges()

    def generate_graph(self, topo_type, node_count, branches = None):
        if topo_type == LADDER:
            total_nodes = node_count/2
            graph = networkx.ladder_graph(total_nodes)

        elif topo_type == LINEAR:
            graph = networkx.path_graph(node_count)

        elif topo_type == MESH:
            graph = networkx.complete_graph(node_count)

        elif topo_type == TREE:
            h = math.log(node_count + 1)/math.log(2) - 1
            graph = networkx.balanced_tree(2, h)

        elif topo_type == STAR:
            graph = networkx.Graph()
            graph.add_node(0)

            nodesinbranch = (node_count - 1)/ BRANCHES
            c = 1

            for i in xrange(BRANCHES):
                prev = 0
                for n in xrange(1, nodesinbranch + 1):
                    graph.add_node(c)
                    graph.add_edge(prev, c)
                    prev = c
                    c += 1

        # node ids are int, make them str
        g = networkx.Graph()
        g.add_nodes_from(map(lambda nid: NODES[str(nid)], 
            graph.nodes()))
        g.add_edges_from(map(lambda t: (NODES[str(t[0])], NODES[str(t[1])]), 
            graph.edges()))

        return g

    def add_node(self, nid):
        nid = str(nid)

        if nid not in self.graph:
            self.graph.add_node(nid)

    def add_edge(self, nid1, nid2):
        nid1 = str(nid1)
        nid2 = str(nid2)

        self.add_node(nid1)
        self.add_node( nid2)

        if nid1 not in self.graph[nid2]:
            self.graph.add_edge(nid2, nid1)

            # The weight of the edge is the delay of the link
            self.graph.edge[nid1][nid2]["weight"] = None
            # confidence interval of the mean RTT
            self.graph.edge[nid1][nid2]["weight_ci"] = None

    def assign_p2p_ips(self, network = "10.0.0.0", prefix = 8, version = 4):
        """ Assign IP addresses to each end of each edge of the network graph,
        computing all the point to point subnets and addresses in the network
        representation.

            :param network: Base network address used for subnetting. 
            :type network: str

            :param prefix: Prefix for the base network address used for subnetting.
            :type prefixt: int

            :param version: IP version (either 4 or 6).
            :type version: int

        """
        if len(networkx.connected_components(self.graph)) > 1:
            raise RuntimeError("Disconnected graph!!")

        # Assign IP addresses to host
        netblock = "%s/%d" % (network, prefix)
        if version == 4:
            net = ipaddr.IPv4Network(netblock)
            new_prefix = 31
        elif version == 6:
            net = ipaddr.IPv6Network(netblock)
            new_prefix = 31
        else:
            raise RuntimeError, "Invalid IP version %d" % version

        sub_itr = net.iter_subnets(new_prefix = new_prefix)

        for nid1, nid2 in self.graph.edges():
            #### Compute subnets for each link
            
            # get a subnet of base_add with prefix /30
            subnet = sub_itr.next()
            mask = subnet.netmask.exploded
            network = subnet.network.exploded
            prefixlen = subnet.prefixlen

            # get host addresses in that subnet
            i = subnet.iterhosts()
            addr1 = i.next()
            addr2 = i.next()

            ip1 = addr1.exploded
            ip2 = addr2.exploded
            self.graph.edge[nid1][nid2]["net"] = dict()
            self.graph.edge[nid1][nid2]["net"][nid1] = ip1
            self.graph.edge[nid1][nid2]["net"][nid2] = ip2
            self.graph.edge[nid1][nid2]["net"]["mask"] = mask
            self.graph.edge[nid1][nid2]["net"]["network"] = mask
            self.graph.edge[nid1][nid2]["net"]["prefix"] = prefixlen

    def get_p2p_info(self, nid1, nid2):
        net = self.graph.edge[nid1][nid2]["net"]
        return ( net[nid1], net[nid2], net["mask"], net["network"], 
                net["prefixlen"] )

    def set_source(self, nid):
        graph.node[nid]["source"] = True

    def set_target(self, nid):
        graph.node[nid]["target"] = True

    def targets(self):
        """ Returns the nodes that are targets """
        return [nid for nid in self.graph.nodes() \
                if self.graph.node[nid].get("target")]

    def sources(self):
        """ Returns the nodes that are sources """
        return [nid for nid in self.graph.nodes() \
                if self.graph.node[nid].get("sources")]

    def select_target_zero(self):
        """ Marks the node 0 as target
        """
        self.set_target("0")

    def select_random_leaf_source(self):
        """  Marks a random leaf node as source. 
        """

        # The ladder is a special case because is not symmetric.
        if self.topo_type == TopologyType.LADDER:
            total_nodes = self.order/2
            leaf1 = str(total_nodes - 1)
            leaf2 = str(nodes - 1)
            leaves = [leaf1, leaf2]
            source = leaves.pop(random.randint(0, len(leaves) - 1))
        else:
            # options must not be already sources or targets
            options = [ k for k,v in graph.degree().iteritems() \
                    if v == 1 and not graph.node[k].get("source") \
                        and not graph.node[k].get("target")]

            source = options.pop(random.randint(0, len(options) - 1))
        
        self.set_source(source)

