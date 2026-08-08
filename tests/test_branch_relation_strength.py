import pytest

from engine.branch_relation_strength import (
    BRANCH_RELATION_WEIGHTS,
    calculate_branch_relation_strength,
)


def make_relation_data(
    count_key: str,
    count: int,
) -> dict:
    """
    テスト用の地支関係データを作成します。
    """
    return {
        count_key: count,
    }


def test_branch_relation_weights():
    """
    v1の暫定重みが意図した値であることを確認します。
    """
    assert BRANCH_RELATION_WEIGHTS == {
        "clash": -2.0,
        "combination": 1.5,
        "trine": 2.5,
        "punishment": -1.5,
        "harm": -1.0,
        "break": -0.5,
    }


def test_no_branch_relations():
    """
    地支関係が存在しない場合を確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=make_relation_data(
            "clash_count",
            0,
        ),
        branch_combinations=make_relation_data(
            "combination_count",
            0,
        ),
        branch_trines=make_relation_data(
            "trine_count",
            0,
        ),
        branch_punishments=make_relation_data(
            "punishment_count",
            0,
        ),
        branch_harms=make_relation_data(
            "harm_count",
            0,
        ),
        branch_breaks=make_relation_data(
            "break_count",
            0,
        ),
    )

    assert result[
        "total_relation_count"
    ] == 0

    assert result[
        "positive_score"
    ] == 0.0

    assert result[
        "negative_score"
    ] == 0.0

    assert result[
        "total_score"
    ] == 0.0

    assert result[
        "balance"
    ] == "neutral"

    assert (
        result["method"]
        == "branch_relation_strength_v1"
    )

    assert (
        result["status"]
        == "provisional_branch_relation_strength"
    )


def test_positive_branch_relations():
    """
    六合と三合だけが存在する場合を確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=make_relation_data(
            "clash_count",
            0,
        ),
        branch_combinations=make_relation_data(
            "combination_count",
            2,
        ),
        branch_trines=make_relation_data(
            "trine_count",
            1,
        ),
        branch_punishments=make_relation_data(
            "punishment_count",
            0,
        ),
        branch_harms=make_relation_data(
            "harm_count",
            0,
        ),
        branch_breaks=make_relation_data(
            "break_count",
            0,
        ),
    )

    assert result[
        "total_relation_count"
    ] == 3

    assert result[
        "positive_score"
    ] == 5.5

    assert result[
        "negative_score"
    ] == 0.0

    assert result[
        "total_score"
    ] == 5.5

    assert result[
        "balance"
    ] == "positive"

    assert result[
        "details"
    ]["combination"] == {
        "count": 2,
        "weight": 1.5,
        "score": 3.0,
    }

    assert result[
        "details"
    ]["trine"] == {
        "count": 1,
        "weight": 2.5,
        "score": 2.5,
    }


def test_negative_branch_relations():
    """
    冲・刑・害・破だけが存在する場合を確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=make_relation_data(
            "clash_count",
            1,
        ),
        branch_combinations=make_relation_data(
            "combination_count",
            0,
        ),
        branch_trines=make_relation_data(
            "trine_count",
            0,
        ),
        branch_punishments=make_relation_data(
            "punishment_count",
            1,
        ),
        branch_harms=make_relation_data(
            "harm_count",
            1,
        ),
        branch_breaks=make_relation_data(
            "break_count",
            1,
        ),
    )

    assert result[
        "total_relation_count"
    ] == 4

    assert result[
        "positive_score"
    ] == 0.0

    assert result[
        "negative_score"
    ] == 5.0

    assert result[
        "total_score"
    ] == -5.0

    assert result[
        "balance"
    ] == "negative"

    assert result[
        "details"
    ]["clash"] == {
        "count": 1,
        "weight": -2.0,
        "score": -2.0,
    }

    assert result[
        "details"
    ]["punishment"] == {
        "count": 1,
        "weight": -1.5,
        "score": -1.5,
    }

    assert result[
        "details"
    ]["harm"] == {
        "count": 1,
        "weight": -1.0,
        "score": -1.0,
    }

    assert result[
        "details"
    ]["break"] == {
        "count": 1,
        "weight": -0.5,
        "score": -0.5,
    }


def test_mixed_branch_relations():
    """
    正方向と負方向の関係が
    混在する場合を確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=make_relation_data(
            "clash_count",
            1,
        ),
        branch_combinations=make_relation_data(
            "combination_count",
            1,
        ),
        branch_trines=make_relation_data(
            "trine_count",
            1,
        ),
        branch_punishments=make_relation_data(
            "punishment_count",
            1,
        ),
        branch_harms=make_relation_data(
            "harm_count",
            1,
        ),
        branch_breaks=make_relation_data(
            "break_count",
            1,
        ),
    )

    assert result[
        "total_relation_count"
    ] == 6

    assert result[
        "positive_score"
    ] == 4.0

    assert result[
        "negative_score"
    ] == 5.0

    assert result[
        "total_score"
    ] == -1.0

    assert result[
        "balance"
    ] == "negative"


