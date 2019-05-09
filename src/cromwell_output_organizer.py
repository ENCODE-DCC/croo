#!/usr/bin/env python3
"""CromwellOutputOrganizer (COO): Cromwell output organizer based on
Cromwell's metadata.json.

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import sys
import json
import argparse
from cromweller_uri import init_cromweller_uri, CromwellerURI
from cromwell_metadata import CromwellMetadata

__version__ = "v0.1.0"


def parse_coo_arguments():
    """Argument parser for Cromwell Output Organizer (COO)
    """
    p = argparse.ArgumentParser()
    p.add_argument(
        'metadata_json',
        help='Path, URL or URI for metadata.json for a workflow '
             'Example: /scratch/sample1/metadata.json, '
             'gs://some/where/metadata.json, '
             'http://hello.com/world/metadata.json')
    p.add_argument(
        '--out-def-json', required=True,
        help='Output definition JSON file for a WDL file corresponding to '
             'the specified metadata.json file')
    p.add_argument(
        '--method', choices=('link', 'copy'), default='link',
        help='Method to localize files on output directory/bucket. '
        '"link" means a soft-linking and it\'s for local directory only. '
        'Original output files will be kept in Cromwell\'s output '
        'directory. '
        '"copy" makes a copy of Cromwell\'s original outputs')
    p.add_argument(
        '--out-dir', default='.', help='Output directory/bucket '
                                       '(local or remote)')
    p.add_argument(
        '--tmp-dir', help='LOCAL temporary directory')
    p.add_argument(
        '--use-gsutil-over-aws-s3', action='store_true',
        help='Use gsutil instead of aws s3 CLI even for S3 buckets.')
    p.add_argument(
        '--http-user',
        help='Username to download data from private URLs')
    p.add_argument(
        '--http-password',
        help='Password to download data from private URLs')

    if len(sys.argv[1:]) == 0:
        p.print_help()
        p.exit()
    # parse all args
    args = p.parse_args()

    # convert to dict
    args_d = vars(args)

    return args_d


class CromwellOutputOrganizer(object):
    """Cromwell output organizer (COO)

    It parses Cromwell's metadata.json to get all information about outputs
    and organize outputs as specified in output definition JSON
    """

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
                    shard_idx = task['shard_idx']
                    out_files = task['out_files']

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
            ${i0} : 0-based index for a main scatter loop
            ${i1} : 1-based index for a main scatter loop
            ${j0} : 0-based index for a nested scatter loop
            ${j1} : 1-based index for a nested scatter loop
            ${k0} : 0-based index for a double-nested scatter loop
            ${k1} : 1-based index for a double-nested scatter loop
            ${basename} : basename of file
        """
        result = s
        if shard_idx is not None:
            i0 = str(shard_idx[0])
            i1 = str(shard_idx[0]+1)
            result = result.replace('${i0}',i0)
            result = result.replace('${i1}',i1)

            if len(shard_idx)>1:            
                j0 = str(shard_idx[1]) 
                j1 = str(shard_idx[1]+1)
                result = result.replace('${j0}',j0)
                result = result.replace('${j1}',j1)

            if len(shard_idx)>2:
                k0 = str(shard_idx[2])
                k1 = str(shard_idx[2]+1)
                result = result.replace('${k0}',k0)
                result = result.replace('${k1}',k1)

        if full_path is not None:
            basename = os.path.basename(full_path)
            result = result.replace('${basename}',basename)

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
