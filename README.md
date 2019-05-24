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
            [--use-rel-path-in-link] [--out-dir OUT_DIR] [--tmp-dir TMP_DIR]
            [--use-gsutil-over-aws-s3] [--http-user HTTP_USER]
            [--http-password HTTP_PASSWORD]
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
                        Cromwell's output directory. "copy" makes a copy of
                        Cromwell's original outputs
  --use-rel-path-in-link
                        Use relative path in link in file table in HTML
                        report. If your output directory is a cloud bucket
                        (GCS, AWS), then it is recommended not to activate
                        this flag unless you have correctly set up file
                        hosting on a cloud bucket. This will be useful if your
                        output directory is local but hosted by a web server
                        (e.g. Apache2)
  --out-dir OUT_DIR     Output directory/bucket (local or remote)
  --tmp-dir TMP_DIR     LOCAL temporary directory
  --use-gsutil-over-aws-s3
                        Use gsutil instead of aws s3 CLI even for S3 buckets.
  --http-user HTTP_USER
                        Username to download data from private URLs
  --http-password HTTP_PASSWORD
                        Password to download data from private URLs
```

## File table

Croo creates a file table in an HTML report file. Such table includes description and absolute paths for all outputs. You can also have clickable links for those outputs. Use `--use-rel-path-in-link` to make those links relative to the HTML file. This will be useful if you have an organized output directory generated by Croo on a local directory hosted by a web server. On cloud buckets (GCS and S3), it is not recommened to use `--use-rel-path-in-link` unless you have configured your bucket to host files.

## WDL customization

> **Optional**: Add the following comments to your WDL then Croo will be able to find an appropriate output definition JSON file for your WDL. Then you don't have to define them in command line arguments everytime you Croo.

```bash
#CROO out_def [URL_OUT_DEF_JSON_FILE_FOR_YOUR_WDL]
```

## Output definition JSON file

An output definition JSON file must be provided for a corresponding WDL file.

For the following example of [ENCODE ATAC-Seq pipeline](https://github.com/ENCODE-DCC/atac-seq-pipeline), `atac.bowtie2` is a task called in a `scatter {}` block iterating over biological replicates so that the type of an output variable `atac.bowtie2.bam` in a workflow level is `Array[File]`. Therefore, we need an index for the `scatter {}` iteration to have access to each file that `bam` points to. An inline expression like `${i}` (0-based) allows access to such index. `${basename}` refers to the basename of the original output file. BAM and flagstat log from `atac.bowtie2` will be transferred to different locations `align/repX/` and `qc/repX/`, respectively. `atac.qc_report` is a final task of a workflow gathering all QC logs so it's not called in a `scatter {}` block. There shouldn't be any scatter indices like `i0`, `i1`, `j0` and `j1`.

Croo also generates a final HTML report `croo.report.html` on `--out-dir`. This HTML report includes a file table summarizing all output files in a tree structure (split by `/`).

Example:
```json
{
  "atac.bowtie2": {
    "bam": {
      "path": "align/rep${i+1}/${basename}",
      "table": "Alignment/Replicate ${i+1}/Raw BAM from bowtie2"
    },
    "flagstat_qc": {
      "path": "qc/rep${i+1}/${basename}",
      "table": "QC and logs/Replicate ${i+1}/Samtools flagstat for Raw BAM"
    }
  },
  "atac.qc_report": {
    "report": {
      "path": "qc/final_qc_report.html",
      "table": "QC and logs/Final QC HTML report"
    },
    "qc_json": {
      "path": "qc/final_qc.json",
      "table": "QC and logs/Final QC JSON file"
    }
  }
}
```

More generally for subworkflows a definition JSON file looks like the following:
```json
{
  "[WORKFLOW_NAME].[TASK_NAME_OR_ALIAS]" : {
    "[OUT_VAR_NAME_IN_TASK]" : {
      "path": "[OUT_REL_PATH_DEF]",
      "table": "[FILE_TABLE_TREE_ITEM]"
    }
  },

  "[WORKFLOW_NAME].[SUBWORKFLOW_NAME_OR_ALIAS].[SUBSUBWORKFLOW_NAME_OR_ALIAS].[TASK_NAME_OR_ALIAS]" : {
    "[OUT_VAR_NAME_IN_TASK]" : {
      "path": "[OUT_REL_PATH_DEF]",
      "table": "[FILE_TABLE_TREE_ITEM]"
    }
  }
}
```

> **WARNING**: Unfortunately, for an output variable `[OUT_VAR_NAME_IN_TASK]` in a task Croo does not currently support `Array[File]` type. It only supports `File` type.
    ```
    task t1 {
        command {
            ...
        }
        output {
            Array[File] out_list  # NOT SUPPORTED
            File out  # SUPPORTED
        }
    }
    ```

`{ "path" : "[OUT_REL_PATH_DEF]", "table": "[FILE_TABLE_TREE_ITEM]" }` defines a final output destination and file table tree item. `[OUT_REL_PATH_DEF]` is a file path **RELATIVE** to the output directory species as `--out-dir`. The following inline expressions are allowed for `[OUT_REL_PATH_DEF]` and `[FILE_TABLE_TREE_ITEM]`. You can use basic Python expressions inside `${}`. For example, `${basename.split(".")[0]}` should be helpful to get the prefix of a file like `some_prefix.fastqs.gz`.

| Built-in variable | Type       | Description                                      |
|-------------------|------------|--------------------------------------------------|
| `basename`        | str        | Basename of file                                 | 
| `dirname`         | str        | Dirname of file                                  | 
| `full_path`       | str        | Full path of file                                | 
| `i`               | int        | 0-based index for main scatter loop              |
| `j`               | int        | 0-based index for nested scatter loop            |
| `k`               | int        | 0-based index for double-nested scatter loop     |
| `shard_idx`       | tuple(int) | tuple of indices for each dim.: (i, j, k, ...)   |

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