def test_balanced_branch_relations():
    """
    正負が相殺される場合を確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=make_relation_data(
            "clash_count",
            1,
        ),
        branch_combinations=make_relation_data(
            "combination_count",
            0,
        ),
        branch_trines=make_relation_data(
            "trine_count",
            1,
        ),
        branch_punishments=make_relation_data(
            "punishment_count",
            0,
        ),
        branch_harms=make_relation_data(
            "harm_count",
            0,
        ),
        branch_breaks=make_relation_data(
            "break_count",
            1,
        ),
    )

    assert result[
        "positive_score"
    ] == 2.5

    assert result[
        "negative_score"
    ] == 2.5

    assert result[
        "total_score"
    ] == 0.0

    assert result[
        "balance"
    ] == "neutral"


def test_none_relation_data():
    """
    関係データがNoneでも
    0件として処理できることを確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=None,
        branch_combinations=None,
        branch_trines=None,
        branch_punishments=None,
        branch_harms=None,
        branch_breaks=None,
    )

    assert result[
        "total_relation_count"
    ] == 0

    assert result[
        "positive_score"
    ] == 0.0

    assert result[
        "negative_score"
    ] == 0.0

    assert result[
        "total_score"
    ] == 0.0

    assert result[
        "balance"
    ] == "neutral"


def test_missing_count_keys():
    """
    countキーが存在しない場合に
    0件として扱うことを確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes={},
        branch_combinations={},
        branch_trines={},
        branch_punishments={},
        branch_harms={},
        branch_breaks={},
    )

    assert result[
        "total_relation_count"
    ] == 0

    assert result[
        "total_score"
    ] == 0.0

    assert result[
        "balance"
    ] == "neutral"


def test_invalid_count_type():
    """
    件数がint以外の場合に
    TypeErrorとなることを確認します。
    """
    with pytest.raises(
        TypeError,
        match="clash_countはint型で指定してください。",
    ):
        calculate_branch_relation_strength(
            branch_clashes={
                "clash_count": "1",
            },
            branch_combinations=None,
            branch_trines=None,
            branch_punishments=None,
            branch_harms=None,
            branch_breaks=None,
        )


def test_negative_count():
    """
    負の件数を拒否することを確認します。
    """
    with pytest.raises(
        ValueError,
        match="break_countは0以上で指定してください。",
    ):
        calculate_branch_relation_strength(
            branch_clashes=None,
            branch_combinations=None,
            branch_trines=None,
            branch_punishments=None,
            branch_harms=None,
            branch_breaks={
                "break_count": -1,
            },
        )


def test_result_contains_all_details():
    """
    detailsに全6種類が
    含まれることを確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=None,
        branch_combinations=None,
        branch_trines=None,
        branch_punishments=None,
        branch_harms=None,
        branch_breaks=None,
    )

    assert set(
        result["details"].keys()
    ) == {
        "clash",
        "combination",
        "trine",
        "punishment",
        "harm",
        "break",
    }


def test_result_contains_weights_copy():
    """
    結果に重み設定が含まれることを確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=None,
        branch_combinations=None,
        branch_trines=None,
        branch_punishments=None,
        branch_harms=None,
        branch_breaks=None,
    )

    assert (
        result["weights"]
        == BRANCH_RELATION_WEIGHTS
    )

    assert (
        result["weights"]
        is not BRANCH_RELATION_WEIGHTS
    )


def test_result_contains_notes():
    """
    暫定実装であることを示すnotesが
    含まれることを確認します。
    """
    result = calculate_branch_relation_strength(
        branch_clashes=None,
        branch_combinations=None,
        branch_trines=None,
        branch_punishments=None,
        branch_harms=None,
        branch_breaks=None,
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert len(
        result["notes"]
    ) >= 1
