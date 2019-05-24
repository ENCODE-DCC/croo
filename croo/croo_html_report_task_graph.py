#!/usr/bin/env python3
"""CrooHtmlReportTaskGraph

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""


class CrooHtmlReportTaskGraph(object):
    HEAD = """
    """
    BODY = """
     """
    def __init__(self, html_root, use_rel_path_in_link=False):
        self._html_root = html_root
        self._use_rel_path_in_link = use_rel_path_in_link

    def get_html_head_str(self):
        return CrooHtmlReportTaskGraph.HEAD

    def get_html_body_str(self):
        html = CrooHtmlReportTaskGraph.BODY
        return html
