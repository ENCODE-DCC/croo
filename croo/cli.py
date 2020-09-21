import argparse
import csv
import logging
import os
import sys

from autouri import GCSURI, S3URI

from . import __version__ as version
from .croo import Croo


def parse_croo_arguments():
    """Argument parser for Cromwell Output Organizer (COO)
    """
    p = argparse.ArgumentParser()
    p.add_argument(
        'metadata_json',
        help='Path, URL or URI for metadata.json for a workflow '
        'Example: /scratch/sample1/metadata.json, '
        'gs://some/where/metadata.json, '
        'http://hello.com/world/metadata.json',
    )
    p.add_argument(
        '--out-def-json',
        help='Output definition JSON file for a WDL file corresponding to '
        'the specified metadata.json file',
    )
    p.add_argument(
        '--method',
        choices=('link', 'copy'),
        default='link',
        help='Method to localize files on output directory/bucket. '
        '"link" means a soft-linking and it\'s for local directory only. '
        'Original output files will be kept in Cromwell\'s output '
        'directory. '
        '"copy" makes copies of Cromwell\'s original outputs',
    )
    p.add_argument(
        '--ucsc-genome-db',
        help='UCSC genome browser\'s "db=" parameter. '
        '(e.g. hg38 for GRCh38 and mm10 for mm10)',
    )
    p.add_argument(
        '--ucsc-genome-pos',
        help='UCSC genome browser\'s "position=" parameter. ' '(e.g. chr1:35000-40000)',
    )
    p.add_argument(
        '--public-gcs', action='store_true', help='Your GCS (gs://) bucket is public.'
    )
    p.add_argument(
        '--use-presigned-url-s3',
        action='store_true',
        help='Generate presigned URLS for files on s3://.',
    )
    p.add_argument(
        '--use-presigned-url-gcs',
        action='store_true',
        help='Generate presigned URLS for files on gs://. --gcp-private-key '
        'must be provided.',
    )
    p.add_argument(
        '--gcp-private-key',
        help='Private key file (JSON/PKCS12) of a service account on '
        'Google Cloud Platform (GCP). This key will be used to make '
        'presigned URLs on files on gs://.',
    )
    p.add_argument(
        '--duration-presigned-url-s3',
        type=int,
        default=S3URI.DURATION_PRESIGNED_URL,
        help='Duration for presigned URLs for files on s3:// in seconds. ',
    )
    p.add_argument(
        '--duration-presigned-url-gcs',
        type=int,
        default=GCSURI.DURATION_PRESIGNED_URL,
        help='Duration for presigned URLs for files on gs:// in seconds. ',
    )
    p.add_argument(
        '--tsv-mapping-path-to-url',
        help='A 2-column TSV file with local path prefix and corresponding '
        'URL prefix. For example, using 1-line 2-col TSV file with '
        '/var/www[TAB]http://my.server.com will replace a local path '
        '/var/www/here/a.txt to a URL http://my.server.com/here/a.txt.',
    )
    p.add_argument(
        '--out-dir',
        default='.',
        help='Output directory/bucket (LOCAL OR REMOTE). '
        'This can be a local path, gs:// or s3://. ',
    )
    p.add_argument(
        '--tmp-dir',
        help='LOCAL temporary cache directory. '
        'All temporary files for auto-inter-storage transfer will be '
        'stored here. You can clean it up but will lose all cached files '
        'so that remote files will be re-downloaded.',
    )
    p.add_argument(
        '--use-gsutil-for-s3',
        action='store_true',
        help='Use gsutil for direct tranfer between GCS and S3 buckets. '
        'Make sure that you have "gsutil" installed and configured '
        'to have access to credentials for GCS and S3 '
        '(e.g. ~/.boto or ~/.aws/credientials)',
    )
    p.add_argument(
        '--no-checksum',
        action='store_true',
        help='Always overwrite on output directory/bucket (--out-dir) '
        'even if md5-identical files (or soft links) already exist there. '
        'Md5 hash/filename/filesize checking will be skipped.',
    )
    p.add_argument('-v', '--version', action='store_true', help='Show version')
    p.add_argument(
        '-D', '--debug', action='store_true', help='Prints all logs >= DEBUG level'
    )

    if len(sys.argv[1:]) == 0:
        p.print_help()
        p.exit()
    if '-v' in sys.argv or '--version' in sys.argv:
        print(version)
        p.exit()

    args = p.parse_args()
    # convert to dict
    d_args = vars(args)

    return d_args


