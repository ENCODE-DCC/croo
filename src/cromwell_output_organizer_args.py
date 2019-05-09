#!/usr/bin/env python3
"""CromwellOutputOrganizer (COO): Cromwell output organizer based on
Cromwell's metadata.json.

Author:
    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import argparse
import sys


def parse_coo_arguments():
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
        '--out-def-json', required=True,
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

    if len(sys.argv[1:]) == 0:
        p.print_help()
        p.exit()
    # parse all args
    args = p.parse_args()

    # convert to dict
    args_d = vars(args)

    return args_d
