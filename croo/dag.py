#!/usr/bin/env python3
"""Directed Acylic Graph with custom hash function
You can use a non-hashable node with immutables (e.g. dict).
A DAG can be converted into Graphviz's DOT format.

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import copy

from caper.dict_tool import dict_to_dot_str


class DAG(object):
    """Directed acyclic graph with a custom hash function.

    Args:
        fnc_is_parent(n1, n2):
            function to check if n1 is a parent of n2.
        fnc_hash (optional):
            hash function to hash a node.
            this is useful when a node has a mutable object
                so that node itself is not hashable
        nodes (optional):
            list of nodes to be added to graph.

    Member variables:
        self._nodes:
            { h: n } where h = hash of a node.
        self._parents:
            { h: set([h_parent1, h_parent2, ...]) } where h = hash of a node.
        self._children:
            { h: set([h_parent1, h_parent2, ...]) } where h = hash of a node.
    """

    def __init__(self, fnc_is_parent, fnc_hash=None, nodes=None):
        self._fnc_is_parent = fnc_is_parent
        self._fnc_hash = fnc_hash
        self._nodes = {}
        self._parents = {}
        self._children = {}
        if nodes is not None:
            for n in nodes:
                self.add_node(n)

    @classmethod
    def from_dag(cls, dag):
        """Copy constructor for DAG.
        """
        return cls(
            is_parent=dag._is_parent,
            fnc_hash=dag._fnc_hash,
            nodes=copy.copy(dag._nodes),
        )

    def __str__(self):
        """to String.
        """
        result = '=== all nodes ===\n'
        for h, v in self._nodes.items():
            result += '{}: {}\n'.format(h, v)

        result += '\n=== parents ===\n'
        for h, v in self._parents.items():
            result += '{}: {}\n'.format(h, v)
            for i, h_ in enumerate(v):
                result += '\t{}: {}\n'.format(i, h_)

        result += '\n=== children ===\n'
        for h, v in self._children.items():
            result += '{}: {}\n'.format(h, v)
            for i, h_ in enumerate(v):
                result += '\t{}: {}\n'.format(i, h_)

        return result

    def to_dot(self, fnc_node_format, fnc_href=None, fnc_subgraph=None, template=None):
        """Converts a DAG into a Graphviz dot string.
        IMPORTANT: ONLY FORMATTED NODES WILL BE SHOWN IN THE GRAPH.

        Args:
            fnc_node_format(n):
                should starts with "[" and endswith "]"
                A single-parameter function to find a format for a node "n".
                e.g. "[shape=box, stype=filled, color=blue, label="hello"]"
            fnc_href(n) (optional):
                A single-parameter function to find a URL for a node "n".
                e.g. "http://some.where.com/rep1.bam"
                A node will not be linked if it returns None
            fnc_subgraph(n) (optional):
                A single-parameter function to find a subgraph name for a node "n".
                A node will not be associated with a subgraph if it returns None
            template (optional):
                A dict for a dot template. Useful to define a format of the whole graph.
                e.g. { "rankdir": "LR", ... }.
                key/val will be simply turned into key = val.
                If val is None then key alone without " = ".
                Refer to the function caper.dict_tool.dict_to_dot_str for details

        This function does the followings:
        1) Make a fixed dot template "digraph D {}" first
        2) Add key/val in a dict "template" to the graph D (as key = val).
        3) Find each node's format by a function "fnc_node_format".
           Only nodes with defined format will be shown in the graph, others will be hidden.
        4) Make links (edges) in a global scope of graph D.
        5) Put a node into a subgraph as defined by a function "fnc_subgraph"

        For example,
            fnc_node_format = lambda n: '[shape=box label={}]'.format(n['label']) if 'label' in n else None
            fnc_subgraph = lambda n: n['group'] if 'group' in n else None
            template = {
                "rankdir": "LR",
                "a1 [shape=box]" : None,
                "subgraph cluster_group_a" : {
                    "style": filled,
                    "color": lightgrey
                }
            }

        Then the result is:
            digraph D {
                rankdir = LR;
                a1 [shape=box];
                subgraph cluster_group_a {
                    style = filled;
                    color = lightgrey;
                    a1;
                    a2;
                }
                subgraph cluster_group_b {
                    b1;
                    b2;
                }
                a0 -> a1 -> b1 -> b2;
            }
        """
        d = copy.deepcopy(template) if template is not None else {}

        formatted_nodes = []
        for h, n in self._nodes.items():
            # wrap hash string
            quoted_h = '"' + str(h) + '"'
            format = fnc_node_format(n)
            if format is not None:
                if fnc_subgraph is not None:
                    subgraph = fnc_subgraph(n)
                    if subgraph is not None:
                        if not subgraph.startswith('subgraph '):
                            subgraph = 'subgraph ' + subgraph
                        if subgraph not in d:
                            d[subgraph] = {}
                        d[subgraph][quoted_h] = None
                if fnc_href is not None:
                    href = fnc_href(n)
                    if href is not None:
                        format = format.rstrip(
                            ']'
                        ) + ' href="{url}" target="blank" tooltip="{url}"]'.format(
                            url=href
                        )
                formatted_nodes.append((h, format))

        for h, format in formatted_nodes:
            quoted_h = '"' + str(h) + '"'
            d['{k} {v}'.format(k=quoted_h, v=format)] = None

        # scan from root to leaf to find children
        # among candidates in formatted_nodes only

        def deepfind_child(h, candidates, depth=0):
            """DFS to find any close children in candidates.
            This doesn't visit the same branch if a child is found
            but still visits other branches to find other close children
            """
            result = []
            if h not in self._children:
                return result
            for h_child in self._children[h]:
                if h_child in candidates:
                    result.append(h_child)
                else:
                    result.extend(deepfind_child(h_child, candidates))
            return result

        # construct a parent-to-child map within formatted_nodes
        for h, format in formatted_nodes:
            quoted_h = '"' + str(h) + '"'
            children = deepfind_child(h, [i for i, _ in formatted_nodes])
            for h_child in children:
                quoted_h_child = '"' + str(h_child) + '"'
                d['{h1} -> {h2}'.format(h1=quoted_h, h2=quoted_h_child)] = None

        return dict_to_dot_str(d)

    def hash_node(self, n):
        if self._fnc_hash is None:
            return hash(n)
        else:
            return self._fnc_hash(n)

    def find_nodes(self, fnc_cond):
        """Find a list of nodes by matching condition function.

        Returns:
            [(h, n)] where h is a hash of a matched node n
        """
        result = []
        for h, n in self._nodes.items():
            if fnc_cond(n):
                result.append((h, n))
        return result

    def get_nodes(self):
        """Get a list of all nodes

        Returns:
            [(h, n)] where h is a hash of a matched node n
        """
        return self._nodes.items()

    def rm_node(self, h, recursive=False):
        """Remove a node based on hash.

        Args:
            h: hash of a node.
            recursive: remove all children nodes recursively.
        """
        self._nodes.pop(h, None)
        self._parents.pop(h, None)
        self._children.pop(h, None)
        for _, v in self._parents.items():
            if h in v:
                v.remove(h)
        for _, v in self._children.items():
            if h in v:
                v.remove(h)

    def add_node(self, n):
        """Add a node to graph.
        """
        # get hash
        h = self.hash_node(n)

        if h in self._nodes:
            # remove all links to n in parents graph
            for h_ in self._parents:
                if h == h_:
                    continue
                parents = self._parents[h_]
                if h in parents:
                    parents.remove(h)
            # remove all links to n in children graph
            for h_ in self._children:
                if h == h_:
                    continue
                children = self._children[h_]
                if h in children:
                    children.remove(h)

        self._parents[h] = set()
        self._children[h] = set()
        self._nodes[h] = n

        # update links in graph
        for h_ in self._nodes:
            if h == h_:
                continue
            n_ = self._nodes[h_]
            p = self._fnc_is_parent(n, n_)
            p_ = self._fnc_is_parent(n_, n)
            if p and p_:
                raise ValueError('Detected a cyclic link in DAG.')
            elif p:
                self._parents[h_].add(h)
                self._children[h].add(h_)
            elif p_:
                self._parents[h].add(h_)
                self._children[h_].add(h)
