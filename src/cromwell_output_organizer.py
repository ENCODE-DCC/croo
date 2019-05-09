#!/usr/bin/env python3
"""CromwellOutputOrganizer (COO): Cromwell output organizer based on
Cromwell's metadata.json.

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import sys
import json
import re
from cromwell_output_organizer_args import parse_coo_arguments
from cromweller_uri import init_cromweller_uri, CromwellerURI
from cromwell_metadata import CromwellMetadata

__version__ = "v0.1.0"


class CromwellOutputOrganizer(object):
    """Cromwell output organizer (COO)

    It parses Cromwell's metadata.json to get all information about outputs
    and organize outputs as specified in output definition JSON
    """
    RE_PATTERN_INLINE_EXP = r'\$\{(.*?)\}'

    def __init__(self, out_def_json, soft_link=True):
        """Initialize COO with output definition JSON
        """
        if isinstance(out_def_json, dict):
            self._out_def_json = out_def_json
        else:
            f = CromwellerURI(out_def_json).get_local_file()
            with open(f, 'r') as fp:
                self._out_def_json = json.loads(fp.read())

        self._soft_link = soft_link

    def organize_output(self, metadata_json, out_dir):
        """Organize outputs
        """
        if isinstance(metadata_json, dict):
            m = metadata_json
        else:
            f = CromwellerURI(metadata_json).get_local_file()
            with open(f, 'r') as fp:
                m = json.loads(fp.read())

        cm = CromwellMetadata(m)
        task_graph = cm.get_task_graph()

        for task_name, out_vars in self._out_def_json.items():
            for out_var_name, out_var in out_vars.items():
                path = out_var.get('path')
                # desc = out_var.get('desc')
                # table_item = out_var.get('table_item')
                # graph_node = out_var.get('graph_node')

                for _, task in task_graph.get_nodes():
                    if task_name != task['task_name']:
                        continue
                    out_files = task['out_files']
                    shard_idx = task['shard_idx']

                    for k, full_path in out_files:
                        if k != out_var_name:
                            continue
                        target_rel_path = \
                            CromwellOutputOrganizer.__interpret_inline_exp(
                                path, full_path, shard_idx)
                        target_uri = os.path.join(out_dir, target_rel_path)

                        CromwellerURI(full_path).copy(
                            target_uri=target_uri,
                            soft_link=self._soft_link)

    @staticmethod
    def __interpret_inline_exp(s, full_path=None, shard_idx=None):
        """Interpret inline expression in output defition JSON
        e.g. s can be "align/rep${i1}/${basename}"

        Args:
            full_path: full absolute path for output file
            shard_idx: tuple of scatter indices. -1 means no scatter
                       e.g. (-1, 0, 1,):
                            no scatter in main workflow
                            scatter id 0 in subworkflow
                            scatter id 1 in subsubworkflow

        Supported expressions:
            ${i} (int) : 0-based index for a main scatter loop
            ${j} (int) : 0-based index for a nested scatter loop
            ${k} (int) : 0-based index for a double-nested scatter loop
            ${basename} (str) : basename of file
            ${dirname} (str)  : dirname of file
            ${full_path} (str) : full_path of file (can be path, gs://, s3://)
            ${shard_idx} : tuple of (i, j, k, ...) with dynamic length
        """
        result = s

        if shard_idx[0] > -1:
            i = shard_idx[0]
        else:
            i = None
        if len(shard_idx) > 1 and shard_idx[1] > -1:
            j = shard_idx[1]
        else:
            j = None
        if len(shard_idx) > 2 and shard_idx[2] > -1:
            k = shard_idx[2]
        else:
            k = None
        basename = os.path.basename(full_path)
        dirname = os.path.dirname(full_path)

        while True:
            m = re.search(CromwellOutputOrganizer.RE_PATTERN_INLINE_EXP, result)
            if m is None:
                break
            result = result.replace(m.group(0), str(eval(m.group(1))), 1)

        return result


def init_dirs_args(args):
    """More initialization for out/tmp directories since tmp
    directory is important for inter-storage transfe using
    CromwellerURI
    """
    if args['out_dir'].startswith(('http://', 'https://')):
        raise ValueError('URL is not allowed for --out-dir')
    elif args['out_dir'].startswith(('gs://', 's3://')):
        if args.get('tmp_dir') is None:
            args['tmp_dir'] = os.path.join(os.getcwd(), '.coo_tmp')
    else:
        args['out_dir'] = os.path.abspath(os.path.expanduser(args['out_dir']))
        os.makedirs(args['out_dir'], exist_ok=True)

        if args.get('tmp_dir') is None:
            args['tmp_dir'] = os.path.join(args['out_dir'], '.coo_tmp')

    # make temp dir
    os.makedirs(args['tmp_dir'], exist_ok=True)

    # init cromweller uri to transfer files across various storages
    #   e.g. gs:// to s3://, http:// to local, ...
    init_cromweller_uri(
        tmp_dir=args['tmp_dir'],
        tmp_s3_bucket=None,
        tmp_gcs_bucket=None,
        http_user=args.get('http_user'),
        http_password=args.get('http_password'),
        use_gsutil_over_aws_s3=args.get('use_gsutil_over_aws_s3'),
        verbose=True)

def main():
    # parse arguments. note that args is a dict
    args = parse_coo_arguments()

    # init out/tmp dirs and CromwellerURI for inter-storage transfer
    init_dirs_args(args)

    co = CromwellOutputOrganizer(
        out_def_json=args['out_def_json'],
        soft_link=args['method'] == 'link')

    co.organize_output(
        metadata_json=args['metadata_json'],
        out_dir=args['out_dir'])

    return 0


if __name__ == '__main__':
    main()
