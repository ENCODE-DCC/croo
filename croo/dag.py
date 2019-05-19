#!/usr/bin/env python3
"""Directed Acylic Graph with custom hash function
so that You can use non-hashable type (e.g. dict) as a node

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import copy


class DAG(object):
    """Directed acyclic graph with custom hash function.

    Args:
        fnc_is_parent(n1, n2):
            function to check if n1 is a parent of n2.
        fnc_hash:
            hash function to hash a node (which can be a mutable like a dict)
        nodes:
            list of nodes to be added to graph.

    Member variables:
        self._nodes:
            { h: n } where h = hash of a node.
        self._parents:
            { h: set([h_parent1, h_parent2, ...]) } where h = hash of a node.
        self._children:
            { h: set([h_parent1, h_parent2, ...]) } where h = hash of a node.
    """
    def __init__(self, fnc_is_parent, fnc_hash, nodes=None):
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
        return cls(is_parent=dag._is_parent, fnc_hash=dag._fnc_hash,
                   nodes=copy.copy(dag._nodes))

    def __str__(self):
        """to String.
        """
        result = '=== all nodes ===\n'
        for h, v in self._nodes.items():
            result += '{}: {}\n'.format(h, v)

        result += '\n=== parents ===\n'
        for h, v in self._parents.items():
            result += '{}: {}\n'.format(h, v)
            for _, h_ in enumerate(v):
                result += '\t{}: {}\n'.format(h_)

        result += '\n=== children ===\n'
        for h, v in self._children.items():
            result += '{}: {}\n'.format(h, v)
            for _, h_ in enumerate(v):
                result += '\t{}: {}\n'.format(h_)

        return result

    def hash_node(self, n):
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
