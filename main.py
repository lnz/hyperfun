from cmd import Cmd
from hypergraph import HyperGraph
import sys
import glob
import pprint
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
        return [v for v in self.hg.V if v.startswith(start)]

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
        if self.state.hg is None:
            print('ERROR: no hypergraph active')
            return
        try:
            s = self.state.hg.toHyperbench()
            with open(inp, 'w') as f:
                print(s, file=f)
        except Exception as e:
            print('Error', e)

    def help_save(self):
        print('Save the active hypergraph in HyperBench format: save <path>')

    def do_separate(self, inp):
        sep = inp.split()
        new_comps = self.state.separate(sep, False)
        self._output_new_comps(new_comps, len(self.state.hg.E))

    def complete_separate(self, text, line, begidx, endidx):
        try:
            return self.state.vertex_complete(text)
        except Exception as e:
            print('Error:', e)

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

    def do_state(self, _inp):
        pprint.pprint(self.state)

    def help_state(self):
        print('Show current state.')
    # Aliases
    do_sep = do_separate
    complete_sep = complete_separate
    help_sep = help_separate
    do_spec = do_special
    complete_spec = complete_special
    help_spec = help_special


if __name__ == "__main__":
    Prompt().cmdloop()
