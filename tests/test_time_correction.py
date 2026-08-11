"""
tests/test_time_correction.py

四柱推命 出生時刻補正エンジン
単体テスト v1

対象
----
engine/time_correction.py

目的
----
time_correction_v1 の以下の仕様を固定する。

・デフォルトはstandard
・standardでは日時を変更しない
・日本標準時基準経度は東経135度
・経度1度につき4分補正
・135度より東はプラス補正
・135度より西はマイナス補正
・longitude直接指定をbirth_placeより優先
・都道府県代表座標から経度を解決できる
・日付跨ぎを正しく検出する
・月跨ぎ、年跨ぎを正しく検出する
・入力datetimeのtzinfoを維持する
・apparent_solarはv1では未実装
・不正入力を明示的に拒否する
・API向けdictへ安全に変換できる
・メタデータが実装仕様と一致する

重要
----
このテストではまだ
calculate_four_pillars() との統合は行わない。

時刻補正モジュール単体の契約を
先に固定する。

Version
-------
test_time_correction_v1
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engine.time_correction import (
    IMPLEMENTED_TIME_CORRECTION_MODES,
    MODE_APPARENT_SOLAR,
    MODE_LONGITUDE,
    MODE_STANDARD,
    PLACE_COORDINATES,
    STANDARD_MERIDIAN,
    SUPPORTED_TIME_CORRECTION_MODES,
    TIME_CORRECTION_METHOD,
    TIME_CORRECTION_STATUS,
    TIME_CORRECTION_VERSION,
    TimeCorrectionResult,
    apply_time_correction,
    calculate_equation_of_time_minutes,
    calculate_longitude_offset_minutes,
    calculate_longitude_offset_seconds,
    get_corrected_datetime,
    get_place_coordinates,
    get_place_latitude,
    get_place_longitude,
    get_time_correction_dict,
    get_time_correction_metadata,
    normalize_time_correction_result,
    resolve_coordinates,
)


# ============================================================
# Constants
# ============================================================


JST = ZoneInfo(
    "Asia/Tokyo"
)


# ============================================================
# Helpers
# ============================================================


def make_datetime(
    year: int = 1984,
    month: int = 7,
    day: int = 10,
    hour: int = 22,
    minute: int = 45,
    second: int = 0,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        tzinfo=JST,
    )


# ============================================================
# 1. Constants
# ============================================================


def test_version_constant():
    assert (
        TIME_CORRECTION_VERSION
        == "time_correction_v1"
    )


def test_method_constant():
    assert (
        TIME_CORRECTION_METHOD
        == "standard_or_longitude_v1"
    )


def test_status_constant():
    assert (
        TIME_CORRECTION_STATUS
        == "longitude_ready"
    )


def test_standard_meridian():
    assert (
        STANDARD_MERIDIAN
        == 135.0
    )


def test_supported_modes():
    assert (
        SUPPORTED_TIME_CORRECTION_MODES
        == (
            "standard",
            "longitude",
            "apparent_solar",
        )
    )


def test_implemented_modes():
    assert (
        IMPLEMENTED_TIME_CORRECTION_MODES
        == (
            "standard",
            "longitude",
        )
    )


def test_mode_constants():
    assert MODE_STANDARD == "standard"
    assert MODE_LONGITUDE == "longitude"

    assert (
        MODE_APPARENT_SOLAR
        == "apparent_solar"
    )


# ============================================================
# 2. Place master
# ============================================================


def test_place_master_contains_47_prefectures():
    assert len(
        PLACE_COORDINATES
    ) == 47


@pytest.mark.parametrize(
    "prefecture",
    (
        "北海道",
        "東京都",
        "愛知県",
        "石川県",
        "福岡県",
        "沖縄県",
    ),
)
def test_place_master_contains_known_prefectures(
    prefecture,
):
    assert (
        prefecture
        in PLACE_COORDINATES
    )


def test_get_place_coordinates_aichi():
    result = get_place_coordinates(
        "愛知県"
    )

    assert result == {
        "latitude": 35.1802,
        "longitude": 136.9066,
    }


def test_get_place_longitude_aichi():
    assert (
        get_place_longitude(
            "愛知県"
        )
        == pytest.approx(
            136.9066
        )
    )


def test_get_place_latitude_aichi():
    assert (
        get_place_latitude(
            "愛知県"
        )
        == pytest.approx(
            35.1802
        )
    )


def test_get_place_coordinates_returns_copy():
    first = get_place_coordinates(
        "愛知県"
    )

    first[
        "longitude"
    ] = 0.0

    second = get_place_coordinates(
        "愛知県"
    )

    assert (
        second[
            "longitude"
        ]
        == pytest.approx(
            136.9066
        )
    )


def test_get_place_coordinates_strips_whitespace():
    assert (
        get_place_coordinates(
            "  愛知県  "
        )
        == get_place_coordinates(
            "愛知県"
        )
    )


def test_unknown_place_raises_value_error():
    with pytest.raises(
        ValueError,
        match="座標を解決できません",
    ):
        get_place_coordinates(
            "存在しない県"
        )


def test_empty_place_raises_value_error():
    with pytest.raises(
        ValueError,
        match="birth_place",
    ):
        get_place_coordinates(
            "   "
        )


def test_non_string_place_raises_type_error():
    with pytest.raises(
        TypeError,
        match="birth_place",
    ):
        get_place_coordinates(
            123
        )


# ============================================================
# 3. Longitude offset
# ============================================================


def test_135_degrees_is_zero_minutes():
    assert (
        calculate_longitude_offset_minutes(
            135.0
        )
        == pytest.approx(
            0.0
        )
    )


def test_one_degree_east_is_plus_four_minutes():
    assert (
        calculate_longitude_offset_minutes(
            136.0
        )
        == pytest.approx(
            4.0
        )
    )


def test_one_degree_west_is_minus_four_minutes():
    assert (
        calculate_longitude_offset_minutes(
            134.0
        )
        == pytest.approx(
            -4.0
        )
    )


def test_tokyo_longitude_offset():
    result = (
        calculate_longitude_offset_minutes(
            139.6503
        )
    )

    assert result == pytest.approx(
        18.6012
    )


def test_aichi_longitude_offset():
    result = (
        calculate_longitude_offset_minutes(
            136.9066
        )
    )

    assert result == pytest.approx(
        7.6264
    )


def test_fukuoka_longitude_offset():
    result = (
        calculate_longitude_offset_minutes(
            130.4017
        )
    )

    assert result == pytest.approx(
        -18.3932
    )


def test_longitude_offset_seconds():
    assert (
        calculate_longitude_offset_seconds(
            136.0
        )
        == pytest.approx(
            240.0
        )
    )


def test_custom_standard_meridian():
    assert (
        calculate_longitude_offset_minutes(
            140.0,
            140.0,
        )
        == pytest.approx(
            0.0
        )
    )


@pytest.mark.parametrize(
    "longitude",
    (
        -180.0,
        180.0,
        0.0,
        135.0,
    ),
)
def test_valid_longitude_boundaries(
    longitude,
):
    result = (
        calculate_longitude_offset_minutes(
            longitude
        )
    )

    assert isinstance(
        result,
        float,
    )


@pytest.mark.parametrize(
    "longitude",
    (
        -180.0001,
        180.0001,
        -999.0,
        999.0,
    ),
)
def test_invalid_longitude_range(
    longitude,
):
    with pytest.raises(
        ValueError,
        match="longitude",
    ):
        calculate_longitude_offset_minutes(
            longitude
        )


@pytest.mark.parametrize(
    "longitude",
    (
        None,
        "136.0",
        [],
        {},
        True,
    ),
)
def test_invalid_longitude_type(
    longitude,
):
    with pytest.raises(
        TypeError,
        match="longitude",
    ):
        calculate_longitude_offset_minutes(
            longitude
        )


# ============================================================
# 4. Coordinate resolution
# ============================================================


def test_resolve_coordinates_from_birth_place():
    result = resolve_coordinates(
        birth_place="愛知県"
    )

    assert result == {
        "birth_place": "愛知県",
        "latitude": 35.1802,
        "longitude": 136.9066,
        "source": (
            "internal_place_master"
        ),
    }


def test_explicit_longitude_has_priority():
    result = resolve_coordinates(
        birth_place="愛知県",
        longitude=140.0,
    )

    assert (
        result[
            "longitude"
        ]
        == pytest.approx(
            140.0
        )
    )

    assert (
        result[
            "source"
        ]
        == "explicit_coordinates"
    )


def test_explicit_latitude_and_longitude():
    result = resolve_coordinates(
        birth_place="愛知県",
        latitude=35.0,
        longitude=140.0,
    )

    assert (
        result[
            "latitude"
        ]
        == pytest.approx(
            35.0
        )
    )

    assert (
        result[
            "longitude"
        ]
        == pytest.approx(
            140.0
        )
    )


def test_explicit_longitude_can_work_without_place():
    result = resolve_coordinates(
        longitude=136.5
    )

    assert (
        result[
            "birth_place"
        ]
        is None
    )

    assert (
        result[
            "latitude"
        ]
        is None
    )

    assert (
        result[
            "longitude"
        ]
        == pytest.approx(
            136.5
        )
    )

    assert (
        result[
            "source"
        ]
        == "explicit_coordinates"
    )


def test_no_coordinates_returns_none_values():
    result = resolve_coordinates()

    assert result == {
        "birth_place": None,
        "latitude": None,
        "longitude": None,
        "source": "none",
    }


@pytest.mark.parametrize(
    "latitude",
    (
        -90.0,
        0.0,
        35.0,
        90.0,
    ),
)
def test_valid_latitude(
    latitude,
):
    result = resolve_coordinates(
        latitude=latitude,
        longitude=135.0,
    )

    assert (
        result[
            "latitude"
        ]
        == pytest.approx(
            latitude
        )
    )


@pytest.mark.parametrize(
    "latitude",
    (
        -90.0001,
        90.0001,
        -999.0,
        999.0,
    ),
)
def test_invalid_latitude_range(
    latitude,
):
    with pytest.raises(
        ValueError,
        match="latitude",
    ):
        resolve_coordinates(
            latitude=latitude,
            longitude=135.0,
        )


@pytest.mark.parametrize(
    "latitude",
    (
        "35",
        [],
        {},
        True,
    ),
)
def test_invalid_latitude_type(
    latitude,
):
    with pytest.raises(
        TypeError,
        match="latitude",
    ):
        resolve_coordinates(
            latitude=latitude,
            longitude=135.0,
        )


# ============================================================
# 5. Standard mode
# ============================================================


def test_standard_mode_returns_result_object():
    target = make_datetime()

    result = apply_time_correction(
        target
    )

    assert isinstance(
        result,
        TimeCorrectionResult,
    )


def test_standard_is_default():
    target = make_datetime()

    result = apply_time_correction(
        target
    )

    assert (
        result.mode
        == MODE_STANDARD
    )


def test_standard_does_not_change_datetime():
    target = make_datetime()

    result = apply_time_correction(
        target,
        mode="standard",
    )

    assert (
        result.original_datetime
        == target
    )

    assert (
        result.corrected_datetime
        == target
    )


def test_standard_offset_is_zero():
    target = make_datetime()

    result = apply_time_correction(
        target,
        mode="standard",
    )

    assert (
        result.longitude_offset_minutes
        == pytest.approx(
            0.0
        )
    )

    assert (
        result.equation_of_time_minutes
        == pytest.approx(
            0.0
        )
    )

    assert (
        result.total_offset_minutes
        == pytest.approx(
            0.0
        )
    )


def test_standard_does_not_resolve_place_implicitly():
    """
    standardでは出生地があっても
    補正を実行しない。

    既存仕様を変えないことを優先する。
    """

    target = make_datetime()

    result = apply_time_correction(
        target,
        birth_place="愛知県",
        mode="standard",
    )

    assert (
        result.corrected_datetime
        == target
    )

    assert (
        result.longitude
        is None
    )

    assert (
        result.latitude
        is None
    )


def test_standard_accepts_explicit_coordinates_without_correction():
    target = make_datetime()

    result = apply_time_correction(
        target,
        latitude=35.0,
        longitude=136.0,
        mode="standard",
    )

    assert (
        result.latitude
        == pytest.approx(
            35.0
        )
    )

    assert (
        result.longitude
        == pytest.approx(
            136.0
        )
    )

    assert (
        result.corrected_datetime
        == target
    )


def test_standard_date_flags_are_false():
    target = make_datetime()

    result = apply_time_correction(
        target
    )

    assert (
        result.date_changed
        is False
    )

    assert (
        result.year_changed
        is False
    )

    assert (
        result.month_changed
        is False
    )

    assert (
        result.day_changed
        is False
    )


# ============================================================
# 6. Longitude mode
# ============================================================


def test_longitude_135_does_not_change_datetime():
    target = make_datetime()

    result = apply_time_correction(
        target,
        longitude=135.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == target
    )

    assert (
        result.total_offset_minutes
        == pytest.approx(
            0.0
        )
    )


def test_longitude_one_degree_east_adds_four_minutes():
    target = make_datetime(
        hour=12,
        minute=0,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == make_datetime(
            hour=12,
            minute=4,
        )
    )


def test_longitude_one_degree_west_subtracts_four_minutes():
    target = make_datetime(
        hour=12,
        minute=0,
    )

    result = apply_time_correction(
        target,
        longitude=134.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == make_datetime(
            hour=11,
            minute=56,
        )
    )


def test_aichi_place_correction():
    target = make_datetime(
        hour=22,
        minute=45,
    )

    result = apply_time_correction(
        target,
        birth_place="愛知県",
        mode="longitude",
    )

    assert (
        result.longitude
        == pytest.approx(
            136.9066
        )
    )

    assert (
        result.longitude_offset_minutes
        == pytest.approx(
            7.6264
        )
    )

    assert (
        result.total_offset_minutes
        == pytest.approx(
            7.6264
        )
    )

    expected = datetime(
        1984,
        7,
        10,
        22,
        52,
        37,
        584000,
        tzinfo=JST,
    )

    assert (
        result.corrected_datetime
        == expected
    )


def test_tokyo_place_is_positive_correction():
    target = make_datetime(
        hour=12,
        minute=0,
    )

    result = apply_time_correction(
        target,
        birth_place="東京都",
        mode="longitude",
    )

    assert (
        result.total_offset_minutes
        > 0
    )

    assert (
        result.corrected_datetime
        > target
    )


def test_fukuoka_place_is_negative_correction():
    target = make_datetime(
        hour=12,
        minute=0,
    )

    result = apply_time_correction(
        target,
        birth_place="福岡県",
        mode="longitude",
    )

    assert (
        result.total_offset_minutes
        < 0
    )

    assert (
        result.corrected_datetime
        < target
    )


def test_longitude_mode_source_from_place_master():
    target = make_datetime()

    result = apply_time_correction(
        target,
        birth_place="愛知県",
        mode="longitude",
    )

    assert (
        result.source
        == "internal_place_master"
    )


def test_longitude_mode_source_explicit():
    target = make_datetime()

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.source
        == "explicit_coordinates"
    )


def test_longitude_requires_resolvable_longitude():
    target = make_datetime()

    with pytest.raises(
        ValueError,
        match="経度が必要",
    ):
        apply_time_correction(
            target,
            mode="longitude",
        )


def test_longitude_unknown_place_fails():
    target = make_datetime()

    with pytest.raises(
        ValueError,
        match="座標を解決できません",
    ):
        apply_time_correction(
            target,
            birth_place="存在しない県",
            mode="longitude",
        )


def test_explicit_longitude_overrides_unknown_place():
    """
    経度が明示指定されているなら、
    birth_placeが内部マスタに無くても
    経度補正自体は実行できる。
    """

    target = make_datetime()

    result = apply_time_correction(
        target,
        birth_place="名古屋市",
        longitude=136.9066,
        mode="longitude",
    )

    assert (
        result.longitude
        == pytest.approx(
            136.9066
        )
    )

    assert (
        result.source
        == "explicit_coordinates"
    )


# ============================================================
# 7. Date boundary
# ============================================================


def test_positive_correction_crosses_to_next_day():
    target = datetime(
        2026,
        8,
        11,
        23,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2026,
            8,
            12,
            0,
            2,
            tzinfo=JST,
        )
    )

    assert (
        result.date_changed
        is True
    )

    assert (
        result.day_changed
        is True
    )

    assert (
        result.month_changed
        is False
    )

    assert (
        result.year_changed
        is False
    )


def test_negative_correction_crosses_to_previous_day():
    target = datetime(
        2026,
        8,
        11,
        0,
        2,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=134.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2026,
            8,
            10,
            23,
            58,
            tzinfo=JST,
        )
    )

    assert (
        result.date_changed
        is True
    )

    assert (
        result.day_changed
        is True
    )


def test_positive_correction_crosses_month():
    target = datetime(
        2026,
        8,
        31,
        23,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2026,
            9,
            1,
            0,
            2,
            tzinfo=JST,
        )
    )

    assert (
        result.date_changed
        is True
    )

    assert (
        result.month_changed
        is True
    )

    assert (
        result.year_changed
        is False
    )


def test_positive_correction_crosses_year():
    target = datetime(
        2026,
        12,
        31,
        23,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2027,
            1,
            1,
            0,
            2,
            tzinfo=JST,
        )
    )

    assert (
        result.date_changed
        is True
    )

    assert (
        result.month_changed
        is True
    )

    assert (
        result.year_changed
        is True
    )


def test_negative_correction_crosses_previous_year():
    target = datetime(
        2026,
        1,
        1,
        0,
        2,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=134.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2025,
            12,
            31,
            23,
            58,
            tzinfo=JST,
        )
    )

    assert (
        result.year_changed
        is True
    )

    assert (
        result.month_changed
        is True
    )

    assert (
        result.day_changed
        is True
    )


# ============================================================
# 8. Timezone preservation
# ============================================================


def test_timezone_is_preserved_standard():
    target = make_datetime()

    result = apply_time_correction(
        target,
        mode="standard",
    )

    assert (
        result.corrected_datetime.tzinfo
        == JST
    )


def test_timezone_is_preserved_longitude():
    target = make_datetime()

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime.tzinfo
        == JST
    )


def test_naive_datetime_remains_naive():
    target = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    assert (
        result.corrected_datetime.tzinfo
        is None
    )


# ============================================================
# 9. Mode normalization / validation
# ============================================================


@pytest.mark.parametrize(
    "mode",
    (
        "STANDARD",
        " Standard ",
        "standard",
    ),
)
def test_standard_mode_is_normalized(
    mode,
):
    result = apply_time_correction(
        make_datetime(),
        mode=mode,
    )

    assert (
        result.mode
        == "standard"
    )


@pytest.mark.parametrize(
    "mode",
    (
        "LONGITUDE",
        " Longitude ",
        "longitude",
    ),
)
def test_longitude_mode_is_normalized(
    mode,
):
    result = apply_time_correction(
        make_datetime(),
        longitude=135.0,
        mode=mode,
    )

    assert (
        result.mode
        == "longitude"
    )


def test_unknown_mode_raises_value_error():
    with pytest.raises(
        ValueError,
        match=(
            "standard/longitude/"
            "apparent_solar"
        ),
    ):
        apply_time_correction(
            make_datetime(),
            mode="unknown",
        )


def test_empty_mode_raises_value_error():
    with pytest.raises(
        ValueError,
        match="mode",
    ):
        apply_time_correction(
            make_datetime(),
            mode="   ",
        )


def test_non_string_mode_raises_type_error():
    with pytest.raises(
        TypeError,
        match="mode",
    ):
        apply_time_correction(
            make_datetime(),
            mode=123,
        )


def test_non_datetime_raises_type_error():
    with pytest.raises(
        TypeError,
        match="birth_datetime",
    ):
        apply_time_correction(
            "1984-07-10",
        )


# ============================================================
# 10. Apparent solar v1 policy
# ============================================================


def test_apparent_solar_is_reserved_but_not_implemented():
    with pytest.raises(
        NotImplementedError,
        match="未実装",
    ):
        apply_time_correction(
            make_datetime(),
            birth_place="愛知県",
            mode="apparent_solar",
        )


def test_equation_of_time_is_not_implemented():
    with pytest.raises(
        NotImplementedError,
        match="未実装",
    ):
        calculate_equation_of_time_minutes(
            make_datetime()
        )


def test_equation_of_time_validates_datetime_first():
    with pytest.raises(
        TypeError,
        match="birth_datetime",
    ):
        calculate_equation_of_time_minutes(
            "1984-07-10"
        )


# ============================================================
# 11. Result object
# ============================================================


def test_result_contains_method_and_status():
    result = apply_time_correction(
        make_datetime()
    )

    assert (
        result.method
        == TIME_CORRECTION_METHOD
    )

    assert (
        result.status
        == TIME_CORRECTION_STATUS
    )


def test_result_is_frozen():
    result = apply_time_correction(
        make_datetime()
    )

    with pytest.raises(
        Exception
    ):
        result.mode = "longitude"


def test_result_to_dict_keeps_datetime_by_default():
    target = make_datetime()

    result = apply_time_correction(
        target
    ).to_dict()

    assert isinstance(
        result[
            "original_datetime"
        ],
        datetime,
    )

    assert isinstance(
        result[
            "corrected_datetime"
        ],
        datetime,
    )


def test_result_to_dict_can_serialize_datetime():
    target = make_datetime()

    result = apply_time_correction(
        target
    ).to_dict(
        serialize_datetime=True
    )

    assert (
        result[
            "original_datetime"
        ]
        == target.isoformat()
    )

    assert (
        result[
            "corrected_datetime"
        ]
        == target.isoformat()
    )


# ============================================================
# 12. Convenience API
# ============================================================


def test_get_corrected_datetime_standard():
    target = make_datetime()

    assert (
        get_corrected_datetime(
            target
        )
        == target
    )


def test_get_corrected_datetime_longitude():
    target = make_datetime(
        hour=12,
        minute=0,
    )

    assert (
        get_corrected_datetime(
            target,
            longitude=136.0,
            mode="longitude",
        )
        == make_datetime(
            hour=12,
            minute=4,
        )
    )


def test_get_time_correction_dict_serializes_by_default():
    target = make_datetime()

    result = (
        get_time_correction_dict(
            target
        )
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        result[
            "original_datetime"
        ]
        == target.isoformat()
    )

    assert (
        result[
            "corrected_datetime"
        ]
        == target.isoformat()
    )


def test_get_time_correction_dict_can_keep_datetime():
    target = make_datetime()

    result = (
        get_time_correction_dict(
            target,
            serialize_datetime=False,
        )
    )

    assert isinstance(
        result[
            "original_datetime"
        ],
        datetime,
    )


# ============================================================
# 13. normalize_time_correction_result
# ============================================================


def test_normalize_result_object():
    target = make_datetime()

    source = apply_time_correction(
        target
    )

    result = (
        normalize_time_correction_result(
            source
        )
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        result[
            "mode"
        ]
        == "standard"
    )


def test_normalize_result_object_serialized():
    target = make_datetime()

    source = apply_time_correction(
        target
    )

    result = (
        normalize_time_correction_result(
            source,
            serialize_datetime=True,
        )
    )

    assert (
        result[
            "original_datetime"
        ]
        == target.isoformat()
    )


def test_normalize_mapping_returns_copy():
    source = {
        "mode": "standard",
        "value": {
            "nested": 1,
        },
    }

    result = (
        normalize_time_correction_result(
            source
        )
    )

    result[
        "value"
    ][
        "nested"
    ] = 999

    assert (
        source[
            "value"
        ][
            "nested"
        ]
        == 1
    )


def test_normalize_mapping_serializes_datetime():
    target = make_datetime()

    source = {
        "original_datetime": target,
        "corrected_datetime": target,
    }

    result = (
        normalize_time_correction_result(
            source,
            serialize_datetime=True,
        )
    )

    assert (
        result[
            "original_datetime"
        ]
        == target.isoformat()
    )

    assert (
        result[
            "corrected_datetime"
        ]
        == target.isoformat()
    )


def test_normalize_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "TimeCorrectionResult"
        ),
    ):
        normalize_time_correction_result(
            123
        )


# ============================================================
# 14. Metadata
# ============================================================


def test_metadata():
    metadata = (
        get_time_correction_metadata()
    )

    assert metadata[
        "version"
    ] == "time_correction_v1"

    assert metadata[
        "method"
    ] == "standard_or_longitude_v1"

    assert metadata[
        "status"
    ] == "longitude_ready"

    assert metadata[
        "default_mode"
    ] == "standard"

    assert metadata[
        "supported_modes"
    ] == [
        "standard",
        "longitude",
        "apparent_solar",
    ]

    assert metadata[
        "implemented_modes"
    ] == [
        "standard",
        "longitude",
    ]

    assert metadata[
        "standard_meridian"
    ] == 135.0

    assert metadata[
        "longitude_minutes_per_degree"
    ] == 4.0

    assert metadata[
        "place_master_count"
    ] == 47

    assert (
        metadata[
            "external_geocoding"
        ]
        is False
    )

    assert (
        metadata[
            "equation_of_time"
        ]
        is False
    )

    assert (
        metadata[
            "apparent_solar"
        ]
        is False
    )


# ============================================================
# 15. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    (
        "birth_place",
        "longitude",
        "mode",
    ),
    (
        (
            None,
            None,
            "standard",
        ),
        (
            None,
            135.0,
            "longitude",
        ),
        (
            "愛知県",
            None,
            "longitude",
        ),
        (
            "東京都",
            None,
            "longitude",
        ),
        (
            "福岡県",
            None,
            "longitude",
        ),
    ),
)
def test_time_correction_is_reproducible(
    birth_place,
    longitude,
    mode,
):
    target = make_datetime()

    first = apply_time_correction(
        target,
        birth_place=birth_place,
        longitude=longitude,
        mode=mode,
    )

    second = apply_time_correction(
        target,
        birth_place=birth_place,
        longitude=longitude,
        mode=mode,
    )

    assert (
        first
        == second
    )


# ============================================================
# 16. Golden examples
# ============================================================


def test_golden_aichi_example():
    """
    1984-07-10 22:45 JST
    愛知県代表経度136.9066度。

    補正:
    +7.6264分
    =
    +7分37.584秒
    """

    target = datetime(
        1984,
        7,
        10,
        22,
        45,
        0,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        birth_place="愛知県",
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            1984,
            7,
            10,
            22,
            52,
            37,
            584000,
            tzinfo=JST,
        )
    )

    assert (
        result.date_changed
        is False
    )


def test_golden_tokyo_example():
    """
    東京都代表経度139.6503度。

    補正:
    +18.6012分
    =
    +18分36.072秒
    """

    target = datetime(
        2026,
        8,
        11,
        12,
        0,
        0,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        birth_place="東京都",
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2026,
            8,
            11,
            12,
            18,
            36,
            72000,
            tzinfo=JST,
        )
    )


def test_golden_fukuoka_example():
    """
    福岡県代表経度130.4017度。

    補正:
    -18.3932分
    =
    -18分23.592秒
    """

    target = datetime(
        2026,
        8,
        11,
        12,
        0,
        0,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        birth_place="福岡県",
        mode="longitude",
    )

    assert (
        result.corrected_datetime
        == datetime(
            2026,
            8,
            11,
            11,
            41,
            36,
            408000,
            tzinfo=JST,
        )
    )


# ============================================================
# 17. Final smoke
# ============================================================


def test_time_correction_final_smoke():
    target = datetime(
        2026,
        8,
        11,
        12,
        0,
        0,
        tzinfo=JST,
    )

    standard = apply_time_correction(
        target,
        mode="standard",
    )

    east = apply_time_correction(
        target,
        longitude=136.0,
        mode="longitude",
    )

    west = apply_time_correction(
        target,
        longitude=134.0,
        mode="longitude",
    )

    assert (
        standard.corrected_datetime
        == target
    )

    assert (
        east.corrected_datetime
        == datetime(
            2026,
            8,
            11,
            12,
            4,
            tzinfo=JST,
        )
    )

    assert (
        west.corrected_datetime
        == datetime(
            2026,
            8,
            11,
            11,
            56,
            tzinfo=JST,
        )
    )

    assert (
        east.total_offset_minutes
        == pytest.approx(
            4.0
        )
    )

    assert (
        west.total_offset_minutes
        == pytest.approx(
            -4.0
        )
    )
