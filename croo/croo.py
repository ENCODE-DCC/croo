import json
import logging
import os
import re

from autouri import GCSURI, S3URI, AbsPath, AutoURI

from .cromwell_metadata import CromwellMetadata
from .croo_html_report import CrooHtmlReport

logger = logging.getLogger(__name__)


class Croo(object):
    """Cromwell output organizer (croo)

    It parses Cromwell's metadata.json to get all information about outputs
    and organize outputs as specified in output definition JSON
    """

    RE_PATTERN_INLINE_EXP = r'\$\{(.*?)\}'
    KEY_TASK_GRAPH_TEMPLATE = 'task_graph_template'
    KEY_INPUT = 'inputs'

    def __init__(
        self,
        metadata_json,
        out_def_json,
        out_dir,
        tmp_dir,
        soft_link=True,
        ucsc_genome_db=None,
        ucsc_genome_pos=None,
        use_presigned_url_s3=False,
        use_presigned_url_gcs=False,
        duration_presigned_url_s3=0,
        duration_presigned_url_gcs=0,
        public_gcs=False,
        gcp_private_key=None,
        map_path_to_url=None,
        no_checksum=False,
    ):
        """Initialize croo with output definition JSON
        Args:
            soft_link:
                DO NOT MAKE A COPY of original cromwell output
                (source) on out_dir (destination).
                Try to soft-link it if both src and dest are on local storage.
                Otherwise, original cromwell outputs will be just referenced.
        """
        self._tmp_dir = tmp_dir
        if isinstance(metadata_json, dict):
            self._metadata = metadata_json
        else:
            f = AutoURI(metadata_json).localize_on(self._tmp_dir)
            with open(f, 'r') as fp:
                self._metadata = json.loads(fp.read())
            if isinstance(self._metadata, list):
                if len(self._metadata) > 1:
                    logger.warning(
                        'Multiple metadata JSON objects '
                        'found in metadata JSON file. Taking the first '
                        'one...'
                    )
                elif len(self._metadata) == 0:
                    raise Exception('metadata JSON file is empty')
                self._metadata = self._metadata[0]
        self._out_dir = out_dir
        self._cm = CromwellMetadata(self._metadata)
        self._ucsc_genome_db = ucsc_genome_db
        self._ucsc_genome_pos = ucsc_genome_pos

        self._use_presigned_url_s3 = use_presigned_url_s3
        self._use_presigned_url_gcs = use_presigned_url_gcs
        self._duration_presigned_url_s3 = duration_presigned_url_s3
        self._duration_presigned_url_gcs = duration_presigned_url_gcs
        self._public_gcs = public_gcs
        self._gcp_private_key = gcp_private_key
        self._map_path_to_url = map_path_to_url
        self._no_checksum = no_checksum

        if isinstance(out_def_json, dict):
            self._out_def_json = out_def_json
        else:
            if out_def_json is None:
                out_def_json_file_from_wdl = self._cm.get_out_def_json_file()
                if out_def_json_file_from_wdl is None:
                    raise ValueError(
                        'out_def JSON file is not defined. '
                        'Define --out-def-json in cmd line arg or '
                        'add "#CROO out_def [URL_OR_CLOUD_URI]" '
                        'to your WDL'
                    )
                out_def_json = out_def_json_file_from_wdl
            f = AutoURI(out_def_json).localize_on(self._tmp_dir)
            with open(f, 'r') as fp:
                self._out_def_json = json.loads(fp.read())

        self._task_graph = self._cm.get_task_graph()
        if Croo.KEY_TASK_GRAPH_TEMPLATE in self._out_def_json:
            self._task_graph_template = self._out_def_json.pop(
                Croo.KEY_TASK_GRAPH_TEMPLATE
            )
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
            public_gcs=self._public_gcs,
            gcp_private_key=self._gcp_private_key,
            use_presigned_url_gcs=self._use_presigned_url_gcs,
            use_presigned_url_s3=self._use_presigned_url_s3,
            duration_presigned_url_s3=self._duration_presigned_url_s3,
            duration_presigned_url_gcs=self._duration_presigned_url_gcs,
            map_path_to_url=self._map_path_to_url,
            ucsc_genome_db=self._ucsc_genome_db,
            ucsc_genome_pos=self._ucsc_genome_pos,
        )

        if self._input_def_json is not None:
            for input_name, input_obj in self._input_def_json.items():
                node_format = input_obj.get('node')
                subgraph = input_obj.get('subgraph')

                for _, node in self._task_graph.get_nodes():
                    # if node is pipeline's input
                    if (
                        node.type != 'output'
                        or node.task_name is not None
                        or node.output_name != input_name
                    ):
                        continue
                    full_path = node.output_path
                    shard_idx = node.shard_idx

                    if node_format is not None:
                        interpreted_node_format = Croo.__interpret_inline_exp(
                            node_format, full_path, shard_idx
                        )
                        if subgraph is not None:
                            interpreted_subgraph = Croo.__interpret_inline_exp(
                                subgraph, full_path, shard_idx
                            )
                        else:
                            interpreted_subgraph = None
                        report.add_to_task_graph(
                            node.output_name,
                            None,
                            shard_idx,
                            full_path,
                            interpreted_node_format,
                            interpreted_subgraph,
                        )

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
                    if not all_outputs:
                        continue

                    for k, full_path, _ in all_outputs:
                        if k != output_name:
                            continue

                        target_uri = full_path
                        if path is not None:
                            interpreted_path = Croo.__interpret_inline_exp(
                                path, full_path, shard_idx
                            )

                            au = AutoURI(full_path)
                            target_path = os.path.join(self._out_dir, interpreted_path)

                            if self._soft_link:
                                au_target = AutoURI(target_path)
                                if isinstance(au, AbsPath) and isinstance(
                                    au_target, AbsPath
                                ):
                                    au.soft_link(target_path, force=True)
                                    target_uri = target_path
                                else:
                                    target_uri = full_path
                            else:
                                target_uri = au.cp(
                                    target_path,
                                    no_checksum=self._no_checksum,
                                    make_md5_file=True,
                                )

                        # get presigned URLs if possible
                        target_url = None
                        if (
                            path is not None
                            or table_item is not None
                            or ucsc_track is not None
                            or node_format is not None
                        ):
                            u = AutoURI(target_uri)

                            if isinstance(u, GCSURI):
                                if self._public_gcs:
                                    target_url = u.get_public_url()

                                elif self._use_presigned_url_gcs:
                                    target_url = u.get_presigned_url(
                                        duration=self._duration_presigned_url_gcs,
                                        private_key_file=self._gcp_private_key,
                                    )

                            elif isinstance(u, S3URI):
                                if self._use_presigned_url_s3:
                                    target_url = u.get_presigned_url(
                                        duration=self._duration_presigned_url_s3
                                    )

                            elif isinstance(u, AbsPath):
                                if self._map_path_to_url:
                                    target_url = u.get_mapped_url(
                                        map_path_to_url=self._map_path_to_url
                                    )

                        if table_item is not None:
                            interpreted_table_item = Croo.__interpret_inline_exp(
                                table_item, full_path, shard_idx
                            )
                            # add to file table
                            report.add_to_file_table(
                                target_uri, target_url, interpreted_table_item
                            )
                        if ucsc_track is not None and target_url is not None:
                            interpreted_ucsc_track = Croo.__interpret_inline_exp(
                                ucsc_track, full_path, shard_idx
                            )
                            report.add_to_ucsc_track(target_url, interpreted_ucsc_track)
                        if node_format is not None:
                            interpreted_node_format = Croo.__interpret_inline_exp(
                                node_format, full_path, shard_idx
                            )
                            if subgraph is not None:
                                interpreted_subgraph = Croo.__interpret_inline_exp(
                                    subgraph, full_path, shard_idx
                                )
                            else:
                                interpreted_subgraph = None
                            report.add_to_task_graph(
                                output_name,
                                task_name,
                                shard_idx,
                                full_path if target_url is None else target_url,
                                interpreted_node_format,
                                interpreted_subgraph,
                            )
        # write to html report
        report.save_to_file()

    @staticmethod
    def __interpret_inline_exp(s, full_path, shard_idx):
        """Interpret inline expression in output defition JSON
        e.g. s can be "align/rep${i1}/${basename}"
        Nested scatter can only be implemented by using subworkflows.

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
            ${ll} (int) : 0-based index for a triple-nested scatter loop
            ${m} (int) : 0-based index for a quadruple-nested scatter loop
            ${n} (int) : 0-based index for a 5-nested scatter loop
            ${o} (int) : 0-based index for a 6-nested scatter loop
            ${basename} (str) : basename of file
            ${dirname} (str)  : dirname of file
            ${full_path} (str) : full_path of file (can be path, gs://, s3://)
            ${shard_idx} : tuple of (i, j, k, ...) with dynamic length
        """
        result = s

        i = None
        if shard_idx[0] > -1:
            i = shard_idx[0]
        j = None
        if len(shard_idx) > 1 and shard_idx[1] > -1:
            j = shard_idx[1]
        k = None
        if len(shard_idx) > 2 and shard_idx[2] > -1:
            k = shard_idx[2]
        l = None
        if len(shard_idx) > 3 and shard_idx[3] > -1:
            l = shard_idx[3]
        m = None
        if len(shard_idx) > 4 and shard_idx[4] > -1:
            m = shard_idx[4]
        n = None
        if len(shard_idx) > 5 and shard_idx[5] > -1:
            n = shard_idx[5]
        o = None
        if len(shard_idx) > 6 and shard_idx[6] > -1:
            o = shard_idx[6]

        basename = os.path.basename(full_path)
        dirname = os.path.dirname(full_path)
        logger.debug(
            'inline expression: basename={basename}, dirname={dirname}, '
            'i={i}, j={j}, k={k}, l={l}, m={m}, n={n}, o={o}'.format(
                basename=basename, dirname=dirname, i=i, j=j, k=k, l=l, m=m, n=n, o=o
            )
        )

        while True:
            m = re.search(Croo.RE_PATTERN_INLINE_EXP, result)
            if m is None:
                break
            result = result.replace(m.group(0), str(eval(m.group(1))), 1)

        return result
