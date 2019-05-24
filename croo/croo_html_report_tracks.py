#!/usr/bin/env python3
"""CrooHtmlReportTracks

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""


class CrooHtmlReportTracks(object):
    HEAD = """
    <link rel="stylesheet" type="text/css" href=\
"http://epigenomegateway.wustl.edu/legacy/style.css" />
    <script type="text/javascript" src="http://epigenomegateway.wustl.edu/\
legacy/js/base.js"></script>
    <script type="text/javascript" src="http://epigenomegateway.wustl.edu/\
legacy/js/personality.js"></script>
    <script type="text/javascript" src="http://epigenomegateway.wustl.edu/\
legacy/js/embed.js"></script>
    """
    BODY = """
    """
    def __init__(self, html_root=None):
        self._html_root = html_root

    def get_html_head_str(self):
        return CrooHtmlReportTracks.HEAD

    def get_html_body_str(self):
        html = CrooHtmlReportTracks.BODY
        return html
