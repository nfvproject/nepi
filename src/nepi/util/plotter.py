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

import networkx
import os

class PFormats:
    DOT = "dot"
    FIGURE = "figure"

class ECPlotter(object):
    def plot(self, ec, fpath = None, format= PFormats.FIGURE, persist = False):
        graph, labels = self._ec2graph(ec)

        add_extension = False

        if persist and not fpath:
            import tempfile
            dirpath = tempfile.mkdtemp()
            fpath = os.path.join(dirpath, "%s_%s" % (ec.exp_id, ec.run_id)) 
            add_extension = True

        if format == PFormats.FIGURE:
            import matplotlib.pyplot as plt
            pos = networkx.graphviz_layout(graph, prog="neato")
            networkx.draw(graph, pos = pos, node_color="white", 
                    node_size = 500, with_labels=True)
           
            label = "\n".join(map(lambda v: "%s: %s" % (v[0], v[1]), labels.iteritems()))
            plt.annotate(label, xy=(0.0, 0.95), xycoords='axes fraction')
            
            if persist:
                if add_extension:
                    fpath += ".png"

                plt.savefig(fpath, bbox_inches="tight")
            else:
                plt.show()

        elif format == PFormats.DOT:
            if persist:
                if add_extension:
                    fpath += ".dot"

                networkx.write_dot(graph, fpath)
            else:
                import subprocess
                subprocess.call(["dot", "-Tps", fpath, "-o", "%s.ps" % fpath])
                subprocess.call(["evince","%s.ps" % fpath])
        
        return fpath

    def _ec2graph(self, ec):
        graph = networkx.Graph(graph = dict(overlap = "false"))

        labels = dict()
        connections = set()

        for guid, rm in ec._resources.iteritems():
            label = rm.get_rtype()

            graph.add_node(guid,
                label = "%d %s" % (guid, label),
                width = 50/72.0, # 1 inch = 72 points
                height = 50/72.0, 
                shape = "circle")

            labels[guid] = label

            for guid2 in rm.connections:
                # Avoid adding a same connection twice
                if (guid2, guid) not in connections:
                    connections.add((guid, guid2))

        for (guid1, guid2) in connections:
            graph.add_edge(guid1, guid2)

        return graph, labels
