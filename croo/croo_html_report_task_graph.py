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
    def __init__(self):
        pass

    def get_html_head_str(self):
        return CrooHtmlReportTaskGraph.HEAD

    def get_html_body_str(self):
        html = CrooHtmlReportTaskGraph.BODY
        return html
