import json
import os
from pathlib import Path
from textwrap import dedent

import pytest
from caper.caper_runner import CaperRunner


def mkdir_and_touch_output_only(maybe_file):
    """mkdir -p and then touch file if it's `.out`
    """
    if Path(maybe_file).suffix == '.out':
        Path(maybe_file).parent.mkdir(parents=True, exist_ok=True)
        Path(maybe_file).touch()


def recursive_replace_val_str(obj, string, new_string, callback_on_replaced=None):
    """Recursively replace value strings in a nested dict/list `obj`.
    Replaces `string` value with `new_string`.
    If `callback_on_replaced` is not None, then call it on a replaced full string.
    """
    if isinstance(obj, list):
        obj = [
            recursive_replace_val_str(x, string, new_string, callback_on_replaced)
            for x in obj
        ]
    elif isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = recursive_replace_val_str(
                obj[k], string, new_string, callback_on_replaced
            )
    elif isinstance(obj, str):
        if string in obj:
            obj = obj.replace(string, new_string)
            if callback_on_replaced:
                callback_on_replaced(obj)

    return obj


def pytest_addoption(parser):
    parser.addoption(
        '--ci-prefix', default='default_ci_prefix', help='Prefix for CI test.'
    )
    parser.addoption(
        '--metadata-json-for-subworkflow',
        default='data/subworkflow/metadata.json',
        help='Path for metadata.json to test subworkflow.'
        'Make sure to run pytest on this script\'s directory '
        'if you use the default path.',
    )
    parser.addoption(
        '--metadata-json-for-nested-scatter',
        default='data/subworkflow/metadata.json',
        help='Path for metadata.json to test nested scatter. '
        'Make sure to run pytest on this script\'s directory '
        'if you use the default path.',
    )


@pytest.fixture(scope='session')
def ci_prefix(request):
    return request.config.getoption('--ci-prefix').rstrip('/')


@pytest.fixture(scope='session')
def metadata_json_for_subworkflow(request, tmpdir_factory):
    """Make a copy of the JSON file and replaces its root with tmp_dir.
    Make empty output files with the same directory structure in the JSON.
    Returns a temporary metadata JSON file with workflow root strings replaced.
    """
    root = tmpdir_factory.mktemp('metadata_json_for_subworkflow')
    metadata_json = json.loads(
        Path(request.config.getoption('--metadata-json-for-subworkflow')).read_text()
    )
    recursive_replace_val_str(
        metadata_json,
        metadata_json['workflowRoot'],
        str(root),
        mkdir_and_touch_output_only,
    )

    metadata_json_file = root / 'metadata.json'
    Path(metadata_json_file).write_text(json.dumps(metadata_json, indent=4))

    return metadata_json_file


@pytest.fixture(scope='session')
def metadata_json_for_nested_scatter(request, tmpdir_factory):
    """Make a copy of the JSON file and replaces its root with tmp_dir.
    Make empty output files with the same directory structure in the JSON.
    Returns a temporary metadata JSON file with workflow root strings replaced.
    """
    root = tmpdir_factory.mktemp('metadata_json_for_nested_scatter')
    metadata_json = json.loads(
        Path(request.config.getoption('--metadata-json-for-nested-scatter')).read_text()
    )
    recursive_replace_val_str(
        metadata_json,
        metadata_json['workflowRoot'],
        str(root),
        mkdir_and_touch_output_only,
    )

    metadata_json_file = root / 'metadata.json'
    Path(metadata_json_file).write_text(json.dumps(metadata_json, indent=4))

    return metadata_json_file


@pytest.fixture(scope='session')
def wdl_main():
    return dedent(
        """
        version 1.0

        import "sub/sub.wdl"
        import "sub2/sub2.wdl" as sub2_alias

        workflow main {
            scatter(i in range(2)) {
                call t_main_1 { input:
                    i = i,
                }
                call sub.sub { input:
                    i = i,
                }
            }
            call t_main_1 as t_main_1_alias { input:
                i = -1,
            }

            call sub2_alias.sub2
            call sub2_alias.sub2 as sub2_alias_alias
        }

        task t_main_1 {
            input {
                Int i
            }

            command {
                echo ~{i} > t_main_1.~{i}.out
                sleep 2
            }

            output {
                File out = "t_main_1.~{i}.out"
            }
        }
    """
    )


@pytest.fixture(scope='session')
def wdl_sub():
    return dedent(
        """
        version 1.0

        import "subsub.wdl"

        workflow sub {
            input {
                Int i
            }

            scatter(j in range(2)) {
                call subsub.subsub { input:
                    i = i,
                    j = j,
                }
            }

            call t_sub_1 { input:
                i = i,
            }

            output {
                Array[Array[File]] out = subsub.out
            }
        }

        task t_sub_1 {
            input {
                Int i
            }
            command {
                echo ~{i} > t_sub_1.~{i}.out
            }

            output {
                File out = "t_sub_1.~{i}.out"
            }
        }
    """
    )


