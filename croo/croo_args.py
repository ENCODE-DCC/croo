#!/usr/bin/env python3
"""CRomwellOutputOrganizer (croo): Cromwell output organizer
command line arguments helper

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import argparse
import sys
from caper.caper_uri import (
    MAX_DURATION_SEC_PRESIGNED_URL_S3,
    MAX_DURATION_SEC_PRESIGNED_URL_GCS)


__version__ = '0.3.0'

def parse_croo_arguments():
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
        '--out-def-json',
        help='Output definition JSON file for a WDL file corresponding to '
             'the specified metadata.json file')
    p.add_argument(
        '--method', choices=('link', 'copy'), default='link',
        help='Method to localize files on output directory/bucket. '
        '"link" means a soft-linking and it\'s for local directory only. '
        'Original output files will be kept in Cromwell\'s output '
        'directory. '
        '"copy" makes copies of Cromwell\'s original outputs')
    p.add_argument(
        '--ucsc-genome-db',
        help='UCSC genome browser\'s "db=" parameter. '
             '(e.g. hg38 for GRCh38 and mm10 for mm10)')
    p.add_argument(
        '--ucsc-genome-pos',
        help='UCSC genome browser\'s "position=" parameter. '
             '(e.g. chr1:35000-40000)')
    p.add_argument(
        '--public-gcs', action='store_true',
        help='Your GCS (gs://) bucket is public.')
    p.add_argument(
        '--use-presigned-url-s3', action='store_true',
        help='Generate presigned URLS for files on s3://.')
    p.add_argument(
        '--use-presigned-url-gcs', action='store_true',
        help='Generate presigned URLS for files on gs://. --gcp-private-key '
             'must be provided.')
    p.add_argument(
        '--gcp-private-key',
        help='Private key file (JSON/PKCS12) of a service account on '
             'Google Cloud Platform (GCP). This key will be used to make '
             'presigned URLs on files on gs://.')
    p.add_argument(
        '--duration-presigned-url-s3',
        default=MAX_DURATION_SEC_PRESIGNED_URL_S3,
        help='Duration for presigned URLs for files on s3:// in seconds. ')
    p.add_argument(
        '--duration-presigned-url-gcs',
        default=MAX_DURATION_SEC_PRESIGNED_URL_GCS,
        help='Duration for presigned URLs for files on gs:// in seconds. ')
    p.add_argument(
        '--tsv-mapping-path-to-url',
        help='A 2-column TSV file with local path prefix and corresponding '
             'URL prefix. For example, using 1-line 2-col TSV file with '
             '/var/www[TAB]http://my.server.com will replace a local path '
             '/var/www/here/a.txt to a URL http://my.server.com/here/a.txt.')
    p.add_argument(
        '--out-dir', default='.',
        help='Output directory/bucket (LOCAL OR REMOTE). '
             'This can be a local path, gs:// or s3://. ')
    p.add_argument(
        '--tmp-dir',
        help='LOCAL temporary cache directory. '
             'All temporary files for auto-inter-storage transfer will be '
             'stored here. You can clean it up but will lose all cached files '
             'so that remote files will be re-downloaded.')
    p.add_argument(
        '--use-gsutil-over-aws-s3', action='store_true',
        help='Use gsutil instead of aws s3 CLI even for S3 buckets.')
    p.add_argument(
        '--http-user',
        help='Username to download data from private URLs')
    p.add_argument(
        '--http-password',
        help='Password to download data from private URLs')
    p.add_argument('-v', '--version', action='store_true',
                   help='Show version')

    if '-v' in sys.argv or '--version' in sys.argv:
        print(__version__)
        p.exit()

    if len(sys.argv[1:]) == 0:
        p.print_help()
        p.exit()
    # parse all args
    args = p.parse_args()

    if args.version is not None and args.version:
        print(__version__)
        p.exit()
    check_args(args)

    # convert to dict
    return vars(args)


def check_args(args):
    if args.use_presigned_url_gcs and args.gcp_private_key is None:
        raise ValueError(
            'Define --gcp-private-key to use presigned URLs on GCS'
            ' (--use-presigned-url-gcs).')
    if args.public_gcs and args.use_presigned_url_gcs:
        raise ValueError(
            'Public GCS bucket (--public-gcs) cannot be presigned '
            '(--use-presigned-url-gcs and --gcp-private-key). '
            'Choose one of them.')

