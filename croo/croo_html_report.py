#!/usr/bin/env python3
"""CrooHtmlReport: HTML report generator for Croo

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import textwrap

from autouri import AutoURI

from .croo_html_report_file_table import CrooHtmlReportFileTable
from .croo_html_report_task_graph import CrooHtmlReportTaskGraph
from .croo_html_report_tracks import CrooHtmlReportUCSCTracks


class CrooHtmlReport(object):
    HEAD = '@HEAD_CONTENTS'
    BODY = '@BODY_CONTENTS'
    HTML = textwrap.dedent(
        """
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
            {head_contents}
          </head>
          <body>{body_contents}</body>
        </html>
    """
    ).format(head_contents=HEAD, body_contents=BODY)
    REPORT_HTML = 'croo.report.{workflow_id}.html'

    def __init__(
        self,
        out_dir,
        workflow_id,
        dag,
        task_graph_template=None,
        public_gcs=None,
        gcp_private_key=None,
        use_presigned_url_gcs=False,
        use_presigned_url_s3=False,
        duration_presigned_url_s3=None,
        duration_presigned_url_gcs=None,
        map_path_to_url=None,
        ucsc_genome_db=None,
        ucsc_genome_pos=None,
    ):
        self._out_dir = out_dir
        self._workflow_id = workflow_id
        self._public_gcs = public_gcs
        self._gcp_private_key = gcp_private_key
        self._use_presigned_url_gcs = use_presigned_url_gcs
        self._use_presigned_url_s3 = use_presigned_url_s3
        self._duration_presigned_url_s3 = duration_presigned_url_s3
        self._duration_presigned_url_gcs = duration_presigned_url_gcs
        self._map_path_to_url = map_path_to_url
        self._ucsc_tracks = CrooHtmlReportUCSCTracks(
            out_dir=out_dir,
            workflow_id=workflow_id,
            public_gcs=public_gcs,
            gcp_private_key=gcp_private_key,
            use_presigned_url_gcs=use_presigned_url_gcs,
            use_presigned_url_s3=use_presigned_url_s3,
            map_path_to_url=map_path_to_url,
            ucsc_genome_db=ucsc_genome_db,
            ucsc_genome_pos=ucsc_genome_pos,
        )
        self._file_table = CrooHtmlReportFileTable(
            out_dir=out_dir, workflow_id=workflow_id
        )
        self._task_graph = CrooHtmlReportTaskGraph(
            out_dir=out_dir,
            workflow_id=workflow_id,
            dag=dag,
            template_d=task_graph_template,
        )

    def add_to_file_table(self, full_path, url, table_item):
        self._file_table.add(full_path, url, table_item)

    def add_to_ucsc_track(self, url, track_line):
        self._ucsc_tracks.add(url, track_line)

    def add_to_task_graph(
        self, out_var, task_name, shard_idx, url, node_format, subgraph
    ):
        self._task_graph.add(out_var, task_name, shard_idx, url, node_format, subgraph)

    def save_to_file(self):
        html = CrooHtmlReport.HTML

        head = ''
        head += self._file_table.get_html_head_str()
        html = html.replace(CrooHtmlReport.HEAD, head)

        body = ''
        body += self._file_table.get_html_body_str()
        body += self._task_graph.get_html_body_str()
        body += self._ucsc_tracks.get_html_body_str()
        html = html.replace(CrooHtmlReport.BODY, body)

        # write to file and return HTML string
        uri_report = os.path.join(
            self._out_dir,
            CrooHtmlReport.REPORT_HTML.format(workflow_id=self._workflow_id),
        )
        AutoURI(uri_report).write(html)
        return html
