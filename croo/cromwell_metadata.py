#!/usr/bin/env python3
"""CromwellMetadata parser.
Construct a task graph based on Cromwell's metadata.json

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import re
import json
import caper
from caper.caper_uri import CaperURI
from collections import OrderedDict
from .dag import DAG


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

    RE_PATTERN_WDL_COMMENT_OUT_DEF_JSON = \
        r'^\s*\#\s*CROO\s+out_def\s(.+)'

    def __init__(self, metadata_json, debug=False):
        self._metadata_json = metadata_json

        # input JSON
        self._input_json = json.loads(
            self._metadata_json['submittedFiles']['inputs'],
            object_pairs_hook=OrderedDict)
        # WDL contents
        self._wdl_str = self._metadata_json['submittedFiles']['workflow']
        self._out_def_json_file = self.__find_out_def_from_wdl()
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

    def get_workflow_id(self):
        return self._workflow_id

    def get_task_graph(self):
        return self._dag

    def get_out_def_json_file(self):
        return self._out_def_json_file

    def __parse_calls(self, calls, parent_wf_name='',
                      wf_alias=None, parent_wf_shard_idx=()):
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

                def find_files_in_dict(d):
                    files = []
                    for k, v in d.items():
                        maybe_files = []
                        if isinstance(v, list):
                            for v_ in v:
                                if isinstance(v_, str):
                                    maybe_files.append(v_)
                        elif isinstance(v, dict):
                            for _, v_ in v.items():
                                if isinstance(v_, str):
                                    maybe_files.append(v_)
                        elif isinstance(v, str):
                            maybe_files.append(v)
                        for f in maybe_files:
                            if CaperURI(f).is_valid_uri():
                                files.append((k, f))
                    return files

                if 'inputs' in c:
                    in_files = find_files_in_dict(c['inputs'])
                else:
                    in_files = []

                if 'outputs' in c:
                    out_files = find_files_in_dict(c['outputs'])
                else:
                    out_files = []

                t = {
                    'task_name': parent_wf_name + wf_name + '.' + task_alias,
                    'shard_idx': parent_wf_shard_idx + (shard_idx,),
                    'status': status,
                    'in_files': in_files,
                    'out_files': out_files
                }
                self._dag.add_node(t)

    def __find_out_def_from_wdl(self):
        r = self.__find_val_from_wdl(
            CromwellMetadata.RE_PATTERN_WDL_COMMENT_OUT_DEF_JSON)
        return r[0] if len(r) > 0 else None

    def __find_val_from_wdl(self, regex_val):
        result = []
        for line in self._wdl_str.split('\n'):
            r = re.findall(regex_val, line)
            if len(r) > 0:
                ret = r[0].strip()
                if len(ret) > 0:
                    result.append(ret)
        return result

    @staticmethod
    def is_parent(t1, t2):
        """Checks if task t1 is a parent of task t2.
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


def main():
    import sys
    import os
    from caper_uri import init_caper_uri

    if len(sys.argv) < 2:
        print('Usage: python cromwell_metadata.py [METADATA_JSON_FILE]')
        sys.exit(1)

    init_caper_uri(os.path.join(os.getcwd(), 'cromwell_metadata_tmp'))

    m_json_file = sys.argv[1]
    CromwellMetadata(m_json_file, debug=True)


if __name__ == '__main__':
    main()
