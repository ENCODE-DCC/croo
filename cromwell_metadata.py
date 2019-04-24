#!/usr/bin/env python3
# written by Jin Lee at ENCODE-DCC

import json
import hashlib
import os
import copy
import re
from collections import OrderedDict


class DAG(object):
    """Directed acyclic graph.

    Args:
        is_parent(n1, n2):
            function to check if n1 is a parent of n2.
        hash_keys:
            list of key names to be used for hashing a node.
            node must have those keys when added.
        nodes:
            list of nodes to be added to graph.

    Member variables:
        self.nodes:
            { h: node } where h = hash of a node.
        self.parents:
            { h: set([h_parent1, h_parent2, ...]) } where h = hash of a node.
        self.children:
            { h: set([h_parent1, h_parent2, ...]) } where h = hash of a node.
    """
    def __init__(self, is_parent, hash_keys=None, nodes=None):
        self.is_parent = is_parent
        self.hash_keys = hash_keys
        self.nodes = {}
        self.parents = {}
        self.children = {}
        if nodes is not None:
            for n in nodes:
                self.add_node(n)

    @classmethod
    def from_dag(cls, dag):
        """Copy constructor.
        """
        nodes = copy.deepcopy(list(dag.nodes.values()))
        return cls(
            is_parent=dag.is_parent,
            hash_keys=dag.hash_keys,
            nodes=nodes)

    def __str__(self):
        """to String.
        """
        result = '=== parents ===\n'
        for h, v in self.parents.items():
            result += '{}\n'.format(self.print_node(h))
            for _, h_ in enumerate(v):
                result += '\t{}\n'.format(self.print_node(h_))

        result += '\n=== children ===\n'
        for h, v in self.children.items():
            result += '{}\n'.format(self.print_node(h))
            for _, h_ in enumerate(v):
                result += '\t{}\n'.format(self.print_node(h_))

        return result

    def find_nodes(self, cond, debug=False):
        """Finds a list of nodes matching condition (dict).

        Args:
            cond: { key: val, ... }

        Returns:
            (h, n) where h is a hash string of a matched node n 
        """
        result = []
        for h, n in self.nodes.items():
            found = True
            for k, v in cond.items():
                if n[k]!=v:
                    found = False
                    break
            if found:
                result.append((h, n))
        return result

    def print_node(self, h, print_all=False):
        """Finds a node by hash string h and print it.

        Args:
            h: hash of a node
        """
        if print_all:
            return ', '.join(
                ['{}: {}'.format(k, v) for k, v in self.nodes.items()])
        else:
            return ', '.join(
                ['{}: {}'.format(k, self.nodes[h][k]) for k in dag.hash_keys])

    def rm_node(self, h, recursive=False):
        """Finds a node by hash string h and remove it from graph.

        Args:
            h: hash of a node.
            recursive: remove all children nodes recursively.
        """
        self.nodes.pop(h, None)
        self.parents.pop(h, None)
        self.children.pop(h, None)
        for _, v in self.parents.items():
            if h in v:
                v.remove(h)
        for _, v in self.children.items():
            if h in v:
                v.remove(h)

    def add_node(self, n):
        """Adds a node to graph.

        Args:
            n: any { } with hash_keys + other keys
        """
        # get hash
        h = self.hash_node(n)

        if h in self.nodes:
            # remove all links to n in parents graph
            for h_ in self.parents:
                if h == h_:
                    continue
                parents = self.parents[h_]
                if h in parents:
                    parents.remove(h)
            # remove all links to n in children graph
            for h_ in self.children:
                if h == h_:
                    continue
                children = self.children[h_]
                if h in children:
                    children.remove(h)

        self.parents[h] = set()
        self.children[h] = set()
        self.nodes[h] = n

        # update links in graph
        for h_ in self.nodes:
            if h == h_:
                continue
            n_ = self.nodes[h_]
            p = self.is_parent(n, n_)
            p_ = self.is_parent(n_, n)
            if p and p_:
                raise ValueError('Detected a cyclic link in DAG.')
            elif p:
                self.parents[h_].add(h)
                self.children[h].add(h_)
            elif p_:
                self.parents[h].add(h_)
                self.children[h_].add(h)

    def hash_node(self, n):
        """Hash (md5) a node based dumped string from dict with hash_keys only

        Args:
            n: any { } with hash_keys + other keys

        Returns:
            Hash string of a node n
        """
        n_ = {k: n[k] for k in self.hash_keys} if self.hash_keys else n
        return hashlib.md5(
            json.dumps(n_, sort_keys=True).encode('utf-8')).hexdigest()


