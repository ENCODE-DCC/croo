#!/usr/bin/env python3
"""CrooHtmlReportUCSCTracks, CrooHtmlReportUWTracks

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import textwrap
import urllib.parse

from autouri import GCSURI, S3URI, AbsPath, AutoURI


class CrooHtmlReportUCSCTracks(object):
    UCSC_TRACKS_TXT = 'croo.ucsc_tracks.{workflow_id}.txt'
    UCSC_TRACKS_URL = 'croo.ucsc_tracks.{workflow_id}.url'

    UCSC_BROWSER_QUERY_POS_PARAM = '&position='
    UCSC_BROWSER_QUERY_URL = 'http://genome.ucsc.edu/cgi-bin/hgTracks?db={db}&ignoreCookie=1{extra_param}&hgct_customText={encoded}'
    UCSC_BROWSER_TEXT_FORMAT = '{track_line} bigDataUrl="{url}"\n'
    HTML_TRACK_HUB_LINK = textwrap.dedent(
        """
        <a href="{url}" target="_blank">{title}</a>
        <br>
        <br>
    """
    )
    HTML_TRACK_HUB_TEXT = textwrap.dedent(
        """
        <b>{title}</b>
        <br>
        <div style="border:2px solid silver">
        <pre style="white-space:pre-wrap;word-wrap:break-word;margin:5px">
        {txt}
        </pre>
        </div>
        <br>
    """
    )

    def __init__(
        self,
        out_dir,
        workflow_id,
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
            extra_param = (
                CrooHtmlReportUCSCTracks.UCSC_BROWSER_QUERY_POS_PARAM
                + self._ucsc_genome_pos
            )
        else:
            extra_param = ''

        # save to TXT
        uri_txt = os.path.join(
            self._out_dir,
            CrooHtmlReportUCSCTracks.UCSC_TRACKS_TXT.format(
                workflow_id=self._workflow_id
            ),
        )

        # localize TXT
        # long URL doesn't work
        u = AutoURI(uri_txt)
        u.write(txt)

        url_trackhub_txt_file = None
        if isinstance(u, GCSURI):
            if self._public_gcs:
                url_trackhub_txt_file = u.get_public_url()

            elif self._use_presigned_url_gcs:
                url_trackhub_txt_file = u.get_presigned_url(
                    duration=self._duration_presigned_url_gcs,
                    private_key_file=self._gcp_private_key,
                )

        elif isinstance(u, S3URI):
            if self._use_presigned_url_s3:
                url_trackhub_txt_file = u.get_presigned_url(
                    duration=self._duration_presigned_url_s3
                )

        elif isinstance(u, AbsPath):
            if self._map_path_to_url:
                url_trackhub_txt_file = u.get_mapped_url(
                    map_path_to_url=self._map_path_to_url
                )
        html = ''

        url = CrooHtmlReportUCSCTracks.UCSC_BROWSER_QUERY_URL.format(
            db=self._ucsc_genome_db,
            extra_param=extra_param,
            encoded=urllib.parse.quote(txt),
        )
        html += CrooHtmlReportUCSCTracks.HTML_TRACK_HUB_LINK.format(
            title='UCSC browser tracks', url=url
        )

        if url_trackhub_txt_file is not None:
            url = CrooHtmlReportUCSCTracks.UCSC_BROWSER_QUERY_URL.format(
                db=self._ucsc_genome_db,
                extra_param=extra_param,
                encoded=urllib.parse.quote(url_trackhub_txt_file),
            )

            html += CrooHtmlReportUCSCTracks.HTML_TRACK_HUB_LINK.format(
                title='UCSC browser tracks (if the above link does not work)', url=url
            )

        html += CrooHtmlReportUCSCTracks.HTML_TRACK_HUB_TEXT.format(
            title='UCSC track hub plain text. Paste it directly to custom track edit box '
            'on UCSC genome browser.',
            txt=txt,
        )

        return html

    def add(self, url, track_line):
        self._items.append((url, track_line))

    def __make_ucsc_track_txt(self):
        result = ''
        for url, track_line in self._items:
            result += CrooHtmlReportUCSCTracks.UCSC_BROWSER_TEXT_FORMAT.format(
                track_line=track_line, url=url
            )
        return result
