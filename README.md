# Cromwell Output Organizer (Croo)

Croo is a Python package for organizing outputs from [Cromwell](https://github.com/broadinstitute/cromwell/).

## Introduction

Croo parses `metadata.json` which is an output from Cromwell and makes an organized directory with a copy (or a soft link) of each output file as described in an output definition JSON file specified by `--out-def-json`.

## Features

* **Automatic file transfer between local/cloud storages**: For example, the following command line works. You can define URIs instead of local path for any command line arguments. The following command line reads from remote metadata JSON file (`gs://some/where/metadata.json`) and output definition JSON file (`s3://over/here/atac.out_def.json`) and write organized outputs to `gs://your/final/out/bucket`.
  	```bash
  	$ croo gs://some/where/metadata.json --out-def-json s3://over/here/atac.out_def.json --out-dir gs://your/final/out/bucket
  	```

* **Soft-linking** (local storage only): Croo defaults to make soft links instead of copying for local-to-local file transfer (local output file defined in a metadata JSON vs. local output directory specifed by `--out-dir`). In order to force copying instead of soft-linking regardless of a storage type then use `--method copy`. Local-to-cloud and cloud-to-local file transfer always uses `copy` method.

* **File table with clickable links**: Croo generates an HTML report with a file table, which is a summary/description of all output files with clickable links for them. Examples: [ATAC](https://storage.googleapis.com/encode-pipeline-output-definition/out_example_atac/croo.report.904b709b-ecb4-42c8-aa81-ca19a15c4bb6.html) and [ChIP](https://storage.googleapis.com/encode-pipeline-output-definition/out_example_chip/croo.report.4665a7c4-c0ac-4e0b-9ac4-3c4d30474d20.html).

* **UCSC browser tracks**: Clickable link for UCSC browser tracks in the HTML report.
    ```bash
    $ croo ... --ucsc-genome-db hg38
    ```

* **Task graph**

## Install

Install it through PIP.
```bash
$ pip install croo
```

Or `git clone` it and manually add `croo` to your environment variable `PATH` in your BASH startup scripts (`~/.bashrc`). Make sure that you have `python3` >=3.3 installed on your system.

```bash
$ git clone https://github.com/ENCODE-DCC/croo
$ echo "export PATH=\"\$PATH:$PWD/croo/bin\"" >> ~/.bashrc
```

## Inter-storage file transfer

In order to use auto-transfer between local/cloud storages, you need to configure for corresponding cloud CLI (`gsutil` or `aws`) for a target storage. Refer to [here](#requirements) for details.

> **WARNING**: Croo does not ensure a fail-safe file transfer when it's interrupted by user or system. Also, there can be race conditions if multiple users try to access/copy files. This will be later addressed in the future release. Until then DO NOT interrupt Croo until you see the following `copying done` message.


## Usage

Croo reads `METADATA_JSON` generated from Cromwell and makes an organized output directory on `OUT_DIR_OR_BUCKET`. You need an `OUT_DEF_JSON` for a WDL associated with `METADATA_JSON` file. See [examples](examples/) for [ATAC-Seq](https://github.com/ENCODE-DCC/atac-seq-pipeline/blob/master/atac.wdl) and [ChIP-Seq](https://github.com/ENCODE-DCC/chip-seq-pipeline2/blob/master/chip.wdl) pipelines. Also see [details](#output-definition-json-file) about how to make a output definition JSON file for your own WDL. You can also define `OUT_DEF_JSON` [in your WDL as a comment](#wdl-customization) to avoid repeatedly defining it in command line arguments.


```bash
$ croo [METADATA_JSON] --out-def-json [OUT_DEF_JSON] --out-dir [OUT_DIR_OR_BUCKET]
```

```
usage: croo [-h] [--out-def-json OUT_DEF_JSON] [--method {link,copy}]
            [--ucsc-genome-db UCSC_GENOME_DB]
            [--ucsc-genome-pos UCSC_GENOME_POS] [--public-gcs]
            [--use-presigned-url-s3] [--use-presigned-url-gcs]
            [--gcp-private-key GCP_PRIVATE_KEY]
            [--duration-presigned-url-s3 DURATION_PRESIGNED_URL_S3]
            [--duration-presigned-url-gcs DURATION_PRESIGNED_URL_GCS]
            [--tsv-mapping-path-to-url TSV_MAPPING_PATH_TO_URL]
            [--out-dir OUT_DIR] [--tmp-dir TMP_DIR] [--use-gsutil-over-aws-s3]
            [--http-user HTTP_USER] [--http-password HTTP_PASSWORD] [-v]
            metadata_json

positional arguments:
  metadata_json         Path, URL or URI for metadata.json for a workflow
                        Example: /scratch/sample1/metadata.json,
                        gs://some/where/metadata.json,
                        http://hello.com/world/metadata.json

optional arguments:
  -h, --help            show this help message and exit
  --out-def-json OUT_DEF_JSON
                        Output definition JSON file for a WDL file
                        corresponding to the specified metadata.json file
  --method {link,copy}  Method to localize files on output directory/bucket.
                        "link" means a soft-linking and it's for local
                        directory only. Original output files will be kept in
                        Cromwell's output directory. "copy" makes copies of
                        Cromwell's original outputs
  --ucsc-genome-db UCSC_GENOME_DB
                        UCSC genome browser's "db=" parameter. (e.g. hg38 for
                        GRCh38 and mm10 for mm10)
  --ucsc-genome-pos UCSC_GENOME_POS
                        UCSC genome browser's "position=" parameter. (e.g.
                        chr1:35000-40000)
  --public-gcs          Your GCS (gs://) bucket is public.
  --use-presigned-url-s3
                        Generate presigned URLS for files on s3://.
  --use-presigned-url-gcs
                        Generate presigned URLS for files on gs://. --gcp-
                        private-key must be provided.
  --gcp-private-key GCP_PRIVATE_KEY
                        Private key file (JSON/PKCS12) of a service account on
                        Google Cloud Platform (GCP). This key will be used to
                        make presigned URLs on files on gs://.
  --duration-presigned-url-s3 DURATION_PRESIGNED_URL_S3
                        Duration for presigned URLs for files on s3:// in
                        seconds.
  --duration-presigned-url-gcs DURATION_PRESIGNED_URL_GCS
                        Duration for presigned URLs for files on gs:// in
                        seconds.
  --tsv-mapping-path-to-url TSV_MAPPING_PATH_TO_URL
                        A 2-column TSV file with local path prefix and
                        corresponding URL prefix. For example, using 1-line
                        2-col TSV file with /var/www[TAB]http://my.server.com
                        will replace a local path /var/www/here/a.txt to a URL
                        http://my.server.com/here/a.txt.
  --out-dir OUT_DIR     Output directory/bucket (LOCAL OR REMOTE). This can be
                        a local path, gs:// or s3://.
  --tmp-dir TMP_DIR     LOCAL temporary cache directory. All temporary files
                        for auto-inter-storage transfer will be stored here.
                        You can clean it up but will lose all cached files so
                        that remote files will be re-downloaded.
  --use-gsutil-over-aws-s3
                        Use gsutil instead of aws s3 CLI even for S3 buckets.
  --http-user HTTP_USER
                        Username to download data from private URLs
  --http-password HTTP_PASSWORD
                        Password to download data from private URLs
  -v, --version         Show version
```

## Original directory vs. Organized directory

Croo makes a link/copy (controlled by `--method copy/link`, `link` by default) of each file on Cromwell's original output directory.

    > **IMPORTANT**: Linking is possible only if those two directories have the same storage types. For example, local vs. local and `gs://` vs. `gs://`). Otherwise Croo will always make copies.

Clickable HTML links and USCS genome browser tracks on the HTML report always point to files on THE ORGANIZED DIRECTORY (`--out-dir`).

For example, your original outputs are on `gs://` and you organize it on your local storage then those clickable links and genome browser tracks will not work unless you set up a web server hosting those files and define a proper mapping from a local path to a URL. See [this section](#ucsc-browser-tracks) for details.

    > **IMPORTANT**: We recommmend to organize outputs on the same storage type. For example, organize outputs on `gs://` for original Cromwell outputs on `gs://`. `croo ... --out-dir gs://some/where/organized`.

## File table

Croo creates a file table in an HTML report file. Such table includes description, absolute paths and URLs for all outputs. You can also have clickable links for those outputs if you have correctly defined parameters described in the [section](#ucsc-browser-tracks). It also makes 3-col TSV file (`croo.filetable.[WORKFLOW_ID].tsv`) which has "Description", "Absolute Path" and "URL" for each output file.

Clickable links on a file table works a bit differently from UCSC browser tracks. They are both URLs but UCSC browser strictly wants to have a **PUBLIC** URL. For example, a clickable link pointing to a file on a private bucket can be opened on your web browser since you have already authenticated yourself for the private bucket so your web browser takes care of all authentication stuffs.

## UCSC Browser tracks

Croo creates UCSC genome browser tracks. Define `--ucsc-genome-db` for your genome (e.g. `hg38` for GRCh38 and `mm10` for mm10). `--ucsc-genome-pos` is optional to specify a genome position (e.g. `chr1:1000-4000`).

UCSC browsers can only take a **PUBLIC** URL for big genomic data file (e.g. `.bigWig`, `.bigBed`, `.bam`, ...). 

1) Local: If you have organized outputs on your local stroage then you should have a web server (e.g. Apache2) to host files to be visualized. Also you need to define a mapping from local path to URL. Make a TSV file for `--tsv-mapping-path-to-url`. Such 2-col TSV file which looks like the following (`LOCAL_PATH_PREFIX [TAB] URL_PREFIX`):

    ```
    /your/local/storage http://your.server/somewhere
    /your/lab/storage http://your.server/lab/directory
    ```
  
    Any filename prefixed with `col-1` will be replace with `col-2`. `col-1` is usually your local output directory specified by `--out-dir` or a working directory.

2) GCS: If your bucket is public then simply add `--public-gcs` and skip this step. You can make a presinged URL for any file on your private GCS bucket. Add `--use-presigned-url-gcs` to Croo command line arguments. You need to have a service account on your Google Cloud project and provide a private key file `--gcp-private-key` for the service account. See [this](https://cloud.google.com/storage/docs/access-control/signing-urls-with-helpers) to make a new service account and get a key file from it.

    > **WARNING**: This presigned URL is PUBLIC and will expire in `--duration-presigned-url-gcs` seconds (604800 sec = 1 week by default).

3) AWS: If your bucket is public then simply skip this step. Add `--use-presigned-url-s3` to Croo command line arguments. You can make a presinged URL for any file on your private S3 bucket.

    > **WARNING**: This presigned URL is PUBLIC and will expire in `--duration-presigned-url-s3` seconds (604800 sec = 1 week by default).

It also makes a USCS track hub text file (`croo.ucsc_tracks.[WORKFLOW_ID].txt`).

## Using presign URLs for cloud buckets (AWS S3 and GCS)

Presiged URLs are **PUBLIC** and Croo's outputs have those URLs in some files (starting with `croo.*.[WORKFLOW_ID].*` on your output directory/bucket `--out-dir`). Make sure that you keep those outputs in a secure place.

Example Croo files:
```
croo.filetable.b8da424d-5704-4350-8e41-a979389dcbed.tsv
croo.report.b8da424d-5704-4350-8e41-a979389dcbed.html
croo.ucsc_tracks.b8da424d-5704-4350-8e41-a979389dcbed.txt
croo.ucsc_tracks.b8da424d-5704-4350-8e41-a979389dcbed.url
```

Croo will make new presign URLs for all outputs everytime you run it. Default life time of those presigned URLs is 1 week.


## WDL customization

> **Optional**: Add the following comments to your WDL then Croo will be able to find an appropriate output definition JSON file for your WDL. Then you don't have to define them in command line arguments everytime you Croo.

```bash
#CROO out_def [URL_OUT_DEF_JSON_FILE_FOR_YOUR_WDL]
```

## Output definition JSON file

See [this](docs/OUT_DEF_JSON.md) document for details.

## Requirements

* [gsutil](https://cloud.google.com/storage/docs/gsutil_install): Run the followings to configure for gsutil:
	```bash
	$ gcloud auth login --no-launch-browser
	$ gcloud auth application-default --no-launch-browser
	```

* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-linux.html): Run the followings to configure for AWS CLI:
	```bash
	$ aws configure
	```