class CromwellWorkflow(object):
    """Construct a cromwell workflow from metadata.json file
    """

    KEY_NAME_DAG = '_task_graph'  # key name for DAG in cromwell input JSON

    def __init__(self, cromwell_metadata_json_file, debug=False):
        self.__read_cromwell_metadata_json_file(cromwell_metadata_json_file)

        # construct an indexed DAG
        self.dag = DAG(
            is_parent = CromwellWorkflow.is_parent,
            hash_keys = ['task_name', 'shard_idx'])

        # read DAG from input_json if it exists
        if CromwellWorkflow.KEY_NAME_DAG in self.input_json:
            for n in self.input_json[CromwellWorkflow.KEY_NAME_DAG]:
                self.dag.add_node(n)

        # convert cromwell-calls into a task (node in DAG)        
        calls = self.metadata_json['calls']
        for task_name, call_list in calls.items():
            for _, c in enumerate(call_list):
                in_var_names = c['inputs'].keys()
                out_var_names = c['outputs'].keys()
                in_files = [v for k, v in c['inputs'].items()
                    if type(v) == str and (
                        CromwellWorkflow.is_uri(v) or os.path.exists(v))]
                out_files = [v for k, v in c['outputs'].items()
                    if type(v) == str and (
                        CromwellWorkflow.is_uri(v) or os.path.exists(v))]
                t = {
                    'task_name': task_name,
                    'shard_idx': c['shardIndex'],
                    'workflow_id': self.workflow_id,
                    'status': c['executionStatus'],
                    'in_files': in_files,
                    'out_files': out_files,
                    'in_var_names' : in_var_names,
                    'out_var_names' : out_var_names,
                    'start_date': None,
                    'end_data': None,
                }
                self.dag.add_node(t)

        if debug:
            print(self.dag)

    def __read_cromwell_metadata_json_file(self, cromwell_metadata_json_file):
        with open(cromwell_metadata_json_file, 'r') as f:
            self.metadata_json = json.load(f)
        self.input_json = json.loads(
            self.metadata_json['submittedFiles']['inputs'],
            object_pairs_hook=OrderedDict)
        self.workflow_id = \
            self.metadata_json['labels']['cromwell-workflow-id'].replace(
                'cromwell-', '')

    @staticmethod
    def is_uri(s):
        """Checks if a given URI (s) is compatible with cromwell
        """
        # not yet supported: 'http://', 'https://'
        return s.startswith(('gs://', 'dx://'))

    @staticmethod
    def is_parent(t1, t2):
        """Checks if task t1 is a parent of task n2.        
        Finds parent task by the intersection of child's in_files
        and parent's out_files. Checks link between two call objects.

        Args:
            t1: task 1
            t2: task 2

        Returns:
            Boolean that checks if t1 is a parent of t2.
        """
        return set(t1['out_files']) & set(t2['in_files'])


