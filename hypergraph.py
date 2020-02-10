import networkx as nx
import re
import pprint
import itertools

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'



class HyperGraph(object):
    def __init__(self):
        self.V = set()
        self.E = list()
        self.edge_dict = dict()

    def copy(self):
        h = HyperGraph()
        for en, e in self.edge_dict.items():
            h.add_edge(e, name=en)
        return h

    def join_copy(self, x, y):
        """Copy of self with vertices x and y joined"""
        h = HyperGraph()
        for en, e in self.edge_dict.items():
            e2 = e.copy()
            if y in e2:
                e2.remove(y)
                e2.add(x)
            h.add_edge(e2, name=en)
        return h

    def toHyperbench(self):
        s = []
        for en, e in self.edge_dict.items():
            s.append('{}({}),'.format(en, ','.join(e)))
        return '\n'.join(s)

    def vertex_induced_subg(self, U):
        """Induced by vertex set U"""
        h = HyperGraph()
        for en, e in self.edge_dict.items():
            e2 = e.copy()
            e2 = e2 & U
            if e2 != set():
                h.add_edge(e2, name=en)
        return h

    def fromHyperbench(fname):
        EDGE_RE = re.compile('\s*([\w:]+)\s?\(([^\)]*)\)')
        def split_to_edge_statements(s):
            x = re.compile('\w+\s*\([^\)]+\)')
            return list(x.findall(s))

        def cleanup_lines(rl):
            a = map(str.rstrip, rl)
            b = filter(lambda x: not x.startswith('%') and len(x) > 0, a)
            return split_to_edge_statements(''.join(b))

        def line_to_edge(l):
            m = EDGE_RE.match(l)
            name = m.group(1)
            e = m.group(2).split(',')
            e = set(map(str.strip, e))
            return name, e            

        with open(fname) as f:
            raw_lines = f.readlines()
        lines = cleanup_lines(raw_lines)

        hg = HyperGraph()
        for l in lines:
            edge_name, edge = line_to_edge(l)
            hg.add_edge(edge, edge_name)
        return hg

    def add_edge(self, edge, name):
        assert(type(edge) == set)
        self.edge_dict[name] = edge
        self.V.update(edge)
        self.E.append(edge)

    def add_special_edge(self, sp):
        SPECIAL_NAME = 'Special'
        # find a name first
        sp_name = None
        for i in itertools.count():
            candidate = SPECIAL_NAME + str(i)
            if candidate not in self.edge_dict:
                sp_name = candidate
                break
        self.add_edge(sp, sp_name)

    def remove_edge(self, name):
        e = self.edge_dict[name]
        del self.edge_dict[name]
        self.E.remove(e)

    def primal_nx(self):
        G = nx.Graph()
        G.add_nodes_from(self.V)
        for i, e in enumerate(self.E):
            for a, b in itertools.combinations(e, 2):
                G.add_edge(a, b)
        return G

    def incidence_nx(self, without=[]):
        G = nx.Graph()
        G.add_nodes_from(self.V)
        G.add_nodes_from(self.edge_dict.keys())
        for n, e in self.edge_dict.items():
            if n in without:
                continue
            for v in e:
                G.add_edge(n, v)
        return G

    def toPACE(self, special=[]):
        buf = list()
        vertex2int = {v: str(i) for i, v in enumerate(self.V, start=1)}
        buf.append('p htd {} {}'.format(len(self.V),
                                        len(self.E)))
        for i, ei in enumerate(self.edge_dict.items(), start=1):
            en, e = ei
            edgestr = ' '.join(map(lambda v: vertex2int[v], e))
            line = '{} {}'.format(i, edgestr)
            buf.append(line)

        if special is None:
            special = []
        for sp in special:
            if sp is None:
                continue
            edgestr = ' '.join(map(lambda v: vertex2int[v], sp))
            buf.append('s ' + edgestr)
        return '\n'.join(buf)

    def separate(self, sep):
        """Returns list of components"""
        primal = self.primal_nx()
        primal.remove_nodes_from(sep)
        comp_vertices = nx.connected_components(primal)
        comps = [self.vertex_induced_subg(U)
                 for U in comp_vertices]
        return comps

    def __repr__(self):
        return bcolors.WARNING +  'HG: {}'.format(pprint.pformat(self.edge_dict))+ bcolors.ENDC
