import pytest

from croo.croo import Croo


@pytest.mark.parametrize(
    'croo_out_def_json, expected_relpaths',
    [
        (
            {"main.t_main_1": {"out": {"path": "main.t_main_1/${i}/${basename}"}}},
            ['main.t_main_1/1/t_main_1.1.out', 'main.t_main_1/0/t_main_1.0.out'],
        ),
        (
            {
                "main.sub.subsub.t_subsub_1": {
                    "out": {
                        "path": "main.sub.subsub.t_subsub_1/${i}/${j}/${k}/${basename}"
                    }
                }
            },
            [
                'main.sub.subsub.t_subsub_1/1/1/1/t_subsub_1.1.1.1.out',
                'main.sub.subsub.t_subsub_1/1/1/0/t_subsub_1.1.1.0.out',
                'main.sub.subsub.t_subsub_1/1/0/1/t_subsub_1.1.0.1.out',
                'main.sub.subsub.t_subsub_1/1/0/0/t_subsub_1.1.0.0.out',
                'main.sub.subsub.t_subsub_1/0/1/1/t_subsub_1.0.1.1.out',
                'main.sub.subsub.t_subsub_1/0/1/0/t_subsub_1.0.1.0.out',
                'main.sub.subsub.t_subsub_1/0/0/1/t_subsub_1.0.0.1.out',
                'main.sub.subsub.t_subsub_1/0/0/0/t_subsub_1.0.0.0.out',
            ],
        ),
        (
            {
                "main.t_main_1_alias": {
                    "out": {"path": "main.t_main_1_alias/${basename}"}
                }
            },
            ['main.t_main_1_alias/t_main_1.-1.out'],
        ),
        (
            {"main.sub2.t_sub2_1": {"out": {"path": "main.sub2.t_sub2_1/${basename}"}}},
            ['main.sub2.t_sub2_1/t_sub2_1.out'],
        ),
        (
            {
                "main.sub2_alias.t_sub2_1": {
                    "out": {"path": "main.sub2_alias.t_sub2_1/${basename}"}
                }
            },
            ['main.sub2_alias.t_sub2_1/t_sub2_1.out'],
        ),
        (
            {
                "main.sub.t_sub_1": {
                    "out": {"path": "main.sub.t_sub_1/${i}/${j}/${basename}"}
                }
            },
            [
                'main.sub.t_sub_1/1/None/t_sub_1.1.out'
                'main.sub.t_sub_1/0/None/t_sub_1.0.out'
            ],
        ),
    ],
)
def test_subworkflow(
    metadata_json_for_subworkflow, tmp_path, croo_out_def_json, expected_relpaths
):
    """Out-of-index-ed label is converted into `None`.
    """
    cm = Croo(
        metadata_json=str(metadata_json_for_subworkflow),
        out_def_json=croo_out_def_json,
        out_dir=str(tmp_path),
        tmp_dir=str(tmp_path),
    )
    cm.organize_output()

    for expected_relpath in expected_relpaths:
        assert (tmp_path / expected_relpath).exists
