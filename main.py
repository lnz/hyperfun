from cmd import Cmd
from hypergraph import HyperGraph
from functools import reduce
import sys
import glob
import pprint
import networkx as nx
import coolname
import readline
readline.set_completer_delims(' \t\n')  # for proper filename completion

INITIAL_HG_NAME = 'init'


class State:
    def __init__(self):
        self.hg = None
        self.current_component = None
        self.components = dict()
        self.component_counter = 1
        self.history = []  # maybe change to real stack

    def ready(self):
        return self.hg is not None

    def _cool_new_name(self):
        def gen_name():
            return '{}-{}'.format(self.current_component,
                                  coolname.generate()[0])
        new_name = gen_name()
        while new_name in self.components:
            new_name = gen_name()
        return new_name

    def make_grid(self, n, m):
        hg = HyperGraph.grid(n, m)
        self.hg = hg
        self.components[INITIAL_HG_NAME] = hg
        self.current_component = INITIAL_HG_NAME

    def load_initial(self, path):
        hg = HyperGraph.fromHyperbench(path)
        self.hg = hg
        self.components[INITIAL_HG_NAME] = hg
        self.current_component = INITIAL_HG_NAME

    def separate(self, sep, add_special):
        sep = set(sep)
        components = self.hg.separate(sep)
        newlist = list()
        for C in components:
            if add_special:
                C.add_special_edge(sep)

            name = 'C{:02d}'.format(self.component_counter)
            self.component_counter += 1

            self.components[name] = C
            newlist.append((name, C))
        return newlist

    def vertex_induced_subg(self, U, complement=False):
        if complement:
            U = set(self.hg.V) - U
        nhg = self.hg.vertex_induced_subg(U)
        new_name = self._cool_new_name()
        self.components[new_name] = nhg
        return new_name, nhg

    def edge_subg(self, edge_names):
        newhg = self.hg.edge_subg(edge_names)
        new_name = self._cool_new_name()
        self.components[new_name] = newhg

        # refactor this into general componenet adding method
        primal = newhg.primal_nx()
        if nx.number_connected_components(primal) > 1:
            print('WARNING: {} is not connected'.format(new_name))
        return new_name, newhg

    def introduce_join(self, x, y):
        newhg = self.hg.join_copy(x, y)
        new_name = '{}_{}={}'.format(self.current_component, x, y)
        if new_name in self.components:
            raise RuntimeError('This join already exists in state')
        self.components[new_name] = newhg
        return new_name, newhg

    def switch_to_comp(self, component_name, add_to_hist=True):
        if component_name == self.current_component:
            raise ValueError('Already at that componenet')
        if component_name not in self.components:
            raise ValueError('Invalid component')
        if add_to_hist:
            self.history.append(self.current_component)
        self.hg = self.components[component_name]
        self.current_component = component_name
        return self.current_component

    def pop_comp(self):
        if len(self.history) == 0:
            raise RuntimeError('History is empty')
        prev_component = self.history.pop()
        return self.switch_to_comp(prev_component,
                                   add_to_hist=False)

    def vertex_complete(self, start):
        if self.hg is None:
            return []
        return [v for v in self.hg.V if v.startswith(start)]

    def edge_complete(self, start):
        if self.hg is None:
            return []
        return [en for en in self.hg.edge_dict.keys() if en.startswith(start)]

    def component_completer(self, start):
        component_names = self.components.keys()
        return [n for n in component_names
                if n.startswith(start)]

    def __repr__(self):
        s = pprint.pformat(self.components)
        s += '\nActive: {}\n'.format(self.current_component)
        return s


