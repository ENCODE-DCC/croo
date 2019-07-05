#!/usr/bin/env python3
"""CRomwellOutputOrganizer (croo): Cromwell output organizer
command line arguments helper

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import argparse
import sys


__version__ = '0.1.7'

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
        '"copy" makes a copy of Cromwell\'s original outputs')
    p.add_argument(
        '--use-rel-path-in-link', action='store_true',
        help='Use relative path in link in file table in HTML report. '
             'If your output directory is a cloud bucket (GCS, AWS), then '
             'it is recommended not to activate this flag unless you have '
             'correctly set up file hosting on a cloud bucket. '
             'This will be useful if your output directory is local but '
             'hosted by a web server (e.g. Apache2)')
    p.add_argument(
        '--out-dir', default='.', help='Output directory/bucket '
                                       '(local or remote)')
    p.add_argument(
        '--tmp-dir', help='LOCAL temporary directory')
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

    # convert to dict
    args_d = vars(args)

    return args_d

