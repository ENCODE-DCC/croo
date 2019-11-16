#!/usr/bin/env python3
"""Croo (croo): Cromwell output organizer based on
Cromwell's metadata.json.

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import sys
import json
import re
import caper
from caper.caper_uri import init_caper_uri, CaperURI, URI_LOCAL

from .croo_args import parse_croo_arguments
from .croo_html_report import CrooHtmlReport
from .cromwell_metadata import CromwellMetadata


class Croo(object):
    """Cromwell output organizer (croo)

    It parses Cromwell's metadata.json to get all information about outputs
    and organize outputs as specified in output definition JSON
    """
    RE_PATTERN_INLINE_EXP = r'\$\{(.*?)\}'
    KEY_TASK_GRAPH_TEMPLATE = 'task_graph_template'
    KEY_INPUT = 'inputs'

    def __init__(self, metadata_json, out_def_json, out_dir,
                 soft_link=True,
                 ucsc_genome_db=None,
                 ucsc_genome_pos=None):
        """Initialize croo with output definition JSON
        """
        if isinstance(metadata_json, dict):
            self._metadata = metadata_json
        else:
            f = CaperURI(metadata_json).get_local_file()
            with open(f, 'r') as fp:
                self._metadata = json.loads(fp.read())
            if isinstance(self._metadata, list):
                if len(self._metadata) > 1:
                    print('[Croo] Warning: multiple metadata JSON objects '
                          'found in metadata JSON file. Taking the first '
                          'one...')
                elif len(self._metadata) == 0:
                    raise Exception('metadata JSON file is empty')
                self._metadata = self._metadata[0]
        self._out_dir = out_dir
        self._cm = CromwellMetadata(self._metadata)
        self._ucsc_genome_db = ucsc_genome_db
        self._ucsc_genome_pos = ucsc_genome_pos

        if isinstance(out_def_json, dict):
            self._out_def_json = out_def_json
        else:
            if out_def_json is None:
                out_def_json_file_from_wdl = self._cm.get_out_def_json_file()
                if out_def_json_file_from_wdl is None:
                    raise ValueError('out_def JSON file is not defined. '
                                     'Define --out-def-json in cmd line arg or '
                                     'add "#CROO out_def [URL_OR_CLOUD_URI]" '
                                     'to your WDL')
                out_def_json = out_def_json_file_from_wdl
            f = CaperURI(out_def_json).get_local_file()
            with open(f, 'r') as fp:
                self._out_def_json = json.loads(fp.read())

        self._task_graph = self._cm.get_task_graph()
        if Croo.KEY_TASK_GRAPH_TEMPLATE in self._out_def_json:
            self._task_graph_template = self._out_def_json.pop(Croo.KEY_TASK_GRAPH_TEMPLATE)
        else:
            self._task_graph_template = None
        if Croo.KEY_INPUT in self._out_def_json:
            self._input_def_json = self._out_def_json.pop(Croo.KEY_INPUT)
        else:
            self._input_def_json = None
        self._soft_link = soft_link

    def organize_output(self):
        """Organize outputs
        """
        report = CrooHtmlReport(
            out_dir=self._out_dir,
            workflow_id=self._cm.get_workflow_id(),
            dag=self._task_graph,
            task_graph_template=self._task_graph_template,
            ucsc_genome_db=self._ucsc_genome_db,
            ucsc_genome_pos=self._ucsc_genome_pos)

        if self._input_def_json is not None:
            for input_name, input_obj in self._input_def_json.items():
                node_format = input_obj.get('node')
                subgraph = input_obj.get('subgraph')

                for _, node in self._task_graph.get_nodes():
                    # if node is pipeline's input
                    if node.type != 'output' or node.task_name is not None \
                            or node.output_name != input_name:
                        continue
                    full_path = node.output_path
                    shard_idx = node.shard_idx

                    if node_format is not None:
                        interpreted_node_format = Croo.__interpret_inline_exp(
                            node_format, full_path, shard_idx)
                        if subgraph is not None:
                            interpreted_subgraph = Croo.__interpret_inline_exp(
                                subgraph, full_path, shard_idx)
                        else:
                            interpreted_subgraph = None
                        report.add_to_task_graph(node.output_name,
                                                 None,
                                                 shard_idx,
                                                 full_path,
                                                 interpreted_node_format,
                                                 interpreted_subgraph)

        for task_name, out_vars in self._out_def_json.items():
            for output_name, output_obj in out_vars.items():
                path = output_obj.get('path')
                table_item = output_obj.get('table')
                ucsc_track = output_obj.get('ucsc_track')
                node_format = output_obj.get('node')
                subgraph = output_obj.get('subgraph')

                for _, node in self._task_graph.get_nodes():
                    # look at output nodes only (not a task node)
                    if task_name != node.task_name or node.type != 'task':
                        continue
                    all_outputs = node.all_outputs
                    shard_idx = node.shard_idx

                    for k, full_path, _ in all_outputs:
                        if k != output_name:
                            continue

                        if path is not None:
                            interpreted_path = Croo.__interpret_inline_exp(
                                path, full_path, shard_idx)

                            # write to output directory
                            target_uri = os.path.join(self._out_dir,
                                                      interpreted_path)
                            # if soft_link, target_uri changes to original source
                            target_uri = CaperURI(full_path).copy(
                                target_uri=target_uri,
                                soft_link=self._soft_link)
                        else:
                            target_uri = full_path

                        # get presigned URLs if possible
                        if path is not None or table_item is not None \
                                or ucsc_track is not None or node_format is not None:
                            target_url = CaperURI(target_uri).get_url()
                        else:
                            target_url = None

                        if table_item is not None:
                            interpreted_table_item = Croo.__interpret_inline_exp(
                                table_item, full_path, shard_idx)
                            # add to file table
                            report.add_to_file_table(target_uri,
                                                     target_url,
                                                     interpreted_table_item)
                        if ucsc_track is not None and target_url is not None:
                            interpreted_ucsc_track = Croo.__interpret_inline_exp(
                                ucsc_track, full_path, shard_idx)
                            report.add_to_ucsc_track(target_url,
                                                     interpreted_ucsc_track)
                        if node_format is not None:
                            interpreted_node_format = Croo.__interpret_inline_exp(
                                node_format, full_path, shard_idx)
                            if subgraph is not None:
                                interpreted_subgraph = Croo.__interpret_inline_exp(
                                    subgraph, full_path, shard_idx)
                            else:
                                interpreted_subgraph = None
                            report.add_to_task_graph(output_name,
                                                     task_name,
                                                     shard_idx,
                                                     full_path if target_url is None else target_url,
                                                     interpreted_node_format,
                                                     interpreted_subgraph)
        # write to html report
        report.save_to_file()

    @staticmethod
    def __interpret_inline_exp(s, full_path, shard_idx):
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
            m = re.search(Croo.RE_PATTERN_INLINE_EXP, result)
            if m is None:
                break
            result = result.replace(m.group(0), str(eval(m.group(1))), 1)

        return result


def init_dirs_args(args):
    """More initialization for out/tmp directories since tmp
    directory is important for inter-storage transfer using
    CaperURI
    """
    if args['out_dir'].startswith(('http://', 'https://')):
        raise ValueError('URL is not allowed for --out-dir')
    elif args['out_dir'].startswith(('gs://', 's3://')):
        if args.get('tmp_dir') is None:
            args['tmp_dir'] = os.path.join(os.getcwd(), '.croo_tmp')
    else:
        args['out_dir'] = os.path.abspath(os.path.expanduser(args['out_dir']))
        os.makedirs(args['out_dir'], exist_ok=True)

        if args.get('tmp_dir') is None:
            args['tmp_dir'] = os.path.join(args['out_dir'], '.croo_tmp')

    # make temp dir
    os.makedirs(args['tmp_dir'], exist_ok=True)

    mapping_path_to_url = None
    if args.get('tsv_mapping_path_to_url') is not None:
        mapping_path_to_url = {}
        f = os.path.expanduser(args.get('tsv_mapping_path_to_url'))
        with open(f, 'r') as fp:
            lines = fp.read().strip('\n').split('\n')
            for line in lines:
                k, v = line.split('\t')
                mapping_path_to_url[k] = v

    # init caper uri to transfer files across various storages
    #   e.g. gs:// to s3://, http:// to local, ...
    init_caper_uri(
        tmp_dir=args['tmp_dir'],
        tmp_s3_bucket=None,
        tmp_gcs_bucket=None,
        http_user=args.get('http_user'),
        http_password=args.get('http_password'),
        use_gsutil_over_aws_s3=args.get('use_gsutil_over_aws_s3'),
        use_presigned_url_s3=args.get('use_presigned_url_s3'),
        use_presigned_url_gcs=args.get('use_presigned_url_gcs'),
        gcp_private_key_file=args.get('gcp_private_key'),
        public_gcs=args.get('public_gcs'),
        duration_sec_presigned_url_s3=args.get('duration_presigned_url_s3'),
        duration_sec_presigned_url_gcs=args.get('duration_presigned_url_gcs'),
        mapping_path_to_url=mapping_path_to_url,
        verbose=True)

def main():
    # parse arguments. note that args is a dict
    args = parse_croo_arguments()

    # init out/tmp dirs and CaperURI for inter-storage transfer
    init_dirs_args(args)

    co = Croo(
        metadata_json=args['metadata_json'],
        out_def_json=args['out_def_json'],
        out_dir=args['out_dir'],
        ucsc_genome_db=args['ucsc_genome_db'],
        ucsc_genome_pos=args['ucsc_genome_pos'],
        soft_link=args['method'] == 'link')

    co.organize_output()

    return 0


if __name__ == '__main__':
    main()
