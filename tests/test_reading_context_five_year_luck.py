"""
tests/test_reading_context_five_year_luck.py

reading_context に追加された five_year_luck の回帰テスト。

目的
----
chart.py が計算した five_year_luck を、
reading_context.py が占術上の再計算を行わず、
AI鑑定用の安定した構造へ正しく整形することを確認する。

主な確認項目
------------
1. luck.five_year_luck が存在する
2. 5年分を保持する
3. 2026～2030年の順序を保持する
4. 各年の target_datetime を保持する
5. 各年の current_luck / annual_luck / integrated_luck を整形する
6. 初年度が既存の単年運データと一致する
7. 歳運干支の5年シーケンスを保持する
8. future_flow が five_year_luck を参照する
9. reading_context が元 chart_result を変更しない
10. five_year_luck がない旧形式では空listとして扱う
11. 出生時刻不明では5年分にも推定情報を伝播する

注意
----
このテストは古典上の未来予測の正解を固定するものではない。
chart.py が算出済みの結果を reading_context.py が
正しく受け渡すことを回帰固定する。
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

from engine.chart import calculate_chart
from engine.reading_context import (
    build_five_year_luck_context,
    build_reading_context,
)


# ============================================================
# Fixed data
# ============================================================


TARGET_DATETIME = datetime(
    2026,
    8,
    15,
    10,
    30,
)

EXPECTED_YEARS = [
    2026,
    2027,
    2028,
    2029,
    2030,
]

EXPECTED_TARGET_DATETIMES = [
    "2026-08-15T10:30:00",
    "2027-07-01T12:00:00",
    "2028-07-01T12:00:00",
    "2029-07-01T12:00:00",
    "2030-07-01T12:00:00",
]

EXPECTED_ANNUAL_GANZHI = [
    "丙午",
    "丁未",
    "戊申",
    "己酉",
    "庚戌",
]


# ============================================================
# Helpers
# ============================================================


def make_request(
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    gender: str,
):
    return SimpleNamespace(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
    )


def make_verified_request():
    return make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


def build_verified_chart_result():
    return calculate_chart(
        make_verified_request(),
        target_datetime=TARGET_DATETIME,
    )


def build_verified_reading_context():
    return build_reading_context(
        build_verified_chart_result()
    )


# ============================================================
# 1. Container
# ============================================================


def test_reading_context_contains_five_year_luck():
    context = build_verified_reading_context()

    assert (
        "five_year_luck"
        in context["luck"]
    )

    assert isinstance(
        context["luck"]["five_year_luck"],
        list,
    )


def test_reading_context_five_year_luck_has_five_entries():
    context = build_verified_reading_context()

    assert len(
        context["luck"]["five_year_luck"]
    ) == 5


# ============================================================
# 2. Year / datetime preservation
# ============================================================


def test_reading_context_five_year_luck_year_sequence():
    context = build_verified_reading_context()

    actual = [
        item["year"]
        for item in context[
            "luck"
        ][
            "five_year_luck"
        ]
    ]

    assert actual == EXPECTED_YEARS


def test_reading_context_five_year_luck_target_datetime_sequence():
    context = build_verified_reading_context()

    actual = [
        item["target_datetime"]
        for item in context[
            "luck"
        ][
            "five_year_luck"
        ]
    ]

    assert (
        actual
        == EXPECTED_TARGET_DATETIMES
    )


# ============================================================
# 3. Entry structure
# ============================================================


def test_reading_context_five_year_luck_entry_keys():
    context = build_verified_reading_context()

    required_keys = {
        "year",
        "target_datetime",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert set(
            item.keys()
        ) == required_keys


def test_reading_context_five_year_luck_nested_types():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert isinstance(
            item["current_luck"],
            dict,
        )
        assert isinstance(
            item["annual_luck"],
            dict,
        )
        assert isinstance(
            item["integrated_luck"],
            dict,
        )


# ============================================================
# 4. Annual luck preservation
# ============================================================


def test_reading_context_five_year_luck_ganzhi_sequence():
    context = build_verified_reading_context()

    actual = [
        item[
            "annual_luck"
        ][
            "ganzhi"
        ]
        for item in context[
            "luck"
        ][
            "five_year_luck"
        ]
    ]

    assert (
        actual
        == EXPECTED_ANNUAL_GANZHI
    )


def test_reading_context_five_year_luck_effective_year_matches_year():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert (
            item[
                "annual_luck"
            ][
                "effective_year"
            ]
            == item["year"]
        )


def test_reading_context_five_year_luck_calendar_year_matches_year():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert (
            item[
                "annual_luck"
            ][
                "calendar_year"
            ]
            == item["year"]
        )


# ============================================================
# 5. First year must match existing one-year context
# ============================================================


def test_first_year_annual_luck_matches_single_year_context():
    context = build_verified_reading_context()

    assert (
        context[
            "luck"
        ][
            "five_year_luck"
        ][0][
            "annual_luck"
        ]
        == context[
            "luck"
        ][
            "annual_luck"
        ]
    )


def test_first_year_current_luck_matches_single_year_context():
    context = build_verified_reading_context()

    assert (
        context[
            "luck"
        ][
            "five_year_luck"
        ][0][
            "current_luck"
        ]
        == context[
            "luck"
        ][
            "current_luck"
        ]
    )


def test_first_year_integrated_luck_matches_single_year_context():
    context = build_verified_reading_context()

    assert (
        context[
            "luck"
        ][
            "five_year_luck"
        ][0][
            "integrated_luck"
        ]
        == context[
            "luck"
        ][
            "integrated_luck"
        ]
    )


# ============================================================
# 6. Integrated luck consistency
# ============================================================


def test_each_integrated_luck_matches_annual_ganzhi():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert (
            item[
                "integrated_luck"
            ][
                "annual_luck_ganzhi"
            ]
            == item[
                "annual_luck"
            ][
                "ganzhi"
            ]
        )


def test_each_integrated_luck_matches_current_luck_ganzhi():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        current_pillar = item[
            "current_luck"
        ][
            "current_pillar"
        ]

        if current_pillar is None:
            continue

        assert (
            item[
                "integrated_luck"
            ][
                "current_luck_ganzhi"
            ]
            == current_pillar[
                "ganzhi"
            ]
        )


# ============================================================
# 7. Compacting / AI input safety
# ============================================================


def test_five_year_context_does_not_copy_annual_evidence():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert (
            "evidence"
            not in item[
                "annual_luck"
            ]
        )


def test_five_year_context_does_not_copy_integrated_evidence():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert (
            "evidence"
            not in item[
                "integrated_luck"
            ]
        )


# ============================================================
# 8. future_flow linkage
# ============================================================


def test_future_flow_focus_contains_five_year_luck():
    context = build_verified_reading_context()

    focus = context[
        "reading_sections"
    ][
        "future_flow"
    ][
        "focus"
    ]

    assert (
        "five_year_luck"
        in focus
    )


def test_future_flow_instruction_mentions_five_year_flow():
    context = build_verified_reading_context()

    instruction = context[
        "reading_sections"
    ][
        "future_flow"
    ][
        "instruction"
    ]

    assert isinstance(
        instruction,
        str,
    )

    assert (
        "5年間"
        in instruction
    )

    assert (
        "年ごと"
        in instruction
    )


# ============================================================
# 9. Direct builder
# ============================================================


def test_build_five_year_luck_context_directly():
    chart_result = (
        build_verified_chart_result()
    )

    result = (
        build_five_year_luck_context(
            chart_result
        )
    )

    assert isinstance(
        result,
        list,
    )

    assert len(result) == 5

    assert [
        item["year"]
        for item in result
    ] == EXPECTED_YEARS

    assert [
        item["annual_luck"]["ganzhi"]
        for item in result
    ] == EXPECTED_ANNUAL_GANZHI


def test_build_five_year_luck_context_old_format_returns_empty_list():
    chart_result = (
        build_verified_chart_result()
    )

    chart_result.pop(
        "five_year_luck"
    )

    result = (
        build_five_year_luck_context(
            chart_result
        )
    )

    assert result == []


# ============================================================
# 10. No mutation
# ============================================================


def test_build_reading_context_does_not_mutate_raw_five_year_luck():
    chart_result = (
        build_verified_chart_result()
    )

    original = deepcopy(
        chart_result[
            "five_year_luck"
        ]
    )

    build_reading_context(
        chart_result
    )

    assert (
        chart_result[
            "five_year_luck"
        ]
        == original
    )


# ============================================================
# 11. Reproducibility
# ============================================================


def test_five_year_reading_context_is_reproducible():
    chart_result = (
        build_verified_chart_result()
    )

    first = build_reading_context(
        chart_result
    )

    second = build_reading_context(
        chart_result
    )

    assert (
        first[
            "luck"
        ][
            "five_year_luck"
        ]
        == second[
            "luck"
        ][
            "five_year_luck"
        ]
    )


# ============================================================
# 12. Unknown birth time
# ============================================================


def test_unknown_birth_time_five_year_luck_has_estimated_timing():
    request = make_request(
        birth_date="1988-08-08",
        birth_time=None,
        birth_place="神奈川県",
        gender="male",
    )

    chart_result = calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )

    context = build_reading_context(
        chart_result
    )

    assert (
        context[
            "birth_time_status"
        ][
            "known"
        ]
        is False
    )

    five_year_luck = context[
        "luck"
    ][
        "five_year_luck"
    ]

    assert len(
        five_year_luck
    ) == 5

    for item in five_year_luck:
        assert (
            item[
                "current_luck"
            ][
                "timing_is_estimated"
            ]
            is True
        )

        assert (
            item[
                "integrated_luck"
            ][
                "timing_is_estimated"
            ]
            is True
        )


def test_known_birth_time_five_year_luck_is_not_estimated():
    context = build_verified_reading_context()

    for item in context[
        "luck"
    ][
        "five_year_luck"
    ]:
        assert (
            item[
                "current_luck"
            ][
                "timing_is_estimated"
            ]
            is False
        )

        assert (
            item[
                "integrated_luck"
            ][
                "timing_is_estimated"
            ]
            is False
        )


# ============================================================
# 13. Sliding target year
# ============================================================


def test_reading_context_five_year_luck_slides_with_target_year():
    chart_result = calculate_chart(
        make_verified_request(),
        target_datetime=datetime(
            2027,
            10,
            20,
            9,
            15,
        ),
    )

    context = build_reading_context(
        chart_result
    )

    years = [
        item["year"]
        for item in context[
            "luck"
        ][
            "five_year_luck"
        ]
    ]

    assert years == [
        2027,
        2028,
        2029,
        2030,
        2031,
    ]

    assert (
        context[
            "luck"
        ][
            "five_year_luck"
        ][0][
            "target_datetime"
        ]
        == "2027-10-20T09:15:00"
    )
