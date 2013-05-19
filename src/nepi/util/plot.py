import networkx
import tempfile

class Plotter(object):
    def __init__(self, box):
        self._graph = networkx.Graph(graph = dict(overlap = "false"))

        traversed = set()
        self._traverse_boxes(traversed, box)

    def _traverse_boxes(self, traversed, box):
        traversed.add(box.guid)

        self._graph.add_node(box.label, 
                width = 50/72.0, # 1 inch = 72 points
                height = 50/72.0, 
                shape = "circle")

        for b in box.connections:
            self._graph.add_edge(box.label, b.label)
            if b.guid not in traversed:
                self._traverse_boxes(traversed, b)

    def plot(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        networkx.draw_graphviz(self._graph)
        networkx.write_dot(self._graph, f.name)
        f.close()
        return f.name

