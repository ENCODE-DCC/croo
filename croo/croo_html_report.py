#!/usr/bin/env python3
"""CrooHtmlReport: HTML report generator for Croo

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

from .croo_html_report_tracks import CrooHtmlReportTracks
from .croo_html_report_task_graph import CrooHtmlReportTaskGraph
from .croo_html_report_file_table import CrooHtmlReportFileTable


class CrooHtmlReport(object):
    HEAD = '@HEAD_CONTENTS'
    BODY = '@BODY_CONTENTS'
    HTML = """
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/\
jquery.min.js"></script>
        {head_contents}
      </head>
      <body>{body_contents}</body>
    </html>
    """.format(head_contents=HEAD, body_contents=BODY)

    def __init__(self, html_root, use_rel_path_in_link=False):
        html_root = html_root.rstrip('/')+'/'
        self._tracks = CrooHtmlReportTracks(
            html_root=html_root)
        self._task_graph = CrooHtmlReportTaskGraph(
            html_root=html_root, use_rel_path_in_link=use_rel_path_in_link)
        self._file_table = CrooHtmlReportFileTable(
            html_root=html_root, use_rel_path_in_link=use_rel_path_in_link)
        self._html_root = html_root
        self._use_rel_path_in_link = use_rel_path_in_link

    def add_to_file_table(self, full_path, table_item):
        self._file_table.add(full_path, table_item)

    def get_html_str(self):
        html = CrooHtmlReport.HTML

        head = ''
        head += self._tracks.get_html_head_str()
        head += self._task_graph.get_html_head_str()
        head += self._file_table.get_html_head_str()
        html = html.replace(CrooHtmlReport.HEAD, head)

        body = ''
        body += self._tracks.get_html_body_str()
        body += self._task_graph.get_html_body_str()
        body += self._file_table.get_html_body_str()
        html = html.replace(CrooHtmlReport.BODY, body)

        return html
