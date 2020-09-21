#!/usr/bin/env python3
"""CromwellMetadata parser.
Construct a task graph based on Cromwell's metadata.json

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import json
import re
from collections import OrderedDict, namedtuple

from autouri import AutoURI
from WDL import parse_document

from .dag import DAG

CMNode = namedtuple(
    'CMNode',
    (
        'type',
        'shard_idx',
        'task_name',
        'output_name',
        'output_path',
        'all_outputs',
        'all_inputs',
    ),
)


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
        return n2.all_inputs is not None and n1.output_path in [
            path for _, path, _ in n2.all_inputs
        ]

    return False


def find_files_in_dict(d, parent=tuple(), list_idx=tuple()):
    """Can recursively parse WDL struct.
    """
    files = []
    if isinstance(d, dict):
        for k, v in d.items():
            files.extend(find_files_in_dict(v, parent=parent + (k,), list_idx=list_idx))

    elif isinstance(d, (list, tuple)):
        for i, v in enumerate(d):
            files.extend(find_files_in_dict(v, parent=parent, list_idx=list_idx + (i,)))

    elif isinstance(d, str) and AutoURI(d).is_valid:
        files.append(('.'.join(parent), d, list_idx if list_idx else (-1,)))
    return files


class CromwellMetadata(object):
    """Construct a task DAG based Cromwell's metadata.json file
    """

    RE_PATTERN_WDL_COMMENT_OUT_DEF_JSON = r'^\s*\#\s*CROO\s+out_def\s(.+)'
    WDL_WORKFLOW_META_OUT_DEF = 'croo_out_def'

    def __init__(self, metadata_json, debug=False):
        self._metadata_json = metadata_json

        # input JSON
        if 'submittedFiles' in self._metadata_json:
            self._input_json = json.loads(
                self._metadata_json['submittedFiles']['inputs'],
                object_pairs_hook=OrderedDict,
            )
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
                all_inputs=None,
            )
            self._dag.add_node(n)

    def __parse_calls(
        self, calls, parent_wf_name='', wf_alias=None, parent_wf_shard_idx=tuple()
    ):
        """Recursively parse calls in metadata JSON for subworkflow
        """
        for call_name, call_list in calls.items():
            for _, c in enumerate(call_list):
                shard_idx = c['shardIndex']
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
                        parent_wf_shard_idx=parent_wf_shard_idx + (shard_idx,),
                    )
                    continue

                task_name = parent_wf_name + wf_name + '.' + task_alias
                shard_idx = parent_wf_shard_idx + (shard_idx,)

                in_files = None
                if 'inputs' in c:
                    in_files = find_files_in_dict(c['inputs'])

                out_files = None
                if 'outputs' in c:
                    out_files = find_files_in_dict(c['outputs'])

                # add task itself to DAG
                n = CMNode(
                    type='task',
                    shard_idx=shard_idx,
                    task_name=task_name,
                    output_name=None,
                    output_path=None,
                    all_outputs=tuple(out_files) if out_files else None,
                    all_inputs=tuple(in_files) if in_files else None,
                )
                self._dag.add_node(n)

                if out_files:
                    for output_name, output_path, _ in out_files:
                        # add each output file to DAG
                        n = CMNode(
                            type='output',
                            shard_idx=shard_idx,
                            task_name=task_name,
                            output_name=output_name,
                            output_path=output_path,
                            all_outputs=None,
                            all_inputs=None,
                        )
                        self._dag.add_node(n)

    def __find_out_def_from_wdl(self):
        r = self.__find_workflow_meta(CromwellMetadata.WDL_WORKFLOW_META_OUT_DEF)
        if r is not None:
            return r

        r = self.__find_val_from_wdl(
            CromwellMetadata.RE_PATTERN_WDL_COMMENT_OUT_DEF_JSON
        )
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

    def __find_workflow_meta(self, key):
        """Find value for a key in workflow's meta section

        Returns:
            None if key not found or any error occurs.
        """
        try:
            wdl = parse_document(self._wdl_str)
            if key in wdl.workflow.meta:
                return wdl.workflow.meta[key]
        except Exception:
            pass
        return None


def main():
    import sys

    if len(sys.argv) < 2:
        print('Usage: python cromwell_metadata.py [METADATA_JSON_FILE]')
        sys.exit(1)

    m_json_file = sys.argv[1]
    CromwellMetadata(m_json_file, debug=True)


if __name__ == '__main__':
    main()
