#!/usr/bin/env python3
"""CrooHtmlReportUCSCTracks, CrooHtmlReportUWTracks

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import urllib.parse
from caper.caper_uri import CaperURI


class CrooHtmlReportUCSCTracks(object):
    UCSC_TRACKS_TXT = 'croo.ucsc_tracks.{workflow_id}.txt'
    UCSC_TRACKS_URL = 'croo.ucsc_tracks.{workflow_id}.url'

    UCSC_BROWSER_QUERY_POS_PARAM = '&position='
    UCSC_BROWSER_QUERY_URL = 'http://genome.ucsc.edu/cgi-bin/hgTracks?db={db}&ignoreCookie=1{extra_param}&hgct_customText={encoded}'
    UCSC_BROWSER_TEXT_FORMAT = '{track_line} bigDataUrl="{url}"\n'
    HTML_TRACK_HUB_LINK = """
<a href="{url}" target="_blank">UCSC browser tracks</a>
<br>
<br>"""
    HTML_TRACK_HUB_TEXT = """
<b>{title}</b>
<br>
<div style="border:2px solid silver">
<pre style="white-space:pre-wrap;word-wrap:break-word;margin:5px">
{txt}
</pre>
</div>
<br>"""

    def __init__(self, out_dir, workflow_id,
                 ucsc_genome_db=None,
                 ucsc_genome_pos=None):
        self._out_dir = out_dir
        self._workflow_id = workflow_id
        self._ucsc_genome_db = ucsc_genome_db
        self._ucsc_genome_pos = ucsc_genome_pos
        self._items = []

    def get_html_body_str(self):
        """HTML for browser track
        This HTML section provides:
            1) A plain text for UCSC genome browser &hgct_customText=
                - This is written to a text file (.txt) on the output directory
            2) An encoded URL for UCSC genome browser &hgct_customText=
            3) Clickable href link
                - Full URL is written to a text file (.url) on the output directory
        """
        if self._ucsc_genome_db is None:
            return ''
        txt = self.__make_ucsc_track_txt()
        if txt is None or txt == '':
            return ''
        if self._ucsc_genome_pos is not None:
            extra_param = CrooHtmlReportUCSCTracks.UCSC_BROWSER_QUERY_POS_PARAM \
                    + self._ucsc_genome_pos
        else:
            extra_param = ''

        encoded = urllib.parse.quote(txt)
        url = CrooHtmlReportUCSCTracks.UCSC_BROWSER_QUERY_URL.format(
            db=self._ucsc_genome_db,
            extra_param=extra_param,
            encoded=encoded)

        html = ''
        html += CrooHtmlReportUCSCTracks.HTML_TRACK_HUB_LINK.format(
            url=url)
        html += CrooHtmlReportUCSCTracks.HTML_TRACK_HUB_TEXT.format(
            title='UCSC track hub plain text',
            txt=txt)
        html += CrooHtmlReportUCSCTracks.HTML_TRACK_HUB_TEXT.format(
            title='UCSC track hub encoded URL '
                  '(Use this for browser\'s parameter &hgct_customText=)',
            txt=encoded)

        # save to TXT
        uri_txt = os.path.join(
            self._out_dir,
            CrooHtmlReportUCSCTracks.UCSC_TRACKS_TXT.format(
                workflow_id=self._workflow_id))
        CaperURI(uri_txt).write_str_to_file(txt)

        # save to URL
        uri_url = os.path.join(
            self._out_dir,
            CrooHtmlReportUCSCTracks.UCSC_TRACKS_URL.format(
                workflow_id=self._workflow_id))
        CaperURI(uri_url).write_str_to_file(url)

        return html

    def add(self, url, track_line):
        self._items.append((url, track_line))

    def __make_ucsc_track_txt(self):
        result = ''
        for url, track_line in self._items:
            result += CrooHtmlReportUCSCTracks.UCSC_BROWSER_TEXT_FORMAT.format(
                track_line=track_line,
                url=url)
        return result
