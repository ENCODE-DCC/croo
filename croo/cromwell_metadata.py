import json
import tempfile
from collections import OrderedDict, namedtuple
from pathlib import Path

from autouri import AutoURI

from .croo_wdl_parser import CrooWDLParser
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


def find_valid_uris_in_dict(d, parent=tuple(), list_idx=tuple()):
    """Can recursively parse WDL struct to find valid AbsPath/URL/URIs.
    For example, /somewhere/here/there.txt, s3://bucket1/t.txt, http://...

    Returns a list of tuples (
        dot_delimited_all_parents_string,
        uri,
        tuple_of_nested_shard_indices,
    ).
    """
    files = []
    if isinstance(d, dict):
        for k, v in d.items():
            files.extend(
                find_valid_uris_in_dict(v, parent=parent + (k,), list_idx=list_idx)
            )

    elif isinstance(d, (list, tuple)):
        for i, v in enumerate(d):
            files.extend(
                find_valid_uris_in_dict(v, parent=parent, list_idx=list_idx + (i,))
            )

    elif isinstance(d, str) and AutoURI(d).is_valid:
        files.append(('.'.join(parent), d, list_idx if list_idx else (-1,)))
    return files


class CromwellMetadata:
    """Construct a task DAG based Cromwell's metadata.json file
    """

    def __init__(self, metadata_json, debug=False):
        self._metadata_json = metadata_json

        # input JSON
        if 'submittedFiles' in self._metadata_json:
            self._input_json = json.loads(
                self._metadata_json['submittedFiles']['inputs'],
                object_pairs_hook=OrderedDict,
            )
            # parse WDL to find croo JSON file path/URL
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_wdl = Path(tmpdir) / 'temp.wdl'
                temp_wdl.write_text(self._metadata_json['submittedFiles']['workflow'])
                self._out_def_json_file = CrooWDLParser(str(temp_wdl)).croo_out_def
        else:
            # Would work also with sub-workflow metadata that does not
            # contain 'submittedFiles'
            self._input_json = None
            self._out_def_json_file = None

        # workflow ID
        self._workflow_id = self._metadata_json['id']

        # construct an indexed DAG
        self._dag = DAG(fnc_is_parent=is_parent_cmnode)

        # parse calls to add tasks and their outputs to graph
        self.__parse_calls(
            self._metadata_json['calls'],
            parent_workflows=(self._metadata_json['workflowName'],),
        )

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

        for file_name, file_path, shard_idx in find_valid_uris_in_dict(
            self._input_json
        ):
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
        self, calls, parent_workflows, parent_workflow_shard_indices=tuple()
    ):
        """Recursively parse `calls` in Cromwell's metadata JSON for subworkflow.
        `calls` is a dict of { key: list_of_calls } with the following two key naming formats.

        - workflow_name.alias_of_subworkflow_or_task:
            Alias is used instead of name if subworkflow/task is imported/called with `as` statement.

        - ScatterAt*_*:
            Cromwell's temporary subworkflow to implement a nested `scatter` of WDL 1.0.
            It is a subworkflow without dot notation.

        Such dict's value `list_of_calls` is a list of `call` objects.

        Args:
            calls:
                `calls` in metadata JSON.
            parent_workflows:
                A tuple of parent workflow's name/alias.
                Grander parent comes first.
                Alias means a subworkflow imported with `as` statement in WDL.
                `None` element in this list means a temporary subworkflow to implement
                nested `scatter`.
            parent_workflow_shard_indices:
                Shard indices of all parent workflows (including nested scatter's indices).
                Grander parent's index comes first.
                The dimensions of `parent_workflows` and `parent_workflow_shard_indices` do not
                necessarily match if there is a nested `scatter`.
        """
        if not parent_workflows or not isinstance(parent_workflows, tuple):
            raise ValueError(
                'parent_workflows must be defined as non-empty tuple. '
                'If it is a root calling of this function '
                'then call with parent_workflows=(main_workflow_name,).'
            )

        for call_name, call_list in calls.items():
            split_call_name = call_name.split('.')

            if len(split_call_name) == 2:
                subworkflow_or_task_alias = split_call_name[1]

            elif len(split_call_name) == 1:
                if not call_name.startswith('ScatterAt'):
                    raise ValueError(
                        'Wrong temporary call name format for a nested subworkflow.'
                    )
                subworkflow_or_task_alias = None

            else:
                raise ValueError('Wrong call name format. Too many dots.')

            for c in call_list:
                shard_idx = c['shardIndex']

                # if it is a subworkflow, then recursively dive into it
                if 'subWorkflowMetadata' in c:
                    self.__parse_calls(
                        c['subWorkflowMetadata']['calls'],
                        parent_workflows=parent_workflows
                        + (subworkflow_or_task_alias,),
                        parent_workflow_shard_indices=parent_workflow_shard_indices
                        + (shard_idx,),
                    )
                    continue

                none_free_parent_workflows = (
                    workflow
                    for workflow in parent_workflows + (subworkflow_or_task_alias,)
                    if workflow is not None
                )

                full_call_name = '.'.join(none_free_parent_workflows)
                shard_idx = parent_workflow_shard_indices + (shard_idx,)

                in_files = None
                if 'inputs' in c:
                    in_files = find_valid_uris_in_dict(c['inputs'])

                out_files = None
                if 'outputs' in c:
                    out_files = find_valid_uris_in_dict(c['outputs'])

                # add task itself to DAG
                n = CMNode(
                    type='task',
                    shard_idx=shard_idx,
                    task_name=full_call_name,
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
                            task_name=full_call_name,
                            output_name=output_name,
                            output_path=output_path,
                            all_outputs=None,
                            all_inputs=None,
                        )
                        self._dag.add_node(n)
