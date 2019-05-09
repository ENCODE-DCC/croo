# Cromweller Output Organizer (COO)

COO is a Python package for organizing outputs from [Cromwell](https://github.com/broadinstitute/cromwell/).

## Introduction

COO takes in `metadata.json` which is generated from Cromwell and parses it to get information about all outputs. Then it makes a copy (or a soft link) of each output file as described in an output definition JSON file specified by `--out-def-json`.

## Features

* **Automatic file transfer between local/cloud storages**: For example, the following command line works. You can define URIs instead of local path for any command line arguments. The following command line reads from remote metadata JSON file (`gs://some/where/metadata.json`) and output definition JSON file (`s3://over/here/atac.out_def.json`) and write organized outputs to `gs://your/final/out/bucket`.
  	```bash
  	$ coo gs://some/where/metadata.json --out-def-json s3://over/here/atac.out_def.json --out-dir gs://your/final/out/bucket
  	```

* **Soft-linking** (local storage only): COO defaults to make soft links instead of copying for local-to-local file transfer (local output file defined in a metadata JSON vs. local output directory specifed by `--out-dir`). In order to force copying instead of soft-linking regardless of a storage type then use `--method copy`. Local-to-cloud and cloud-to-local file transfer always uses `copy` method.


## Output definition JSON file

An output definition JSON file must be provided for a corresponding WDL file.

For the following example of [ENCODE ATAC-Seq pipeline](https://github.com/ENCODE-DCC/atac-seq-pipeline), `atac.bowtie2` is a task called in a `scatter {}` block iterating over biological replicates so that the type of an output variable `atac.bowtie2.bam` in a workflow level is `Array[File]`. Therefore, we need an index for the `scatter {}` iteration to have access to each file that `bam` points to. An inline expression like `${i}` (0-based) allows access to such index. `${basename}` refers to the basename of the original output file. BAM and flagstat log from `atac.bowtie2` will be transferred to different locations `align/repX/` and `qc/repX/`, respectively. `atac.qc_report` is a final task of a workflow gathering all QC logs so it's not called in a `scatter {}` block. There shouldn't be any scatter indices like `i0`, `i1`, `j0` and `j1`.

Example:
```json
{
  "atac.bowtie2": {
    "bam": {
      "path": "align/rep${i+1}/${basename}",
    },
    "flagstat_qc": {
      "path": "qc/rep${i+1}/${basename}",
    }
  },
  "atac.qc_report": {
    "report": {
      "path": "qc/final_qc_report.html"
    },
    "qc_json": {
      "path": "qc/final_qc.json"
    }
  }
}
```

More generally for subworkflows a definition JSON file looks like the following:
```json
{
  "[WORKFLOW_NAME].[TASK_NAME_OR_ALIAS]" : {
    "[OUT_VAR_NAME_IN_TASK]" : {
      "path": "[OUT_REL_PATH_DEF]"
    }
  },

  "[WORKFLOW_NAME].[SUBWORKFLOW_NAME_OR_ALIAS].[SUBSUBWORKFLOW_NAME_OR_ALIAS].[TASK_NAME_OR_ALIAS]" : {
    "[OUT_VAR_NAME_IN_TASK]" : {
      "path": "[OUT_REL_PATH_DEF]"
    }
  }
}
```

> **WARNING**: Unfortunately, for an output variable `[OUT_VAR_NAME_IN_TASK]` in a task COO does not currently support `Array[File]` type. It only supports `File` type.
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

`{ "path" : "[OUT_REL_PATH_DEF]" }` defines a final output destination. It's a file path **RELATIVE** to the output directory species as `--out-dir`. The following inline expressions are allowe for `[OUT_REL_PATH_DEF]`. You can use basic Python expressions inside `${}`. For example, `${basename.split(".")[0]}` should be helpful to get the prefix of a file like `some_prefix.fastqs.gz`.

| Built-in variable | Type       | Description                                      |
|-------------------|------------|--------------------------------------------------|
| `basename`        | str        | Basename of file                                 | 
| `dirname`         | str        | Dirname of file                                  | 
| `full_path`       | str        | Full path of file                                | 
| `i`               | int        | 0-based index for main scatter loop              |
| `j`               | int        | 0-based index for nested scatter loop            |
| `k`               | int        | 0-based index for double-nested scatter loop     |
| `shard_idx`       | tuple(int) | tuple of indices for each dim.: (i, j, k, ...)   |

## Install

We will add PIP installation later. Until then `git clone` it and manually add `coo` to your environment variable `PATH` in your BASH startup scripts (`~/.bashrc`). Make sure that you have `python3` >=3.3 installed on your system.

```bash
$ git clone https://github.com/ENCODE-DCC/cromwell_output_organizer
$ echo "export PATH=\"\$PATH:$PWD/cromwell_output_organizer\"" >> ~/.bashrc
```

## Inter-storage file transfer

In order to use auto-transfer between local/cloud storages, you need to configure for corresponding cloud CLI (`gsutil` or `aws`) for a target storage. Refer to [here](#requirements) for details.

> **WARNING**: COO does not ensure a fail-safe file transfer when it's interrupted by user or system. Also, there can be race conditions if multiple users try to access/copy files. This will be later addressed in the future release. Until then DO NOT interrupt COO until you see the following `copying done` message.


## Usage

```bash
usage: coo [-h] --out-def-json OUT_DEF_JSON [--method {link,copy}]
           [--out-dir OUT_DIR] [--tmp-dir TMP_DIR] [--use-gsutil-over-aws-s3]
           [--http-user HTTP_USER] [--http-password HTTP_PASSWORD]
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
  --out-dir OUT_DIR     Output directory/bucket
  --tmp-dir TMP_DIR     Temporary local directory
  --use-gsutil-over-aws-s3
                        Use gsutil instead of aws s3 CLI even for S3 buckets.
  --http-user HTTP_USER
                        Username to download data from private URLs
  --http-password HTTP_PASSWORD
                        Password to download data from private URLs

```

## Requirements

* `python` >= 3.3, `pip3`, `wget` and `curl`

	Debian:
	```bash
	$ sudo apt-get install python3 python3-pip wget curl
	```
	Others:
	```bash
	$ sudo yum install python3 epel-release wget curl
	```

* [gsutil](https://cloud.google.com/storage/docs/gsutil_install): Run the followings to configure for gsutil:
	```bash
	$ gcloud auth login --no-launch-browser
	$ gcloud auth application-default --no-launch-browser
	```

* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-linux.html): Run the followings to configure for AWS CLI:
	```bash
	$ aws configure
	```
