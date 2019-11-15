# Output definition JSON file

An output definition JSON file must be provided for a corresponding WDL file.

## General

For the following example of [ENCODE ATAC-Seq pipeline](https://github.com/ENCODE-DCC/atac-seq-pipeline), `atac.align` is a task called in a `scatter {}` block iterating over biological replicates so that the type of an output variable `atac.align.bam` in a workflow level is `Array[File]`. Therefore, we need an index for the `scatter {}` iteration to have access to each file that `bam` points to. An inline expression like `${i}` (0-based) allows access to such index. `${basename}` refers to the basename of the original output file. BAM and `SAMstats` log from `atac.align` will be transferred to different locations `align/repX/` and `qc/repX/`, respectively. `atac.qc_report` is a final task of a workflow gathering all QC logs so it's not called in a `scatter {}` block. There shouldn't be any scatter indices like `i0`, `i1`, `j0` and `j1`.

Croo also generates a final HTML report `croo.report.[WORKFLOW_ID].html` on `--out-dir`. This HTML report includes a file table summarizing all output files in a tree structure (split by `/`) and a clickable link for UCSC browser tracks.

Example:
```json
{
  "atac.align": {
    "bam": {
      "path": "align/rep${i+1}/${basename}",
      "table": "Alignment/Replicate ${i+1}/Raw BAM from aligner",
      "node": "[shape=box style=\"filled, rounded\" fillcolor=lightyellow label=\"BAM\"]",
      "subgraph": "cluster_rep${i+1}"
    },
    "samstat_qc": {
      "path": "qc/rep${i+1}/${basename}",
      "table": "QC and logs/Replicate ${i+1}/SAMstats log for Raw BAM",
      "node": "[shape=oval style=\"filled\" fillcolor=gainsboro fontsize=6 margin=0 label=\"SAMstats\nQC\"]",
      "subgraph": "cluster_rep${i+1}"
    }
  },
  "atac.macs2_signal_track": {
    "pval_bw": {
      "path": "signal/rep${i+1}/${basename}",
      "table": "Signal/Replicate ${i+1}/MACS2 signal track (p-val)",
      "ucsc_track": "track type=bigWig name=\"MACS2 p-val (rep${i+1})\" priority=${i+1} smoothingWindow=off maxHeightPixels=80:60:40 color=255,0,0 autoScale=off viewLimits=0:40 visibility=full",
      "node": "[shape=box style=\"filled, rounded\" fillcolor=lightyellow label=\"BW\np-val\"]",
      "subgraph": "cluster_rep${i+1}"
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
  },

  "inputs": {
    "atac.fastqs_rep1_R1": {
      "node": "[shape=box style=\"filled, rounded\" fillcolor=pink label=\"FASTQ\nR1 (${i+1})\"]",
      "subgraph": "cluster_rep1"
    },
    "atac.fastqs_rep1_R2": {
      "node": "[shape=box style=\"filled, rounded\" fillcolor=pink label=\"FASTQ\nR2 (${i+1})\"]",
      "subgraph": "cluster_rep1"
    },
    "atac.fastqs_rep2_R1": {
      "node": "[shape=box style=\"filled, rounded\" fillcolor=pink label=\"FASTQ\nR1 (${i+1})\"]",
      "subgraph": "cluster_rep2"
    },
    "atac.fastqs_rep2_R2": {
      "node": "[shape=box style=\"filled, rounded\" fillcolor=pink label=\"FASTQ\nR2 (${i+1})\"]",
      "subgraph": "cluster_rep2"
    },
    "atac.bams": {
      "node": "[shape=box style=\"filled, rounded\" fillcolor=pink label=\"BAM\"]",
      "subgraph": "cluster_rep${i+1}"
    }
  },

  "task_graph_template": {
    "graph [rankdir=LR nodesep=0.1 ranksep=0.3]": null,
    "node [shape=box fontsize=9 margin=0.05 penwidth=0.5 height=0 fillcolor=lightcyan color=darkgrey style=filled]": null,
    "edge [arrowsize=0.5 color=darkgrey penwidth=0.5]": null,
    "subgraph cluster_pooled_rep":{"style": "\"filled, dashed\"", "fontsize": "9", "color": "darkgrey", "penwidth": "0.5", "fillcolor": "oldlace", "labeljust": "\"l\"", "label": "\"Pooled replicate\""},
    "subgraph cluster_rep1":  {"style": "\"filled, dashed\"", "fontsize": "9", "color": "darkgrey", "penwidth": "0.5", "fillcolor": "honeydew", "labeljust": "\"l\"", "label": "\"Replicate 1\""},
    "subgraph cluster_rep2":  {"style": "\"filled, dashed\"", "fontsize": "9", "color": "darkgrey", "penwidth": "0.5", "fillcolor": "honeydew", "labeljust": "\"l\"", "label": "\"Replicate 2\""}
  }
}
```

More generally for subworkflows a definition JSON file looks like the following:
```json
{
  "[WORKFLOW_NAME].[TASK_NAME_OR_ALIAS]" : {
    "[OUT_VAR_NAME_IN_TASK]" : {
      "path": "[OUT_REL_PATH_DEF]",
      "table": "[FILE_TABLE_TREE_ITEM]",
      "ucsc_track": "[UCSC_TRACK_FORMAT]",
      "node": "[NODE_FORMAT_WRAPPED_IN_SQUARE_BRACKETS]",
      "subgraph": "[SUBGRAPH_NAME_IN_GRAPH]"
    }
  },

  "[WORKFLOW_NAME].[SUBWORKFLOW_NAME_OR_ALIAS].[SUBSUBWORKFLOW_NAME_OR_ALIAS].[TASK_NAME_OR_ALIAS]" : {
    "[OUT_VAR_NAME_IN_TASK]" : {
      "path": "[OUT_REL_PATH_DEF]",
      "table": "[FILE_TABLE_TREE_ITEM]",
      "ucsc_track": "[UCSC_TRACK_FORMAT]",
      "node": "[NODE_FORMAT_WRAPPED_IN_SQUARE_BRACKETS]",
      "subgraph": "[SUBGRAPH_NAME_IN_GRAPH]"
    }
  }

  "inputs": {
    [WORKFLOW_NAME].[INPUT_VAR_NAME] : {
      "node": "[NODE_FORMAT_WRAPPED_IN_SQUARE_BRACKETS]",
      "subgraph": "[SUBGRAPH_NAME_IN_GRAPH]"
    }
  },

  "task_graph_template": {
    [ANY_KEY]: [ANY_VAL],
    [ANY_KEY2]: null,
    [Any_KEY3]: {
      [Any_KEY3_1]: [ANY_VAL3_1],
      ...
    }
    ...
  }
}
```

## Task graph

Optionally, you can define inputs (see the above `"inputs"` JSON object) to show them in a task graph as starting nodes. Otherwise, the task graph will not show any inputs. Croo is an output organize so that it does not modify (e.g. presigning bucket URLs) those inputs.

For the scatter indices, the same mechanics apply to multi-dimensional `File` inputs (e.g. `Array[Array[File]]` -> `i, j`). Each dimension's index is converted into inline expression variables `i`, `j` and `k` up to 3 dimesions.

We have another JSON object for task graph's template (see the above "task_graph_template" JSON object). This template JSON will be converted into an equivalent Graphviz DOT. Any key/value pair will be converted into `KEY = VAL;` in a DOT, recursively for JSON in JSON. A key with a value `None` or `null` will be converted into `KEY;` alone. An equivalent DOT template converted from the above `"task_graph_template"` JSON object looks like the following. This is useful to define default style for all tasks while individual task-output's style can be defined in `"node"`.

```dot
digraph D {
        graph [rankdir=LR nodesep=0.1 ranksep=0.3];
        node [shape=box fontsize=9 margin=0.05 penwidth=0.5 height=0 fillcolor=lightcyan color=darkgrey style=filled];
        edge [arrowsize=0.5 color=darkgrey penwidth=0.5];
        subgraph cluster_pooled_rep {
                style = "filled, dashed";
                fontsize = 9;
                color = darkgrey;
                penwidth = 0.5;
                fillcolor = oldlace;
                labeljust = "l";
                label = "Pooled replicate";
        }
        subgraph cluster_rep1 {
                style = "filled, dashed";
                fontsize = 9;
                color = darkgrey;
                penwidth = 0.5;
                fillcolor = honeydew;
                labeljust = "l";
                label = "Replicate 1";
        }
        subgraph cluster_rep2 {
                style = "filled, dashed";
                fontsize = 9;
                color = darkgrey;
                penwidth = 0.5;
                fillcolor = honeydew;
                labeljust = "l";
                label = "Replicate 2";
        }
}
```

## File table

`{ "path" : "[OUT_REL_PATH_DEF]", "table": "[FILE_TABLE_TREE_ITEM]" }` defines a final output destination and file table tree item. `[OUT_REL_PATH_DEF]` is a file path **RELATIVE** to the output directory species as `--out-dir`. The following inline expressions are allowed for `[OUT_REL_PATH_DEF]` and `[FILE_TABLE_TREE_ITEM]`. You can use basic Python expressions inside `${}`. For example, `${basename.split(".")[0]}` should be helpful to get the prefix of a file like `some_prefix.fastqs.gz`.

## USCS browser track

`"ucsc_track": "[UCSC_TRACK_FORMAT]"` defines UCSC browser's custom track text format except for one parameter `bigDataUrl=` (to define a public URL for a file). See [this](https://genome.ucsc.edu/FAQ/FAQlink.html) for details.
> **WARNING**: DO NOT INCLUDE ANY PARAMETER IN "[UCSC_TRACK_FORMAT]" WHICH SPECIFIES DATA FILE URL (e.g. `bigDataUrl=` or `url=`). Croo will make a public URL and append it with `bigDataUrl=` to the track text.

## Inline expression

List of build-in variables for a inline expression

| Built-in variable | Type       | Description                                      |
|-------------------|------------|--------------------------------------------------|
| `basename`        | str        | Basename of file                                 | 
| `dirname`         | str        | Dirname of file                                  | 
| `full_path`       | str        | Full path of file                                | 
| `i`               | int        | 0-based index for main scatter loop              |
| `j`               | int        | 0-based index for nested scatter loop            |
| `k`               | int        | 0-based index for double-nested scatter loop     |
| `shard_idx`       | tuple(int) | tuple of indices for each dim.: (i, j, k, ...)   |
