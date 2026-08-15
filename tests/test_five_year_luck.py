"""
tests/test_five_year_luck.py

five_year_luck v1 の回帰テスト。

目的
----
engine.chart.calculate_chart() に追加された five_year_luck が、

1. 鑑定基準年を含む5年間を返す
2. 初年度は実際の target_datetime を使用する
3. 翌年以降は各年7月1日12:00を代表日時として使用する
4. 各年ごとに current_luck を再評価する
5. 各年ごとに annual_luck を計算する
6. 各年ごとに integrated_luck を再計算する
7. 既存の current_luck / annual_luck / integrated_luck を変更しない
8. 同じ target_datetime なら結果が再現可能である

ことを固定する。

注意
----
このテストは「古典上の運勢の最終正解」を固定するものではない。
five_year_luck の計算パイプラインとデータ整合性を回帰固定する。
"""

from datetime import datetime
from types import SimpleNamespace

from engine.annual_luck import (
    calculate_annual_luck_for_datetime,
)
from engine.chart import calculate_chart
from engine.current_luck import (
    evaluate_current_luck,
)
from engine.integrated_luck import (
    calculate_integrated_luck,
)


# ============================================================
# Fixed target
# ============================================================


TARGET_DATETIME = datetime(
    2026,
    8,
    15,
    10,
    30,
)


# ============================================================
# Request helpers
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


def calculate_verified_chart():
    return calculate_chart(
        make_verified_request(),
        target_datetime=TARGET_DATETIME,
    )


# ============================================================
# Basic structure
# ============================================================


def test_chart_contains_five_year_luck():
    result = calculate_verified_chart()

    assert "five_year_luck" in result
    assert isinstance(
        result["five_year_luck"],
        list,
    )


def test_five_year_luck_has_exactly_five_entries():
    result = calculate_verified_chart()

    five_year_luck = result[
        "five_year_luck"
    ]

    assert len(five_year_luck) == 5


def test_five_year_luck_year_sequence():
    result = calculate_verified_chart()

    years = [
        item["year"]
        for item in result[
            "five_year_luck"
        ]
    ]

    assert years == [
        2026,
        2027,
        2028,
        2029,
        2030,
    ]


def test_five_year_luck_entry_structure():
    result = calculate_verified_chart()

    required_keys = {
        "year",
        "target_datetime",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }

    for item in result[
        "five_year_luck"
    ]:
        assert required_keys.issubset(
            item.keys()
        )

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
# Target datetime rules
# ============================================================


def test_five_year_luck_first_year_uses_actual_target_datetime():
    result = calculate_verified_chart()

    first = result[
        "five_year_luck"
    ][0]

    assert (
        first["target_datetime"]
        == TARGET_DATETIME.isoformat()
    )


def test_five_year_luck_future_years_use_july_first_noon():
    result = calculate_verified_chart()

    expected = [
        "2027-07-01T12:00:00",
        "2028-07-01T12:00:00",
        "2029-07-01T12:00:00",
        "2030-07-01T12:00:00",
    ]

    actual = [
        item["target_datetime"]
        for item in result[
            "five_year_luck"
        ][1:]
    ]

    assert actual == expected


# ============================================================
# Existing one-year results are preserved
# ============================================================


def test_five_year_luck_first_entry_matches_existing_current_luck():
    result = calculate_verified_chart()

    assert (
        result["five_year_luck"][0][
            "current_luck"
        ]
        == result["current_luck"]
    )


def test_five_year_luck_first_entry_matches_existing_annual_luck():
    result = calculate_verified_chart()

    assert (
        result["five_year_luck"][0][
            "annual_luck"
        ]
        == result["annual_luck"]
    )


def test_five_year_luck_first_entry_matches_existing_integrated_luck():
    result = calculate_verified_chart()

    assert (
        result["five_year_luck"][0][
            "integrated_luck"
        ]
        == result["integrated_luck"]
    )


# ============================================================
# Annual luck consistency
# ============================================================


def test_five_year_luck_annual_effective_year_matches_entry_year():
    result = calculate_verified_chart()

    for item in result[
        "five_year_luck"
    ]:
        assert (
            item["annual_luck"][
                "effective_year"
            ]
            == item["year"]
        )


def test_five_year_luck_annual_calendar_year_matches_entry_year():
    result = calculate_verified_chart()

    for item in result[
        "five_year_luck"
    ]:
        assert (
            item["annual_luck"][
                "calendar_year"
            ]
            == item["year"]
        )


