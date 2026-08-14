"""
tests/test_reading_prompt_five_year_luck.py

reading_prompt の five_year_luck 対応回帰テスト。

目的
----
reading_context に格納された5年分の運勢データが、
reading_prompt で正しくAI入力へ渡されることを確認する。

主な確認項目
------------
1. build_five_year_prompt_facts() が5件返す
2. 2026～2030年を保持する
3. 丙午→丁未→戊申→己酉→庚戌を保持する
4. 初年度が current_year_remaining になる
5. 2年目以降が full_future_year になる
6. build_user_prompt() に five_year_luck が含まれる
7. future_flow で5年間を比較する指示が含まれる
8. 現在年を年末までの残り期間として扱う指示が含まれる
9. 「○○年は」の連発を避けるルールが含まれる
10. 単年データだけを5年へ引き延ばさないルールが含まれる
11. 2027年開始なら2027～2031へスライドする
12. 出生時刻不明時の推定情報を保持する
13. consultation_context 連動を壊さない
14. 元 reading_context を変更しない
15. five_year_luck がない旧contextでも後方互換を維持する
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

from engine.chart import calculate_chart
from engine.consultation_context import (
    build_consultation_context,
)
from engine.reading_context import (
    build_reading_context,
)
from engine.reading_prompt import (
    build_five_year_prompt_facts,
    build_reading_request,
    build_section_prompt,
    build_user_prompt,
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


def build_verified_reading_context():
    chart_result = calculate_chart(
        make_verified_request(),
        target_datetime=TARGET_DATETIME,
    )

    return build_reading_context(
        chart_result
    )


# ============================================================
# 1. Five-year facts
# ============================================================


def test_build_five_year_prompt_facts_returns_list():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    assert isinstance(
        result,
        list,
    )


def test_build_five_year_prompt_facts_has_five_entries():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    assert len(result) == 5


def test_build_five_year_prompt_facts_year_sequence():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    assert [
        item["year"]
        for item in result
    ] == EXPECTED_YEARS


def test_build_five_year_prompt_facts_ganzhi_sequence():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    assert [
        item[
            "annual_luck"
        ][
            "ganzhi"
        ]
        for item in result
    ] == EXPECTED_ANNUAL_GANZHI


# ============================================================
# 2. Period type
# ============================================================


def test_first_year_is_current_year_remaining():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    assert (
        result[0][
            "period_type"
        ]
        == "current_year_remaining"
    )


def test_future_years_are_full_future_year():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    assert all(
        item[
            "period_type"
        ]
        == "full_future_year"
        for item
        in result[1:]
    )


# ============================================================
# 3. Structure
# ============================================================


def test_five_year_prompt_fact_entry_keys():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    required_keys = {
        "year",
        "target_datetime",
        "period_type",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }

    for item in result:
        assert set(
            item.keys()
        ) == required_keys


def test_five_year_prompt_fact_nested_types():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    for item in result:
        assert isinstance(
            item[
                "current_luck"
            ],
            dict,
        )
        assert isinstance(
            item[
                "annual_luck"
            ],
            dict,
        )
        assert isinstance(
            item[
                "integrated_luck"
            ],
            dict,
        )


# ============================================================
# 4. User prompt contains five-year data
# ============================================================


def test_user_prompt_contains_five_year_luck():
    context = build_verified_reading_context()

    prompt = build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    assert (
        "five_year_luck"
        in prompt
    )


def test_user_prompt_contains_all_five_years():
    context = build_verified_reading_context()

    prompt = build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    for year in EXPECTED_YEARS:
        assert str(
            year
        ) in prompt


def test_user_prompt_contains_all_five_ganzhi():
    context = build_verified_reading_context()

    prompt = build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    for ganzhi in EXPECTED_ANNUAL_GANZHI:
        assert ganzhi in prompt


# ============================================================
# 5. Future-flow instructions
# ============================================================


def test_future_flow_prompt_mentions_five_years():
    context = build_verified_reading_context()

    prompt = build_section_prompt(
        context,
        "future_flow",
    )

    assert (
        "5年間"
        in prompt
    )


def test_future_flow_prompt_mentions_year_by_year_comparison():
    context = build_verified_reading_context()

    prompt = build_section_prompt(
        context,
        "future_flow",
    )

    assert (
        "年ごと"
        in prompt
        or "年ごとの"
        in prompt
    )


def test_future_flow_prompt_treats_first_year_as_remaining_period():
    context = build_verified_reading_context()

    prompt = build_section_prompt(
        context,
        "future_flow",
    )

    assert (
        "年末まで"
        in prompt
    )

    assert (
        "残り期間"
        in prompt
    )


def test_future_flow_prompt_discourages_repeating_year_phrase():
    context = build_verified_reading_context()

    prompt = build_section_prompt(
        context,
        "future_flow",
    )

    assert (
        "ここから年末にかけて"
        in prompt
    )

    assert (
        "今年残りの期間"
        in prompt
    )


def test_future_flow_prompt_forbids_stretching_single_year_data():
    context = build_verified_reading_context()

    prompt = build_section_prompt(
        context,
        "future_flow",
    )

    assert (
        "単年データ"
        in prompt
    )

    assert (
        "five_year_luck"
        in prompt
    )


def test_future_flow_prompt_requests_five_year_summary():
    context = build_verified_reading_context()

    prompt = build_section_prompt(
        context,
        "future_flow",
    )

    assert (
        "5年間全体"
        in prompt
        or "5年間を俯瞰"
        in prompt
    )


# ============================================================
# 6. Current year / future year distinction
# ============================================================


def test_prompt_contains_current_year_period_type():
    context = build_verified_reading_context()

    prompt = build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    assert (
        "current_year_remaining"
        in prompt
    )


def test_prompt_contains_future_year_period_type():
    context = build_verified_reading_context()

    prompt = build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    assert (
        "full_future_year"
        in prompt
    )


# ============================================================
# 7. Integrated-luck consistency
# ============================================================


def test_five_year_prompt_facts_integrated_ganzhi_matches_annual():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    for item in result:
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


def test_five_year_prompt_facts_integrated_ganzhi_matches_current():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    for item in result:
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
# 8. Sliding year
# ============================================================


def test_prompt_five_year_luck_slides_with_target_year():
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

    result = build_five_year_prompt_facts(
        context
    )

    assert [
        item["year"]
        for item in result
    ] == [
        2027,
        2028,
        2029,
        2030,
        2031,
    ]


# ============================================================
# 9. Unknown birth time
# ============================================================


def test_unknown_birth_time_keeps_estimated_flags():
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

    result = build_five_year_prompt_facts(
        context
    )

    assert len(result) == 5

    for item in result:
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


def test_known_birth_time_keeps_non_estimated_flags():
    context = build_verified_reading_context()

    result = build_five_year_prompt_facts(
        context
    )

    for item in result:
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
# 10. Consultation context compatibility
# ============================================================


def test_future_flow_prompt_with_consultation_context():
    context = build_verified_reading_context()

    consultation = (
        build_consultation_context(
            concern=(
                "今後の仕事の方向性を"
                "どう考えればよいか知りたい"
            ),
            desired_future=(
                "無理なく長く続けられる"
                "働き方を見つけたい"
            ),
        )
    )

    prompt = build_section_prompt(
        context,
        "future_flow",
        consultation_context=(
            consultation
        ),
    )

    assert (
        "今後の仕事の方向性"
        in prompt
    )

    assert (
        "5年間"
        in prompt
    )

    assert (
        "five_year_luck"
        in prompt
    )


def test_reading_request_with_consultation_and_five_year_luck():
    context = build_verified_reading_context()

    consultation = (
        build_consultation_context(
            concern=(
                "今後5年間の仕事運を"
                "知りたい"
            ),
            desired_future=(
                "自分に合う働き方を"
                "見つけたい"
            ),
        )
    )

    request = build_reading_request(
        context,
        consultation_context=(
            consultation
        ),
        sections=(
            "future_flow",
        ),
    )

    assert (
        request[
            "validation"
        ][
            "valid"
        ]
        is True
    )

    assert len(
        request[
            "messages"
        ]
    ) == 2

    user_prompt = request[
        "messages"
    ][1][
        "content"
    ]

    assert (
        "5年間"
        in user_prompt
    )

    assert (
        "今後5年間の仕事運"
        in user_prompt
    )


# ============================================================
# 11. No mutation
# ============================================================


def test_build_five_year_prompt_facts_does_not_mutate_context():
    context = build_verified_reading_context()

    original = deepcopy(
        context
    )

    build_five_year_prompt_facts(
        context
    )

    assert context == original


def test_build_user_prompt_does_not_mutate_context():
    context = build_verified_reading_context()

    original = deepcopy(
        context
    )

    build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    assert context == original


# ============================================================
# 12. Backward compatibility
# ============================================================


def test_old_context_without_five_year_luck_returns_empty_list():
    context = build_verified_reading_context()

    context[
        "luck"
    ].pop(
        "five_year_luck"
    )

    result = build_five_year_prompt_facts(
        context
    )

    assert result == []


def test_old_context_without_five_year_luck_can_build_user_prompt():
    context = build_verified_reading_context()

    context[
        "luck"
    ].pop(
        "five_year_luck"
    )

    prompt = build_user_prompt(
        context,
        sections=(
            "future_flow",
        ),
    )

    assert isinstance(
        prompt,
        str,
    )

    assert prompt.strip()


# ============================================================
# 13. Reproducibility
# ============================================================


def test_five_year_prompt_facts_reproducible():
    context = build_verified_reading_context()

    first = build_five_year_prompt_facts(
        context
    )

    second = build_five_year_prompt_facts(
        context
    )

    assert first == second


def test_future_flow_prompt_reproducible():
    context = build_verified_reading_context()

    first = build_section_prompt(
        context,
        "future_flow",
    )

    second = build_section_prompt(
        context,
        "future_flow",
    )

    assert first == second
