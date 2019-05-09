#!/usr/bin/env python3
"""CromwellMetadata parser.
Construct a task graph based on Cromwell's metadata.json

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import json
from dag import DAG
from collections import OrderedDict
from cromweller_uri import CromwellerURI


class CromwellMetadata(object):
    """Construct a task DAG based Cromwell's metadata.json file
    """
    TASK_TEMPLATE = {
        'task_name': None,  # WORKFLOW_NAME.TASK_NAME,
                            # WORKFLOW_NAME.SUBWORKFLOW_NAME.TASK_NAME
        'shard_idx': None,  # tuple of shard_idx for possible nested scatters
                            # due to subworkflows. -1 means no scatter
                            # e.g. (0,)    scatter id 0 in main workflow
                            # e.g. (-1, 1) no scatter in main workflow
                            #              scatter id 1 in sub workflow
        'status': None,  # status string (e.g. Running)
        'in_files': None,  # tuple of (var_name, file_path_or_uri)
        'out_files': None  # tuple of (var_name, file_path_or_uri)
    }

    def __init__(self, metadata_json, debug=False):
        self._metadata_json = metadata_json

        # input JSON
        self._input_json = json.loads(
            self._metadata_json['submittedFiles']['inputs'],
            object_pairs_hook=OrderedDict)

        # workflow ID
        self._workflow_id = self._metadata_json['id']

        # construct an indexed DAG
        self._dag = DAG(fnc_is_parent=CromwellMetadata.is_parent,
                        fnc_hash=CromwellMetadata.hash_task)
        # parse calls
        self.__parse_calls(self._metadata_json['calls'])

        self._debug = debug
        if self._debug:
            print(self._dag)

    def get_task_graph(self):
        return self._dag

    def __parse_calls(self, calls, parent_wf_name='', wf_alias=None, parent_wf_shard_idx=()):
        """Recursively parse calls in metadata JSON for subworkflow
        """
        for call_name, call_list in calls.items():
            for _, c in enumerate(call_list):
                shard_idx = c['shardIndex']
                status = c['executionStatus']
                if wf_alias is None:
                    wf_name = call_name.split('.')[0]
                else:
                    wf_name = wf_alias
                task_alias = call_name.split('.')[1]

                # if it is a subworkflow, then recursively dive into it 
                if 'subWorkflowMetadata' in c:
                    self.__parse_calls(
                        c['subWorkflowMetadata']['calls'],
                        parent_wf_name=parent_wf_name + wf_name + '.',
                        wf_alias=task_alias,
                        parent_wf_shard_idx=(shard_idx,))
                    continue

                in_files = [
                    (k, v) for k, v in c['inputs'].items()
                        if isinstance(v, str) \
                            and CromwellerURI(v).is_valid_uri()]
                out_files = [
                    (k, v) for k, v in c['outputs'].items()
                        if isinstance(v, str) \
                            and CromwellerURI(v).is_valid_uri()]
                t = {
                    'task_name': parent_wf_name + wf_name + '.' + task_alias,
                    'shard_idx': parent_wf_shard_idx + (shard_idx,),
                    'status': status,
                    'in_files': in_files,
                    'out_files': out_files
                }
                self._dag.add_node(t)


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
        return set([v for k, v in t1['out_files']]) \
                & set([v for k, v in t2['in_files']]) 

    @staticmethod
    def hash_task(t):
        """Special hash function for a task. Hash task_name and shard_idx only
        """
        return hash((t['task_name'], t['shard_idx']))


# class CromwellOutput(CromwellMetadata):
#     """Creates an input JSON to restart a failed/successful workflow from
#         1) where it left off if user doesn't specify a point of restarting in
#             restart_def_json_file.            
#         2) a point of restarting specified by a user. a point of restarting can
#             guessed from link between input variables and tasks defined in
#              input_def_json_file.

#     Args:
#         metadata_json:
#             See details in parent class.

#         input_def_json_file:
#             JSON file with mappings (WDL File input -> WDL task's output or input).

#         restart_def_json_file:
#             JSON file with WDL File input to restart a pipeline with.
#     """
#     def __init__(self, metadata_json, out_def_json=None, debug=False):

#         super(CromwellWorkflowRestart, self).__init__(
#             metadata_json, debug=debug)

#         # let's make a deep copy of original DAG constructed from cromwell metadata.json
#         # this new DAG will be pruned to generate a new input JSON to restart a pipeline.
#         # a link between task and input variable can be guessed from input_def_json_file.
#         # then it will recursively remove all children tasks from a restarting point
#         # specified by users. such point is defined in restart_def_json_file.
#         # self._dag_restart = DAG(self._dag)

#         # parse JSON files
#         self.__parse_out_def_json_file(out_def_json)
#         # self.__parse_restart_def_json_file(restart_def_json_file)

