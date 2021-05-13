import pytest

from croo.croo import Croo


@pytest.mark.parametrize(
    'croo_out_def_json, expected_relpaths',
    [
        (
            {
                "nested_scatter.t_nested_scatter_1": {
                    "out": {"path": "t_nested_scatter_1/${i}/${j}/${basename}"}
                }
            },
            [
                't_nested_scatter_1/1/1/t_nested_scatter_1.1.1.out',
                't_nested_scatter_1/1/0/t_nested_scatter_1.1.0.out',
                't_nested_scatter_1/0/1/t_nested_scatter_1.0.1.out',
                't_nested_scatter_1/0/0/t_nested_scatter_1.0.0.out',
            ],
        )
    ],
)
def test_nested_scatter(
    metadata_json_for_nested_scatter, tmp_path, croo_out_def_json, expected_relpaths
):
    cm = Croo(
        metadata_json=str(metadata_json_for_nested_scatter),
        out_def_json=croo_out_def_json,
        out_dir=str(tmp_path),
        tmp_dir=str(tmp_path),
    )
    cm.organize_output()

    for expected_relpath in expected_relpaths:
        assert (tmp_path / expected_relpath).exists