class Prompt(Cmd):
    prompt = '福 '
    intro = 'Type ? for help'
    state = State()

    def _complete_vertices(self, text, line, begidx, endidx):
        try:
            return self.state.vertex_complete(text)
        except Exception as e:
            print('Error:', e)

    def _complete_edge(self, text, line, begidx, endidx):
        try:
            return self.state.edge_complete(text)
        except Exception as e:
            print('Error:', e)

    def _output_new_comps(self, components,
                          old_edge_num=None, special=False):
        """
        Outputs list of pairs (component_name, component_hg).
        If old_edge_num is set, output 1/2 - balancedness with respect to this number of edge for full graph.
        If special is True, correct for newly added special edges in balancedness computation.
        """
        balanced = True
        for cn, C in components:
            print('{}:'.format(cn))
            print(C)

            # balanced checks
            C_sz = len(C.E)
            if special:  # newly added edge doesn't count
                C_sz = C_sz - 1
            if old_edge_num is not None and C_sz > old_edge_num / 2:
                balanced = False
        if old_edge_num is not None:
            print('Balanced:', balanced)

    def do_exit(self, inp):
        sys.exit(0)

    def help_exit(self):
        print('Exit Hyperfun')
    do_EOF = do_exit
    help_EOF = help_exit

    def do_grid(self, inp):
        dim = inp.split()
        if len(dim) != 2:
            print('WARNING: dimensions given wrong')
            return
        if self.state.hg is not None:
            print('WARNING: already have hypergraph, ignoring until "reset"')
            return
        try:
            dim = list(map(int, dim))
            self.state.make_grid(dim[0], dim[1])
        except Exception as e:
            print('Error', e)

    def help_grid(self, inp):
        print('Create a <n> x <m> grid graph as the initial hyperraph.',
              '    grid <n> <m>',
              sep='\n')

    def do_load(self, inp):
        if self.state.hg is not None:
            print('WARNING: already have hypergraph, ignoring until "reset"')
            return
        try:
            self.state.load_initial(inp)
        except Exception as e:
            print('Error loading file:', e)

    def complete_load(self, text, line, begidx, endidx):
        globstr = '{}*'.format(text)
        return list(glob.glob(globstr))

    def help_load(self):
        print('Load a hypergraph in HyperBench format: load <path>')

    def do_save(self, inp):
        params = inp.split()
        if len(params) < 1 or len(params) > 2:
            print('WARNING: invalid usage, see help')
            return
        path = params[0]
        fmt = params[1] if len(params) > 1 else 'hyperbench'
        fmt = fmt.lower()

        if self.state.hg is None:
            print('WARNING: no hypergraph active')
            return
        try:
            if fmt == 'hyperbench':
                s = self.state.hg.toHyperbench()
            elif fmt == 'sc':
                s = self.state.hg.toVisualSC()
            elif fmt == 'pace':
                s = self.state.hg.toPACE()
            else:
                print('WARNING: invalid format chosen, see help')
                return
            with open(path, 'w') as f:
                print(s, file=f)
        except Exception as e:
            print('Error', e)

    def help_save(self):
        print('Save the active hypergraph in chosen format (hyperbench (default), sc): save <path> [<format>]')

    def do_separate(self, inp):
        sep = inp.split()
        new_comps = self.state.separate(sep, False)
        self._output_new_comps(new_comps, len(self.state.hg.E))
    complete_separate = _complete_vertices

    def help_separate(self):
        print('Separate by vertices: separate/sep <list of vertices> ')

    def do_special(self, inp):
        sep = inp.split()
        new_comps = self.state.separate(sep, True)
        self._output_new_comps(new_comps, old_edge_num=len(self.state.hg.E),
                               special=True)
    complete_special = complete_separate

    def help_special(self):
        print('Separate and add separator as special edge to new componenets.')

    def do_comp(self, inp):
        try:
            now = self.state.switch_to_comp(inp)
            print('Using component', now)
        except Exception as e:
            print('Error:', e)

    def complete_comp(self, text, line, begidx, endidx):
        return self.state.component_completer(text)

    def help_comp(self):
        print('Switch to <comp> as the active hypergraph: comp <comp>')

    def do_pop(self, _inp):
        try:
            now = self.state.pop_comp()
            print('Using component', now)
        except Exception as e:
            print('Error', e)

    def help_pop(self):
        print('Go back to last hypergraph in history.')

    def do_hist(self, _inp):
        pprint.pprint(self.state.history)

    def help_hist(self):
        print('Show history of components, most recent at end.')

    def do_show(self, _inp):
        pprint.pprint(self.state.hg)

    def help_show(self):
        print('Show active hypergraph.')

    def do_findv(self, inp):
        if self.state.hg is None:
            print('No active hypergraph!')
            return
        hl_list = inp.split()
        print(self.state.hg.fancy_repr(hl=hl_list))
    complete_findv = _complete_vertices

    def help_findv(self):
        print('Highlight vertices in active hypergraph: findv <list of vertices>')

    def do_find_edge(self, inp):
        if self.state.hg is None:
            print('No active hypergraph!')
            return
        edge_names = inp.split()
        edges = [self.state.hg.edge_dict[en] for en in edge_names]
        hl_list = reduce(lambda a, b: a | b, edges)  # union over all edges
        print(self.state.hg.fancy_repr(hl=hl_list))
    complete_find_edge = _complete_edge

    def help_find_edge(self):
        print('Highlight all vertices incident to given edges: find_edge <list of edges>')

    def do_edge_subgraph(self, inp):
        if self.state.hg is None:
            print('No active hypergraph')
            return
        edge_names = inp.split()
        try:
            name, hg = self.state.edge_subg(edge_names)
            print(name)
            print(hg)
        except Exception as e:
            print('ERROR', e)
    complete_edge_subgraph = _complete_edge

    def help_edge_subgraph(self):
        print(
            "Creates subgraph that includes only the given edges.",
            "    edge_subgraph <list of edges>",
            "May fail if invalid edges are given.",
            sep='\n'
        )

    def do_join(self, inp):
        jv = inp.split()
        if len(jv) > 2:
            print('WARNING: takes exactly 2 attributes')
            return
        if not self.state.ready():
            print('WARNING: not ready')
            return
        try:
            name, hg = self.state.introduce_join(jv[0], jv[1])
            print(name)
            print(hg)
        except Exception as e:
            print('ERROR', e)

    complete_join = _complete_vertices

    def help_join(self):
        print(
            "Joins two vertices of the hypergraph into one.",
            "    join <x> <y>",
            "Vertex <y> becomes <x> in all edges. May introduce",
            "duplicate edges that are not automatically removed.",
            sep='\n'
        )

    def do_complement(self, inp):
        U = set(inp.split())
        r = self.state.vertex_induced_subg(U, complement=True)
        self._output_new_comps([r])

    def do_reset(self, _inp):
        self.state = State()

    def help_reset(self):
        print('Resets all state!')

    def do_state(self, _inp):
        pprint.pprint(self.state)

    def help_state(self):
        print('Show current state.')
    # Aliases
    do_sep = do_separate
    complete_sep = _complete_vertices
    help_sep = help_separate
    do_spec = do_special
    complete_spec = _complete_vertices
    help_spec = help_special


if __name__ == "__main__":
    Prompt().cmdloop()
