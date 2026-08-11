"""
tests/test_verified_charts_v2.py

外部暦照合済みの四柱を固定する
ゴールデン回帰テスト v2。

目的
----
過去の期待値そのものが誤っていた場合、
大量のpytestがGREENでも暦計算の正確性は保証できない。

そのため本ファイルでは、
外部万年暦と照合した「年柱・月柱・日柱・時柱」を
ゴールデンデータとして固定する。

今回固定する主要ケース
----------------------
1. 1985-07-17 21:50 石川県 女性
   乙丑 / 癸未 / 丁巳 / 辛亥

2. 1984-07-22 04:15 北海道 女性
   甲子 / 辛未 / 丁巳 / 壬寅

3. 1984-07-22 13:40 福岡県 男性
   甲子 / 辛未 / 丁巳 / 丁未

4. 1984-07-21 12:00 東京都 男性
   甲子 / 辛未 / 丙辰 / 甲午

重要
----
・このテストはAI鑑定文を検証しない。
・格局・用神・大運等の流派差を含む判定は固定しない。
・まず暦計算の土台である四柱を固定する。
・出生地の真太陽時補正は現行エンジンの仕様に従う。
・未検証の立春・節入り・23時境界を推測で追加しない。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from engine.chart import calculate_chart


# ============================================================
# Constants
# ============================================================


VERIFIED_CHARTS_V2_METHOD = (
    "externally_verified_four_pillars_v2"
)

VERIFIED_CHARTS_V2_STATUS = (
    "golden_regression"
)


# ============================================================
# Request adapter
# ============================================================


@dataclass(frozen=True)
class VerifiedChartRequest:
    """
    calculate_chart()へ渡す最小request。

    api.models.ChartRequestへの依存を避け、
    engine.chartの回帰テストとして利用する。
    """

    birth_date: str
    birth_time: str
    birth_place: str
    gender: str


# ============================================================
# Golden data
# ============================================================


GOLDEN_CHARTS = (
    {
        "id": (
            "1985_ishikawa_female_verified_v2"
        ),
        "request": VerifiedChartRequest(
            birth_date="1985-07-17",
            birth_time="21:50",
            birth_place="石川県",
            gender="female",
        ),
        "expected": {
            "year": "乙丑",
            "month": "癸未",
            "day": "丁巳",
            "hour": "辛亥",
        },
        "expected_day_master": "丁",
        "source_note": (
            "1985-07-17は乙丑年・癸未月・丁巳日。"
            "丁日21-23時は辛亥。"
        ),
    },
    {
        "id": (
            "1984_hokkaido_female_early_hour_v2"
        ),
        "request": VerifiedChartRequest(
            birth_date="1984-07-22",
            birth_time="04:15",
            birth_place="北海道",
            gender="female",
        ),
        "expected": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "壬寅",
        },
        "expected_day_master": "丁",
        "source_note": (
            "1984-07-22は甲子年・辛未月・丁巳日。"
            "丁日03-05時は壬寅。"
        ),
    },
    {
        "id": (
            "1984_fukuoka_male_afternoon_v2"
        ),
        "request": VerifiedChartRequest(
            birth_date="1984-07-22",
            birth_time="13:40",
            birth_place="福岡県",
            gender="male",
        ),
        "expected": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "丁未",
        },
        "expected_day_master": "丁",
        "source_note": (
            "1984-07-22は甲子年・辛未月・丁巳日。"
            "丁日13-15時は丁未。"
        ),
    },
    {
        "id": (
            "1984_tokyo_male_noon_v2"
        ),
        "request": VerifiedChartRequest(
            birth_date="1984-07-21",
            birth_time="12:00",
            birth_place="東京都",
            gender="male",
        ),
        "expected": {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "甲午",
        },
        "expected_day_master": "丙",
        "source_note": (
            "1984-07-21は甲子年・辛未月・丙辰日。"
            "丙日11-13時は甲午。"
        ),
    },
)


GOLDEN_IDS = tuple(
    item["id"]
    for item in GOLDEN_CHARTS
)


# ============================================================
# Helpers
# ============================================================


def _pillar_data(
    result: dict[str, Any],
    position: str,
) -> dict[str, Any]:
    """
    calculate_chart()の返却構造から柱データを取得する。

    現行chartでは result["chart"][position] を正式位置とする。
    """

    assert isinstance(
        result,
        dict,
    )

    assert (
        "chart"
        in result
    )

    chart = result[
        "chart"
    ]

    assert isinstance(
        chart,
        dict,
    )

    assert (
        position
        in chart
    )

    pillar = chart[
        position
    ]

    assert isinstance(
        pillar,
        dict,
    )

    return pillar


def _pillar_string(
    result: dict[str, Any],
    position: str,
) -> str:
    """
    指定柱の干支文字列を返す。
    """

    pillar = _pillar_data(
        result,
        position,
    )

    value = pillar.get(
        "pillar"
    )

    assert isinstance(
        value,
        str,
    )

    assert len(
        value
    ) == 2

    return value


def _stem(
    result: dict[str, Any],
    position: str,
) -> str:
    return _pillar_data(
        result,
        position,
    )[
        "stem"
    ]


def _branch(
    result: dict[str, Any],
    position: str,
) -> str:
    return _pillar_data(
        result,
        position,
    )[
        "branch"
    ]


def _calculate(
    item: dict[str, Any],
) -> dict[str, Any]:
    """
    ゴールデンケースを計算する。
    """

    return calculate_chart(
        item[
            "request"
        ]
    )


def _find_case(
    case_id: str,
) -> dict[str, Any]:
    """
    IDからゴールデンケースを取得する。
    """

    for item in GOLDEN_CHARTS:
        if (
            item[
                "id"
            ]
            == case_id
        ):
            return item

    raise AssertionError(
        f"unknown golden case: {case_id}"
    )


# ============================================================
# 1. Golden data integrity
# ============================================================


def test_golden_chart_ids_are_unique():
    assert (
        len(
            GOLDEN_IDS
        )
        == len(
            set(
                GOLDEN_IDS
            )
        )
    )


def test_golden_chart_count():
    """
    v2開始時点では、
    外部照合済みの4命式だけを固定する。

    未検証データを数合わせで追加しない。
    """

    assert (
        len(
            GOLDEN_CHARTS
        )
        == 4
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_golden_data_has_four_expected_pillars(
    item,
):
    assert set(
        item[
            "expected"
        ].keys()
    ) == {
        "year",
        "month",
        "day",
        "hour",
    }


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_golden_expected_pillars_are_two_characters(
    item,
):
    for value in (
        item[
            "expected"
        ].values()
    ):
        assert isinstance(
            value,
            str,
        )

        assert len(
            value
        ) == 2


# ============================================================
# 2. Complete four-pillar golden regression
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_chart_four_pillars(
    item,
):
    result = _calculate(
        item
    )

    actual = {
        position: _pillar_string(
            result,
            position,
        )
        for position in (
            "year",
            "month",
            "day",
            "hour",
        )
    }

    assert (
        actual
        == item[
            "expected"
        ]
    )


# ============================================================
# 3. Individual pillar regression
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_year_pillar(
    item,
):
    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "year",
        )
        == item[
            "expected"
        ][
            "year"
        ]
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_month_pillar(
    item,
):
    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "month",
        )
        == item[
            "expected"
        ][
            "month"
        ]
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_day_pillar(
    item,
):
    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "day",
        )
        == item[
            "expected"
        ][
            "day"
        ]
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_hour_pillar(
    item,
):
    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "hour",
        )
        == item[
            "expected"
        ][
            "hour"
        ]
    )


# ============================================================
# 4. Stem / branch internal consistency
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
@pytest.mark.parametrize(
    "position",
    (
        "year",
        "month",
        "day",
        "hour",
    ),
)
def test_verified_pillar_matches_stem_and_branch(
    item,
    position,
):
    result = _calculate(
        item
    )

    pillar = _pillar_string(
        result,
        position,
    )

    assert (
        pillar
        == (
            _stem(
                result,
                position,
            )
            + _branch(
                result,
                position,
            )
        )
    )


# ============================================================
# 5. Day master regression
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_day_master_matches_day_stem(
    item,
):
    result = _calculate(
        item
    )

    day_stem = _stem(
        result,
        "day",
    )

    assert (
        day_stem
        == item[
            "expected_day_master"
        ]
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_day_pillar_first_character_is_day_master(
    item,
):
    result = _calculate(
        item
    )

    day_pillar = _pillar_string(
        result,
        "day",
    )

    assert (
        day_pillar[
            0
        ]
        == item[
            "expected_day_master"
        ]
    )


# ============================================================
# 6. 1985-07-17 regression
# ============================================================


def test_verified_1985_07_17_is_not_old_otsushi_value():
    """
    旧期待値「乙巳」を再び混入させない。

    外部暦照合後の正解は丁巳。
    """

    item = _find_case(
        "1985_ishikawa_female_verified_v2"
    )

    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "day",
        )
        == "丁巳"
    )

    assert (
        _pillar_string(
            result,
            "day",
        )
        != "乙巳"
    )


def test_verified_1985_07_17_hour_is_shingai():
    item = _find_case(
        "1985_ishikawa_female_verified_v2"
    )

    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "hour",
        )
        == "辛亥"
    )


def test_verified_1985_07_17_complete_sequence():
    item = _find_case(
        "1985_ishikawa_female_verified_v2"
    )

    result = _calculate(
        item
    )

    assert [
        _pillar_string(
            result,
            position,
        )
        for position in (
            "year",
            "month",
            "day",
            "hour",
        )
    ] == [
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
    ]


# ============================================================
# 7. 1984-07-22 date consistency
# ============================================================


def test_1984_07_22_same_date_same_year_month_day():
    """
    同じ1984-07-22で出生時刻・出生地・性別が異なっても、
    年柱・月柱・日柱は一致することを固定する。
    """

    early = _calculate(
        _find_case(
            "1984_hokkaido_female_early_hour_v2"
        )
    )

    afternoon = _calculate(
        _find_case(
            "1984_fukuoka_male_afternoon_v2"
        )
    )

    for position in (
        "year",
        "month",
        "day",
    ):
        assert (
            _pillar_string(
                early,
                position,
            )
            == _pillar_string(
                afternoon,
                position,
            )
        )


def test_1984_07_22_hour_changes_with_birth_time():
    """
    同日でも時刻が変われば時柱は変化する。
    """

    early = _calculate(
        _find_case(
            "1984_hokkaido_female_early_hour_v2"
        )
    )

    afternoon = _calculate(
        _find_case(
            "1984_fukuoka_male_afternoon_v2"
        )
    )

    assert (
        _pillar_string(
            early,
            "hour",
        )
        == "壬寅"
    )

    assert (
        _pillar_string(
            afternoon,
            "hour",
        )
        == "丁未"
    )

    assert (
        _pillar_string(
            early,
            "hour",
        )
        != _pillar_string(
            afternoon,
            "hour",
        )
    )


# ============================================================
# 8. Consecutive-day regression
# ============================================================


def test_1984_07_21_day_is_heishin():
    item = _find_case(
        "1984_tokyo_male_noon_v2"
    )

    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "day",
        )
        == "丙辰"
    )


def test_1984_07_22_day_is_teishi():
    item = _find_case(
        "1984_hokkaido_female_early_hour_v2"
    )

    result = _calculate(
        item
    )

    assert (
        _pillar_string(
            result,
            "day",
        )
        == "丁巳"
    )


def test_consecutive_day_progression_1984_07_21_to_22():
    """
    7/21 丙辰 → 7/22 丁巳 の連続性を固定する。
    """

    first = _calculate(
        _find_case(
            "1984_tokyo_male_noon_v2"
        )
    )

    second = _calculate(
        _find_case(
            "1984_hokkaido_female_early_hour_v2"
        )
    )

    assert (
        _pillar_string(
            first,
            "day",
        )
        == "丙辰"
    )

    assert (
        _pillar_string(
            second,
            "day",
        )
        == "丁巳"
    )


# ============================================================
# 9. Month-pillar regression
# ============================================================


@pytest.mark.parametrize(
    "case_id",
    (
        "1984_hokkaido_female_early_hour_v2",
        "1984_fukuoka_male_afternoon_v2",
        "1984_tokyo_male_noon_v2",
    ),
)
def test_july_1984_verified_month_is_shinbi(
    case_id,
):
    """
    1984年7月21日・22日は節月で辛未月。
    """

    result = _calculate(
        _find_case(
            case_id
        )
    )

    assert (
        _pillar_string(
            result,
            "month",
        )
        == "辛未"
    )


def test_july_1985_verified_month_is_kibi():
    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_string(
            result,
            "month",
        )
        == "癸未"
    )


# ============================================================
# 10. Year-pillar regression
# ============================================================


@pytest.mark.parametrize(
    "case_id",
    (
        "1984_hokkaido_female_early_hour_v2",
        "1984_fukuoka_male_afternoon_v2",
        "1984_tokyo_male_noon_v2",
    ),
)
def test_verified_1984_year_is_kinoene(
    case_id,
):
    result = _calculate(
        _find_case(
            case_id
        )
    )

    assert (
        _pillar_string(
            result,
            "year",
        )
        == "甲子"
    )


def test_verified_1985_year_is_kinotoushi():
    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_string(
            result,
            "year",
        )
        == "乙丑"
    )


# ============================================================
# 11. Basic chart structure
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_chart_has_four_pillar_dicts(
    item,
):
    result = _calculate(
        item
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = _pillar_data(
            result,
            position,
        )

        assert (
            "pillar"
            in pillar
        )

        assert (
            "stem"
            in pillar
        )

        assert (
            "branch"
            in pillar
        )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_chart_pillars_have_ten_god_field(
    item,
):
    result = _calculate(
        item
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        assert (
            "stem_ten_god"
            in _pillar_data(
                result,
                position,
            )
        )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_chart_pillars_have_twelve_stage(
    item,
):
    result = _calculate(
        item
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        value = _pillar_data(
            result,
            position,
        ).get(
            "twelve_stage"
        )

        assert isinstance(
            value,
            str,
        )

        assert (
            value.strip()
        )


# ============================================================
# 12. Day-pillar dependent ten-god consistency
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_day_pillar_stem_ten_god_is_none(
    item,
):
    """
    日干自身は通変星の基準なので、
    day.stem_ten_godはNoneを期待する。
    """

    result = _calculate(
        item
    )

    assert (
        _pillar_data(
            result,
            "day",
        ).get(
            "stem_ten_god"
        )
        is None
    )


def test_verified_1985_ten_gods_follow_tei_day_master():
    """
    丁日主の1985検証命式で、
    天干通変星が日主丁を基準に計算されていることを確認。
    """

    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_data(
            result,
            "year",
        )[
            "stem_ten_god"
        ]
        == "偏印"
    )

    assert (
        _pillar_data(
            result,
            "month",
        )[
            "stem_ten_god"
        ]
        == "偏官"
    )

    assert (
        _pillar_data(
            result,
            "day",
        )[
            "stem_ten_god"
        ]
        is None
    )

    assert (
        _pillar_data(
            result,
            "hour",
        )[
            "stem_ten_god"
        ]
        == "偏財"
    )


# ============================================================
# 13. Hidden-stem basic integrity
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_chart_hidden_stems_are_present(
    item,
):
    result = _calculate(
        item
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = _pillar_data(
            result,
            position,
        )

        hidden_stems = pillar.get(
            "hidden_stems"
        )

        assert isinstance(
            hidden_stems,
            list,
        )

        assert (
            len(
                hidden_stems
            )
            >= 1
        )


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_main_hidden_stem_is_in_hidden_stems(
    item,
):
    result = _calculate(
        item
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = _pillar_data(
            result,
            position,
        )

        main = pillar.get(
            "main_hidden_stem"
        )

        hidden = pillar.get(
            "hidden_stems"
        )

        assert (
            main
            in hidden
        )


# ============================================================
# 14. Known 1985 pillar details
# ============================================================


def test_verified_1985_year_hidden_stems():
    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_data(
            result,
            "year",
        )[
            "hidden_stems"
        ]
        == [
            "己",
            "癸",
            "辛",
        ]
    )


def test_verified_1985_month_hidden_stems():
    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_data(
            result,
            "month",
        )[
            "hidden_stems"
        ]
        == [
            "己",
            "丁",
            "乙",
        ]
    )


def test_verified_1985_day_hidden_stems():
    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_data(
            result,
            "day",
        )[
            "hidden_stems"
        ]
        == [
            "丙",
            "戊",
            "庚",
        ]
    )


def test_verified_1985_hour_hidden_stems():
    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert (
        _pillar_data(
            result,
            "hour",
        )[
            "hidden_stems"
        ]
        == [
            "壬",
            "甲",
        ]
    )


# ============================================================
# 15. Known 1985 twelve stages
# ============================================================


def test_verified_1985_twelve_stages():
    """
    丁日主に対する十二運の回帰テスト。
    """

    result = _calculate(
        _find_case(
            "1985_ishikawa_female_verified_v2"
        )
    )

    assert {
        position: _pillar_data(
            result,
            position,
        )[
            "twelve_stage"
        ]
        for position in (
            "year",
            "month",
            "day",
            "hour",
        )
    } == {
        "year": "墓",
        "month": "冠帯",
        "day": "帝旺",
        "hour": "胎",
    }


# ============================================================
# 16. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_verified_chart_reproducible(
    item,
):
    """
    同一入力で四柱が変化しないことを確認する。
    """

    first = _calculate(
        item
    )

    second = _calculate(
        item
    )

    first_pillars = {
        position: _pillar_string(
            first,
            position,
        )
        for position in (
            "year",
            "month",
            "day",
            "hour",
        )
    }

    second_pillars = {
        position: _pillar_string(
            second,
            position,
        )
        for position in (
            "year",
            "month",
            "day",
            "hour",
        )
    }

    assert (
        first_pillars
        == second_pillars
    )


# ============================================================
# 17. Source notes
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_CHARTS,
    ids=GOLDEN_IDS,
)
def test_golden_case_has_source_note(
    item,
):
    """
    将来、期待値を変更する場合に、
    何を根拠に固定したケースか追跡できるようにする。
    """

    assert isinstance(
        item.get(
            "source_note"
        ),
        str,
    )

    assert (
        item[
            "source_note"
        ].strip()
    )


# ============================================================
# 18. Metadata
# ============================================================


def test_verified_charts_v2_metadata():
    assert (
        VERIFIED_CHARTS_V2_METHOD
        == "externally_verified_four_pillars_v2"
    )

    assert (
        VERIFIED_CHARTS_V2_STATUS
        == "golden_regression"
    )


# ============================================================
# 19. Final golden smoke
# ============================================================


def test_verified_charts_v2_final_smoke():
    """
    4件すべてについて、
    外部照合済み四柱が完全一致することを最終確認。
    """

    actual = {}

    for item in GOLDEN_CHARTS:
        result = _calculate(
            item
        )

        actual[
            item[
                "id"
            ]
        ] = tuple(
            _pillar_string(
                result,
                position,
            )
            for position in (
                "year",
                "month",
                "day",
                "hour",
            )
        )

    assert actual == {
        (
            "1985_ishikawa_female_verified_v2"
        ): (
            "乙丑",
            "癸未",
            "丁巳",
            "辛亥",
        ),
        (
            "1984_hokkaido_female_early_hour_v2"
        ): (
            "甲子",
            "辛未",
            "丁巳",
            "壬寅",
        ),
        (
            "1984_fukuoka_male_afternoon_v2"
        ): (
            "甲子",
            "辛未",
            "丁巳",
            "丁未",
        ),
        (
            "1984_tokyo_male_noon_v2"
        ): (
            "甲子",
            "辛未",
            "丙辰",
            "甲午",
        ),
    }