#     def __parse_out_def_json_file(self, input_def_json_file):
#         """Parse a JSON file to read mappings of workflow input to 
#         to WDL task's output (or input for the first task in a workflow).

#         It's not recommended to map workflow input to task's input because task's input can come
#         from multiple tasks. Therefore, use it for the first task in a workflow only.

#         In the following example of ATAC-Seq pipeline,

#         Example:
#         {
#             "atac.fastqs_rep1_R1" : "atac.trim_adapter[0].fastqs_R1",
#             "atac.fastqs_rep1_R2" : "atac.trim_adapter[0].fastqs_R2",
#             "atac.fastqs_rep2_R1" : "atac.trim_adapter[1].fastqs_R1",
#             "atac.fastqs_rep2_R2" : "atac.trim_adapter[1].fastqs_R2"
#             "atac.trim_merged_fastqs_R1[i]" : "atac.trim_adapter[i].trim_merged_fastqs_R1",
#             "atac.trim_merged_fastqs_R2[i]" : "atac.trim_adapter[i].trim_merged_fastqs_R2",    
#             "atac.bams[i]" : "atac.bowtie2[i].bam"
#         }
#         """
#         self._map_wf_input_to_task_output = {}        

#         if input_def_json_file is None:
#             return

#         with open(input_def_json_file, 'r') as f:
#             input_def_json = json.load(f)

#         for k, v in input_def_json.items():
#             in_var = k.strip()                
#             task_name, task_out_var = v.strip().rsplit('.', 1)
            
#             # task name can have a C-style array expression [int].
#             # e.g. "WF_NAME.TASK_NAME[SHARD_IDX].OUT_VAR_NAME"
#             arr = task_name.strip(']').split('[')
#             if len(arr)==1:
#                 task_name, shard_idx = arr[0], -1
#             elif len(arr)==2:                
#                 task_name, shard_idx = arr[0], arr[1]
#                 if shard_idx = 'i':
#                     shard_idx = -2 # use -2 for scattered tasks, -1 for non-scattered tasks
#                 else:
#                     shard_idx = int(shard_idx)
#             else:
#                 ValueError('Incorrect format for task name in input_def_json.')
                        
#             if shard_idx is not None:
#                 nodes = self._dag.find_nodes({"task_name": task_name, "shard_idx": shard_idx})
#                 assert(len(nodes)==1)
#             else:
#                 nodes = self._dag.find_nodes({"task_name": task_name} )

#             if len(nodes)==1:
#                 # find again by (task_name, )
#             for n in self._dag.find_nodes( {"task_name" : task_name} ):


#             # hash task to find a node in DAG
#             h = self._dag.hash_node({
#                 "task_name" : task_name,
#                 "shard_idx" : shard_idx
#             })
#             print(task_name, shard_idx)
#             print(h)
#             print(n)
#             print(list(self._dag.nodes))
#             assert(h in self._dag.nodes)

#             self._map_wf_input_to_task_output[in_var] = {
#                 "task_name" : task_name,
#                 "shard_idx" : shard_idx,
#                 "in_var_name" : task_out_var
#                     if task_out_var in self._dag.nodes[h]['in_var_names'] else None,
#                 "out_var_name" : task_out_var
#                     if task_out_var in self._dag.nodes[h]['out_var_names'] else None
#             }

#     # def __parse_restart_def_json_file(self, restart_def_json_file):
#     #     """Parse a JSON file.

#     #     Example:
#     #     {
#     #         "atac.nodup_bams[2]" : "rep3.raw.bam",
#     #         "atac.bams[0]" : "rep1.raw.bam",
#     #         "atac.tas" : [null, "rep2.tagAlign.gz", null]
#     #     }
#     #     """
#     #     self._inputs = {}

#     #     if restart_def_json_file is None:
#     #         return

#     #     with open(restart_def_json_file, 'r') as f:
#     #         restart_def_json = json.load(f)

#     #     for k, v in restart_def_json.items():
#     #         # input var name can have C-style array expression [int].
#     #         # also dict value can be an array. see above example.
#     #         arr = k.strip(']').split('[')
#     #         if len(arr)==1:
#     #             if type(v)==list:
#     #                 raise NotImplemented()
#     #             else:
#     #                 in_var, shard_idx = arr[0], -1 # -1 for non-scattered task
#     #         elif len(arr)==2:
#     #             in_var, shard_idx = arr[0], int(arr[1])
#     #         else:
#     #             raise ValueError('Incorrect format for task name in input_def_json.')


def main():
    import sys
    import os
    from cromweller_uri import init_cromweller_uri

    if len(sys.argv)<2:
        print('Usage: python cromwell_metadata.py [METADATA_JSON_FILE]')
        sys.exit(1)

    init_cromweller_uri(os.path.join(os.getcwd(), 'cromwell_metadata_tmp'))
    
    m_json_file = sys.argv[1]
    c = CromwellMetadata(m_json_file, debug=True)


if __name__ == '__main__':
    main()