def check_args(args):
    """Check cmd line arguments are valid

    Args:
        args:
            dict of cmd line arguments
    """
    if args['use_presigned_url_gcs'] and args['gcp_private_key'] is None:
        raise ValueError(
            'Define --gcp-private-key to use presigned URLs on GCS'
            ' (--use-presigned-url-gcs).'
        )

    if args['public_gcs'] and args['use_presigned_url_gcs']:
        raise ValueError(
            'Public GCS bucket (--public-gcs) cannot be presigned '
            '(--use-presigned-url-gcs and --gcp-private-key). '
            'Choose one of them.'
        )

    if args['tmp_dir'] is None:
        pass
    elif args['tmp_dir'].startswith(('http://', 'https://')):
        raise ValueError('URL is not allowed for --tmp-dir')
    elif args['tmp_dir'].startswith(('gs://', 's3://')):
        raise ValueError('Cloud URI is not allowed for --tmp-dir')

    if args['out_dir'].startswith(('http://', 'https://')):
        raise ValueError('URL is not allowed for --out-dir')


def init_dirs(args):
    """More initialization for out/tmp directories since tmp
    directory is important for inter-storage transfer using
    Autouri

    Args:
        args:
            dict of cmd line arguments
    """
    if args['out_dir'].startswith(('gs://', 's3://')):
        if args['tmp_dir'] is None:
            args['tmp_dir'] = os.path.join(os.getcwd(), '.croo_tmp')
    else:
        args['out_dir'] = os.path.abspath(os.path.expanduser(args['out_dir']))
        os.makedirs(args['out_dir'], exist_ok=True)
        if args['tmp_dir'] is None:
            args['tmp_dir'] = os.path.join(args['out_dir'], '.croo_tmp')

    if args['tmp_dir'] is not None:
        args['tmp_dir'] = os.path.abspath(os.path.expanduser(args['tmp_dir']))


def init_autouri(args):
    """Initialize Autouri and its logger

    Args:
        args:
            dict of cmd line arguments
    """
    GCSURI.init_gcsuri(use_gsutil_for_s3=args['use_gsutil_for_s3'])

    # autouri's path to url mapping
    if args['tsv_mapping_path_to_url'] is not None:
        mapping_path_to_url = {}
        f = os.path.expanduser(args['tsv_mapping_path_to_url'])
        with open(f, newline='') as fp:
            reader = csv.reader(fp, delimiter='\t')
            for line in reader:
                mapping_path_to_url[line[0]] = line[1]
        args['mapping_path_to_url'] = mapping_path_to_url
    else:
        args['mapping_path_to_url'] = None


def init_logging(args):
    if args.get('debug'):
        log_level = 'DEBUG'
    else:
        log_level = 'INFO'
    logging.basicConfig(
        level=log_level, format='%(asctime)s|%(name)s|%(levelname)s| %(message)s'
    )
    # suppress filelock logging
    logging.getLogger('filelock').setLevel('CRITICAL')


def main():
    args = parse_croo_arguments()

    check_args(args)
    init_dirs(args)
    init_autouri(args)
    init_logging(args)

    co = Croo(
        metadata_json=args['metadata_json'],
        out_def_json=args['out_def_json'],
        out_dir=args['out_dir'],
        tmp_dir=args['tmp_dir'],
        soft_link=args['method'] == 'link',
        ucsc_genome_db=args['ucsc_genome_db'],
        ucsc_genome_pos=args['ucsc_genome_pos'],
        use_presigned_url_s3=args['use_presigned_url_s3'],
        use_presigned_url_gcs=args['use_presigned_url_gcs'],
        duration_presigned_url_s3=args['duration_presigned_url_s3'],
        duration_presigned_url_gcs=args['duration_presigned_url_gcs'],
        public_gcs=args['public_gcs'],
        gcp_private_key=args['gcp_private_key'],
        map_path_to_url=args['mapping_path_to_url'],
        no_checksum=args['no_checksum'],
    )

    co.organize_output()

    return 0


if __name__ == '__main__':
    main()