def test_five_year_luck_expected_ganzhi_sequence():
    result = calculate_verified_chart()

    ganzhi = [
        item["annual_luck"]["ganzhi"]
        for item in result[
            "five_year_luck"
        ]
    ]

    assert ganzhi == [
        "丙午",
        "丁未",
        "戊申",
        "己酉",
        "庚戌",
    ]


# ============================================================
# Direct engine-call consistency
# ============================================================


def _birth_datetime_for_verified_chart():
    """
    chart.py が既知出生時刻で大運計算へ渡す
    timezone-naive の出生日時と同じ条件を再現する。
    """
    return datetime(
        1985,
        7,
        17,
        21,
        50,
    )


def test_each_year_current_luck_matches_direct_engine_call():
    result = calculate_verified_chart()

    birth_datetime = (
        _birth_datetime_for_verified_chart()
    )

    for item in result[
        "five_year_luck"
    ]:
        target = datetime.fromisoformat(
            item["target_datetime"]
        )

        expected = evaluate_current_luck(
            birth_datetime=birth_datetime,
            target_datetime=target,
            luck_pillars=result[
                "luck_pillars"
            ],
        )

        assert (
            item["current_luck"]
            == expected
        )


def test_each_year_annual_luck_matches_direct_engine_call():
    result = calculate_verified_chart()

    for item in result[
        "five_year_luck"
    ]:
        target = datetime.fromisoformat(
            item["target_datetime"]
        )

        expected = (
            calculate_annual_luck_for_datetime(
                target_datetime=target,
                day_master_stem=result[
                    "day_master"
                ][
                    "stem"
                ],
                useful_gods=result[
                    "useful_gods"
                ],
                current_luck=item[
                    "current_luck"
                ],
            )
        )

        assert (
            item["annual_luck"]
            == expected
        )


def test_each_year_integrated_luck_matches_direct_engine_call():
    result = calculate_verified_chart()

    for item in result[
        "five_year_luck"
    ]:
        expected = (
            calculate_integrated_luck(
                current_luck=item[
                    "current_luck"
                ],
                annual_luck=item[
                    "annual_luck"
                ],
                useful_gods=result[
                    "useful_gods"
                ],
            )
        )

        assert (
            item["integrated_luck"]
            == expected
        )


# ============================================================
# Internal consistency
# ============================================================


def test_each_integrated_luck_references_same_year_annual_ganzhi():
    result = calculate_verified_chart()

    for item in result[
        "five_year_luck"
    ]:
        assert (
            item["integrated_luck"][
                "annual_luck_ganzhi"
            ]
            == item["annual_luck"][
                "ganzhi"
            ]
        )


def test_each_integrated_luck_references_same_current_luck():
    result = calculate_verified_chart()

    for item in result[
        "five_year_luck"
    ]:
        current_pillar = item[
            "current_luck"
        ].get(
            "current_luck_pillar"
        )

        if current_pillar is None:
            # 起運前など current_luck_pillar が存在しないケースは、
            # integrated_luck 側の仕様に委ねる。
            continue

        assert (
            item["integrated_luck"][
                "current_luck_ganzhi"
            ]
            == current_pillar[
                "ganzhi"
            ]
        )


# ============================================================
# Reproducibility
# ============================================================


def test_five_year_luck_fixed_target_is_reproducible():
    request = make_verified_request()

    first = calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )

    second = calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )

    assert (
        first["five_year_luck"]
        == second["five_year_luck"]
    )


# ============================================================
# Different start year
# ============================================================


def test_five_year_luck_slides_with_target_year():
    result = calculate_chart(
        make_verified_request(),
        target_datetime=datetime(
            2027,
            10,
            20,
            9,
            15,
        ),
    )

    years = [
        item["year"]
        for item in result[
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
        result["five_year_luck"][0][
            "target_datetime"
        ]
        == "2027-10-20T09:15:00"
    )

    assert (
        result["five_year_luck"][1][
            "target_datetime"
        ]
        == "2028-07-01T12:00:00"
    )


# ============================================================
# Unknown birth time regression
# ============================================================


def test_five_year_luck_supports_unknown_birth_time():
    request = make_request(
        birth_date="1988-08-08",
        birth_time=None,
        birth_place="神奈川県",
        gender="male",
    )

    result = calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )

    assert (
        result["birth_time_status"][
            "known"
        ]
        is False
    )

    assert len(
        result["five_year_luck"]
    ) == 5

    for item in result[
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
