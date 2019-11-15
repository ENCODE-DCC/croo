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
from collections import OrderedDict, namedtuple
from .dag import DAG


CMNode = namedtuple('CMNode',
    ('type', 'shard_idx', 'task_name', 'output_name', 'output_path',
     'all_outputs', 'all_inputs'))


def is_parent_cmnode(n1, n2):
    """Check if n1 is a parent node of n2.
    There are two types of nodes:
    1) task
    2) output
    """
    if n1.type not in ('task', 'output') or n2.type not in ('task', 'output'):
        raise ValueError('Unsupported CMNode type: {}.'.format(n1.type))

    if n1.type == 'task' and n2.type == 'output':
        return n1.task_name == n2.task_name and n1.shard_idx == n2.shard_idx

    elif n1.type == 'output' and n2.type == 'task':
        return n2.all_inputs is not None and \
                n1.output_path in [path for _, path, _ in n2.all_inputs]

    return False


def find_files_in_dict(d):
    files = []
    for k, v in d.items():
        maybe_files = []
        if isinstance(v, list):
            for i, v_ in enumerate(v):
                if isinstance(v_, str):
                    maybe_files.append((v_, (i,)))
                elif isinstance(v_, list):
                    for j, v__ in enumerate(v_):
                        if isinstance(v__, str):
                            maybe_files.append((v__, (i, j)))
                        elif isinstance(v__, list):
                            for k, v___ in enumerate(v__):
                                if isinstance(v___, str):
                                    maybe_files.append((v___, (i, j, k)))
        elif isinstance(v, dict):
            for _, v_ in v.items():
                if isinstance(v_, str):
                    maybe_files.append((v_, (-1,)))
        elif isinstance(v, str):
            maybe_files.append((v, (-1,)))
        for f, shard_idx in maybe_files:
            if CaperURI(f).is_valid_uri():
                files.append((k, f, shard_idx))
    return files


class CromwellMetadata(object):
    """Construct a task DAG based Cromwell's metadata.json file
    """
    RE_PATTERN_WDL_COMMENT_OUT_DEF_JSON = \
        r'^\s*\#\s*CROO\s+out_def\s(.+)'

    def __init__(self, metadata_json, debug=False):
        self._metadata_json = metadata_json

        # input JSON
        if 'submittedFiles' in self._metadata_json:
            self._input_json = json.loads(
                self._metadata_json['submittedFiles']['inputs'],
                object_pairs_hook=OrderedDict)
            # WDL contents
            self._wdl_str = self._metadata_json['submittedFiles']['workflow']
            self._out_def_json_file = self.__find_out_def_from_wdl()
        else:
            # Would work also with sub-workflow metadata that does not
            # contain 'submittedFiles'
            self._input_json = None
            # WDL contents
            self._wdl_str = None
            self._out_def_json_file = None
        # workflow ID
        self._workflow_id = self._metadata_json['id']

        # construct an indexed DAG
        self._dag = DAG(fnc_is_parent=is_parent_cmnode)

        # parse calls to add tasks and their outputs to graph
        self.__parse_calls(self._metadata_json['calls'])

        # parse input JSON to add inputs to graph
        self.__parse_input_json()

        self._debug = debug
        if self._debug:
            print(self._dag)

    def get_workflow_id(self):
        return self._workflow_id

    def get_task_graph(self):
        return self._dag

    def get_out_def_json_file(self):
        return self._out_def_json_file

    def __parse_input_json(self):
        """Recursively parse input JSON to add input files to graph
        """
        if self._input_json is None:
            return

        for file_name, file_path, shard_idx in find_files_in_dict(self._input_json):
            # add it as an "output" without an associated task
            n = CMNode(
                type='output',
                shard_idx=shard_idx,
                task_name=None,
                output_name=file_name,
                output_path=file_path,
                all_outputs=None,
                all_inputs=None)
            self._dag.add_node(n)

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

                task_name = parent_wf_name + wf_name + '.' + task_alias
                shard_idx = parent_wf_shard_idx + (shard_idx,)

                if 'inputs' in c:
                    in_files = find_files_in_dict(c['inputs'])
                else:
                    in_files = None

                if 'outputs' in c:
                    out_files = find_files_in_dict(c['outputs'])
                else:
                    out_files = None

                # add task itself to DAG
                n = CMNode(
                    type='task',
                    shard_idx=shard_idx,
                    task_name=task_name,
                    output_name=None,
                    output_path=None,
                    all_outputs=tuple(out_files),
                    all_inputs=tuple(in_files))
                self._dag.add_node(n)

                for output_name, output_path, _ in out_files:
                    # add each output file to DAG
                    n = CMNode(
                        type='output',
                        shard_idx=shard_idx,
                        task_name=task_name,
                        output_name=output_name,
                        output_path=output_path,
                        all_outputs=None,
                        all_inputs=None)
                    self._dag.add_node(n)

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