class CromwellWorkflowRestart(CromwellWorkflow):
    """Creates an input JSON to restart a failed/successful workflow from
        1) where it left off if user doesn't specify a point of restarting in
            restart_def_json_file.            
        2) a point of restarting specified by a user. a point of restarting can
            guessed from link between input variables and tasks defined in
             input_def_json_file.

    Args:
        cromwell_metadata_json_file:
            See details in parent class.

        input_def_json_file:
            JSON file with mappings (WDL File input -> WDL task's output or input).

        restart_def_json_file:
            JSON file with WDL File input to restart a pipeline with.
    """
    def __init__(self,
        cromwell_metadata_json_file,
        input_def_json_file=None,
        restart_def_json_file=None,
        debug=False):

        super(CromwellWorkflowRestart, self).__init__(
            cromwell_metadata_json_file, debug=debug)

        # let's make a deep copy of original DAG constructed from cromwell metadata.json
        # this new DAG will be pruned to generate a new input JSON to restart a pipeline.
        # a link between task and input variable can be guessed from input_def_json_file.
        # then it will recursively remove all children tasks from a restarting point
        # specified by users. such point is defined in restart_def_json_file.
        self.dag_restart = DAG(self.dag)

        # parse JSON files
        self.__parse_input_def_json_file(input_def_json_file)
        self.__parse_restart_def_json_file(restart_def_json_file)

    def __parse_input_def_json_file(self, input_def_json_file):
        """Parse a JSON file to read mappings of workflow input to 
        to WDL task's output (or input for the first task in a workflow).

        It's not recommended to map workflow input to task's input because task's input can come
        from multiple tasks. Therefore, use it for the first task in a workflow only.

        In the following example of ATAC-Seq pipeline,

        Example:
        {
            "atac.fastqs_rep1_R1" : "atac.trim_adapter[0].fastqs_R1",
            "atac.fastqs_rep1_R2" : "atac.trim_adapter[0].fastqs_R2",
            "atac.fastqs_rep2_R1" : "atac.trim_adapter[1].fastqs_R1",
            "atac.fastqs_rep2_R2" : "atac.trim_adapter[1].fastqs_R2"
            "atac.trim_merged_fastqs_R1[i]" : "atac.trim_adapter[i].trim_merged_fastqs_R1",
            "atac.trim_merged_fastqs_R2[i]" : "atac.trim_adapter[i].trim_merged_fastqs_R2",    
            "atac.bams[i]" : "atac.bowtie2[i].bam"
        }
        """
        self._map_wf_input_to_task_output = {}        

        if input_def_json_file is None:
            return

        with open(input_def_json_file, 'r') as f:
            input_def_json = json.load(f)

        for k, v in input_def_json.items():
            in_var = k.strip()                
            task_name, task_out_var = v.strip().rsplit('.', 1)
            
            # task name can have a C-style array expression [int].
            # e.g. "WF_NAME.TASK_NAME[SHARD_IDX].OUT_VAR_NAME"
            arr = task_name.strip(']').split('[')
            if len(arr)==1:
                task_name, shard_idx = arr[0], -1
            elif len(arr)==2:                
                task_name, shard_idx = arr[0], arr[1]
                if shard_idx = 'i':
                    shard_idx = -2 # use -2 for scattered tasks, -1 for non-scattered tasks
                else:
                    shard_idx = int(shard_idx)
            else:
                ValueError('Incorrect format for task name in input_def_json.')
                        
            if shard_idx is not None:
                nodes = self.dag.find_nodes({"task_name": task_name, "shard_idx": shard_idx})
                assert(len(nodes)==1)
            else:
                nodes = self.dag.find_nodes({"task_name": task_name} )

            if len(nodes)==1:
                # find again by (task_name, )
            for n in self.dag.find_nodes( {"task_name" : task_name} ):


            # hash task to find a node in DAG
            h = self.dag.hash_node({
                "task_name" : task_name,
                "shard_idx" : shard_idx
            })
            print(task_name, shard_idx)
            print(h)
            print(n)
            print(list(self.dag.nodes))
            assert(h in self.dag.nodes)

            self._map_wf_input_to_task_output[in_var] = {
                "task_name" : task_name,
                "shard_idx" : shard_idx,
                "in_var_name" : task_out_var
                    if task_out_var in self.dag.nodes[h]['in_var_names'] else None,
                "out_var_name" : task_out_var
                    if task_out_var in self.dag.nodes[h]['out_var_names'] else None
            }

    def __parse_restart_def_json_file(self, restart_def_json_file):
        """Parse a JSON file.

        Example:
        {
            "atac.nodup_bams[2]" : "rep3.raw.bam",
            "atac.bams[0]" : "rep1.raw.bam",
            "atac.tas" : [null, "rep2.tagAlign.gz", null]
        }
        """
        self._inputs = {}

        if restart_def_json_file is None:
            return

        with open(restart_def_json_file, 'r') as f:
            restart_def_json = json.load(f)

        for k, v in restart_def_json.items():
            # input var name can have C-style array expression [int].
            # also dict value can be an array. see above example.
            arr = k.strip(']').split('[')
            if len(arr)==1:
                if type(v)==list:
                    raise NotImplemented()
                else:
                    in_var, shard_idx = arr[0], -1 # -1 for non-scattered task
            elif len(arr)==2:
                in_var, shard_idx = arr[0], int(arr[1])
            else:
                raise ValueError('Incorrect format for task name in input_def_json.')


def main():
    m_json_file = '/users/leepc12/code/atac-seq-pipeline/metadata.json'
    input_def_json_file = '/users/leepc12/code/dev_cromwell_metadata_parser/example_input_def.json'
    restart_def_json_file = '/users/leepc12/code/dev_cromwell_metadata_parser/example_restart_def.json'

    wf_restart = CromwellWorkflowRestart(m_json_file,
        input_def_json_file,
        restart_def_json_file,
        debug=False)


if __name__ == '__main__':
    main()