@pytest.fixture(scope='session')
def wdl_subsub():
    return dedent(
        """
        version 1.0

        workflow subsub {
            input {
                Int i
                Int j
            }
            scatter(k in range(2)) {
                call t_subsub_1 { input:
                    i = i,
                    j = j,
                    k = k,
                }
            }
            output {
                Array[File] out = t_subsub_1.out
            }
        }

        task t_subsub_1 {
            input {
                Int i
                Int j
                Int k
            }
            command {
                echo ~{i}.~{j}.~{k} > t_subsub_1.~{i}.~{j}.~{k}.out
            }

            output {
                File out = "t_subsub_1.~{i}.~{j}.~{k}.out"
            }
        }
    """
    )


@pytest.fixture(scope='session')
def wdl_sub2():
    return dedent(
        """
        version 1.0

        workflow sub2 {
            call t_sub2_1

            output {
                File out = t_sub2_1.out
            }
        }

        task t_sub2_1 {
            command {
                echo -1 > t_sub2_1.out
            }

            output {
                File out = "t_sub2_1.out"
            }
        }
    """
    )


@pytest.fixture(scope='session')
def wdl_nested_scatter():
    return dedent(
        """
        version 1.0

        workflow nested_scatter {
            scatter(i in range(2)) {
                scatter(j in range(2)) {
                    call t_nested_scatter_1 { input:
                        i = i,
                        j = j,
                    }
                }
            }
        }

        task t_nested_scatter_1 {
            input {
                Int i
                Int j
            }

            command {
                echo ~{i}.~{j} > t_nested_scatter_1.~{i}.~{j}.out
            }
            output {
                File out = "t_nested_scatter_1.~{i}.~{j}.out"
            }
        }
    """
    )


@pytest.fixture(scope='session')
def tmpdir_for_subworkflow(tmpdir_factory, wdl_main, wdl_sub, wdl_subsub, wdl_sub2):
    """Temporary directory with main WDL and all imported sub WDLs
    in a correct directory structure.

    There are 3 files on this directory.
        - main WDL: main.wdl
        - sub WDL: sub/sub.wdl
        - sub2 WDL: sub2/sub2.wdl

    Returns a PathLib object of the root directory.
    """
    root = tmpdir_factory.mktemp('main')
    root.mkdir('sub')
    root.mkdir('sub2')

    Path(root / 'main.wdl').write_text(wdl_main)
    Path(root / 'sub' / 'sub.wdl').write_text(wdl_sub)
    Path(root / 'sub' / 'subsub.wdl').write_text(wdl_subsub)
    Path(root / 'sub2' / 'sub2.wdl').write_text(wdl_sub2)

    return root


@pytest.fixture(scope='session')
def tmpdir_for_nested_scatter(tmpdir_factory, wdl_nested_scatter):
    """Temporary directory with nested-scatter WDL.

    There is 1 file on this directory.
        - main WDL: nested_scatter.wdl

    Returns a PathLib object of the root directory.
    """
    root = tmpdir_factory.mktemp('nested_scatter')
    Path(root / 'nested_scatter.wdl').write_text(wdl_nested_scatter)

    return root


@pytest.fixture(scope='session')
def run_caper_to_make_metadata_json_for_subworkflow(tmpdir_for_subworkflow,):
    wdl = tmpdir_for_subworkflow / 'main.wdl'
    metadata_json = tmpdir_for_subworkflow / 'metadata.json'

    os.chdir(str(tmpdir_for_subworkflow))
    caper_runner = CaperRunner(
        default_backend='Local', local_out_dir=str(tmpdir_for_subworkflow)
    )

    thread = caper_runner.run(
        backend='Local', wdl=str(wdl), metadata_output=str(metadata_json)
    )
    thread.join()

    return metadata_json


@pytest.fixture(scope='session')
def run_caper_to_make_metadata_json_for_nested_scatter(tmpdir_for_nested_scatter,):
    wdl = tmpdir_for_nested_scatter / 'nested_scatter.wdl'
    metadata_json = tmpdir_for_nested_scatter / 'metadata.json'

    os.chdir(str(tmpdir_for_nested_scatter))
    caper_runner = CaperRunner(
        default_backend='Local', local_out_dir=str(tmpdir_for_subworkflow)
    )

    thread = caper_runner.run(
        backend='Local', wdl=str(wdl), metadata_output=str(metadata_json)
    )
    thread.join()

    return metadata_json
