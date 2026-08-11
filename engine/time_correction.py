"""
engine/time_correction.py

四柱推命 出生時刻補正エンジン v1

目的
----
出生日時に対して、
四柱推命で利用する時刻補正を適用する。

初期実装では以下の2モードを正式対応する。

standard
    補正なし。
    既存仕様と完全互換。

longitude
    出生地経度と日本標準時基準経度
    東経135度との差を時刻へ反映する。

apparent_solar
    将来の真太陽時対応用に予約。
    v1では未実装。

設計原則
--------
・補正は四柱計算の前処理として行う。
・補正後日時を時柱だけに使わない。
・補正後日時を年柱・月柱・日柱・時柱
  すべての計算入力として扱う。
・既存挙動を壊さないため、
  デフォルトはstandardとする。
・外部ジオコーディングAPIには依存しない。
・v1では経度を明示指定するか、
  内部の都道府県代表座標から解決する。

重要
----
日本標準時の基準経度は東経135度。

地球は24時間で360度回転するため、

    経度1度 = 4分

として地方平均太陽時補正を計算する。

例
--
東京付近:
    longitude = 139.6503

    (139.6503 - 135.0) * 4
    = 約18.6012分

標準時12:00
    ↓
地方平均太陽時
約12:18:36

Version
-------
time_correction_v1
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping


# ============================================================
# Constants
# ============================================================


TIME_CORRECTION_VERSION = (
    "time_correction_v1"
)

TIME_CORRECTION_METHOD = (
    "standard_or_longitude_v1"
)

TIME_CORRECTION_STATUS = (
    "longitude_ready"
)


STANDARD_MERIDIAN = 135.0


MODE_STANDARD = "standard"
MODE_LONGITUDE = "longitude"
MODE_APPARENT_SOLAR = (
    "apparent_solar"
)


SUPPORTED_TIME_CORRECTION_MODES = (
    MODE_STANDARD,
    MODE_LONGITUDE,
    MODE_APPARENT_SOLAR,
)


IMPLEMENTED_TIME_CORRECTION_MODES = (
    MODE_STANDARD,
    MODE_LONGITUDE,
)


# ============================================================
# Place master
# ============================================================

# 都道府県代表座標。
#
# v1では経度補正の再現性を優先し、
# 外部ジオコーディングAPIは使用しない。
#
# 座標は県庁所在地付近の代表値として扱う。
# 厳密な市区町村座標が必要な場合は、
# API側からlongitudeを直接指定する。

PLACE_COORDINATES: dict[str, dict[str, float]] = {
    "北海道": {
        "latitude": 43.0642,
        "longitude": 141.3469,
    },
    "青森県": {
        "latitude": 40.8244,
        "longitude": 140.7400,
    },
    "岩手県": {
        "latitude": 39.7036,
        "longitude": 141.1527,
    },
    "宮城県": {
        "latitude": 38.2688,
        "longitude": 140.8721,
    },
    "秋田県": {
        "latitude": 39.7186,
        "longitude": 140.1024,
    },
    "山形県": {
        "latitude": 38.2404,
        "longitude": 140.3633,
    },
    "福島県": {
        "latitude": 37.7503,
        "longitude": 140.4676,
    },
    "茨城県": {
        "latitude": 36.3418,
        "longitude": 140.4468,
    },
    "栃木県": {
        "latitude": 36.5657,
        "longitude": 139.8836,
    },
    "群馬県": {
        "latitude": 36.3911,
        "longitude": 139.0608,
    },
    "埼玉県": {
        "latitude": 35.8569,
        "longitude": 139.6489,
    },
    "千葉県": {
        "latitude": 35.6047,
        "longitude": 140.1233,
    },
    "東京都": {
        "latitude": 35.6762,
        "longitude": 139.6503,
    },
    "神奈川県": {
        "latitude": 35.4478,
        "longitude": 139.6425,
    },
    "新潟県": {
        "latitude": 37.9026,
        "longitude": 139.0236,
    },
    "富山県": {
        "latitude": 36.6953,
        "longitude": 137.2113,
    },
    "石川県": {
        "latitude": 36.5947,
        "longitude": 136.6256,
    },
    "福井県": {
        "latitude": 36.0652,
        "longitude": 136.2216,
    },
    "山梨県": {
        "latitude": 35.6642,
        "longitude": 138.5684,
    },
    "長野県": {
        "latitude": 36.6513,
        "longitude": 138.1810,
    },
    "岐阜県": {
        "latitude": 35.3912,
        "longitude": 136.7223,
    },
    "静岡県": {
        "latitude": 34.9769,
        "longitude": 138.3831,
    },
    "愛知県": {
        "latitude": 35.1802,
        "longitude": 136.9066,
    },
    "三重県": {
        "latitude": 34.7303,
        "longitude": 136.5086,
    },
    "滋賀県": {
        "latitude": 35.0045,
        "longitude": 135.8686,
    },
    "京都府": {
        "latitude": 35.0116,
        "longitude": 135.7681,
    },
    "大阪府": {
        "latitude": 34.6863,
        "longitude": 135.5200,
    },
    "兵庫県": {
        "latitude": 34.6913,
        "longitude": 135.1830,
    },
    "奈良県": {
        "latitude": 34.6851,
        "longitude": 135.8048,
    },
    "和歌山県": {
        "latitude": 34.2260,
        "longitude": 135.1675,
    },
    "鳥取県": {
        "latitude": 35.5039,
        "longitude": 134.2381,
    },
    "島根県": {
        "latitude": 35.4723,
        "longitude": 133.0505,
    },
    "岡山県": {
        "latitude": 34.6618,
        "longitude": 133.9344,
    },
    "広島県": {
        "latitude": 34.3966,
        "longitude": 132.4596,
    },
    "山口県": {
        "latitude": 34.1859,
        "longitude": 131.4714,
    },
    "徳島県": {
        "latitude": 34.0658,
        "longitude": 134.5593,
    },
    "香川県": {
        "latitude": 34.3401,
        "longitude": 134.0434,
    },
    "愛媛県": {
        "latitude": 33.8416,
        "longitude": 132.7657,
    },
    "高知県": {
        "latitude": 33.5597,
        "longitude": 133.5311,
    },
    "福岡県": {
        "latitude": 33.5904,
        "longitude": 130.4017,
    },
    "佐賀県": {
        "latitude": 33.2494,
        "longitude": 130.2988,
    },
    "長崎県": {
        "latitude": 32.7503,
        "longitude": 129.8777,
    },
    "熊本県": {
        "latitude": 32.7898,
        "longitude": 130.7417,
    },
    "大分県": {
        "latitude": 33.2382,
        "longitude": 131.6126,
    },
    "宮崎県": {
        "latitude": 31.9111,
        "longitude": 131.4239,
    },
    "鹿児島県": {
        "latitude": 31.5602,
        "longitude": 130.5581,
    },
    "沖縄県": {
        "latitude": 26.2124,
        "longitude": 127.6809,
    },
}


# ============================================================
# Dataclass
# ============================================================


@dataclass(frozen=True)
class TimeCorrectionResult:
    """
    時刻補正結果。

    datetimeは内部処理向けに
    datetime型のまま保持する。
    """

    original_datetime: datetime
    corrected_datetime: datetime

    mode: str

    birth_place: str | None

    latitude: float | None
    longitude: float | None

    standard_meridian: float

    longitude_offset_minutes: float
    equation_of_time_minutes: float
    total_offset_minutes: float

    date_changed: bool
    year_changed: bool
    month_changed: bool
    day_changed: bool

    source: str

    method: str
    status: str

    def to_dict(
        self,
        *,
        serialize_datetime: bool = False,
    ) -> dict[str, Any]:
        """
        dictへ変換する。

        serialize_datetime=Trueの場合は
        datetimeをISO文字列へ変換する。
        """

        result = asdict(
            self
        )

        if serialize_datetime:
            result[
                "original_datetime"
            ] = (
                self
                .original_datetime
                .isoformat()
            )

            result[
                "corrected_datetime"
            ] = (
                self
                .corrected_datetime
                .isoformat()
            )

        return result


# ============================================================
# Validation
# ============================================================


def _validate_datetime(
    value: datetime,
) -> None:
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(
            "birth_datetimeはdatetime型で指定してください。"
        )


def _validate_mode(
    mode: str,
) -> str:
    if not isinstance(
        mode,
        str,
    ):
        raise TypeError(
            "modeは文字列で指定してください。"
        )

    normalized = (
        mode
        .strip()
        .lower()
    )

    if not normalized:
        raise ValueError(
            "modeを指定してください。"
        )

    if (
        normalized
        not in (
            SUPPORTED_TIME_CORRECTION_MODES
        )
    ):
        raise ValueError(
            "modeは"
            "standard/longitude/apparent_solar"
            "のいずれかで指定してください。"
        )

    return normalized


def _validate_longitude(
    longitude: float,
) -> float:
    if isinstance(
        longitude,
        bool,
    ):
        raise TypeError(
            "longitudeは数値で指定してください。"
        )

    if not isinstance(
        longitude,
        (int, float),
    ):
        raise TypeError(
            "longitudeは数値で指定してください。"
        )

    value = float(
        longitude
    )

    if not (
        -180.0
        <= value
        <= 180.0
    ):
        raise ValueError(
            "longitudeは-180以上180以下で指定してください。"
        )

    return value


def _validate_latitude(
    latitude: float,
) -> float:
    if isinstance(
        latitude,
        bool,
    ):
        raise TypeError(
            "latitudeは数値で指定してください。"
        )

    if not isinstance(
        latitude,
        (int, float),
    ):
        raise TypeError(
            "latitudeは数値で指定してください。"
        )

    value = float(
        latitude
    )

    if not (
        -90.0
        <= value
        <= 90.0
    ):
        raise ValueError(
            "latitudeは-90以上90以下で指定してください。"
        )

    return value


def _validate_standard_meridian(
    value: float,
) -> float:
    return _validate_longitude(
        value
    )


def _normalize_birth_place(
    birth_place: str | None,
) -> str | None:
    if birth_place is None:
        return None

    if not isinstance(
        birth_place,
        str,
    ):
        raise TypeError(
            "birth_placeは文字列で指定してください。"
        )

    value = birth_place.strip()

    if not value:
        return None

    return value


# ============================================================
# Place master
# ============================================================


def get_place_coordinates(
    birth_place: str,
) -> dict[str, float]:
    """
    都道府県代表座標を返す。

    v1では完全一致のみ対応する。
    """

    normalized = (
        _normalize_birth_place(
            birth_place
        )
    )

    if normalized is None:
        raise ValueError(
            "birth_placeを指定してください。"
        )

    coordinates = (
        PLACE_COORDINATES.get(
            normalized
        )
    )

    if coordinates is None:
        raise ValueError(
            "birth_placeから座標を解決できません。 "
            "v1では都道府県名を指定するか、"
            "longitudeを直接指定してください。"
        )

    return deepcopy(
        coordinates
    )


def get_place_longitude(
    birth_place: str,
) -> float:
    return float(
        get_place_coordinates(
            birth_place
        )[
            "longitude"
        ]
    )


def get_place_latitude(
    birth_place: str,
) -> float:
    return float(
        get_place_coordinates(
            birth_place
        )[
            "latitude"
        ]
    )


# ============================================================
# Longitude correction
# ============================================================


def calculate_longitude_offset_minutes(
    longitude: float,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
) -> float:
    """
    経度差による時刻補正量を分で返す。

    Formula
    -------
    (longitude - standard_meridian) * 4

    東側:
        正の補正

    西側:
        負の補正
    """

    longitude = (
        _validate_longitude(
            longitude
        )
    )

    standard_meridian = (
        _validate_standard_meridian(
            standard_meridian
        )
    )

    return (
        (
            longitude
            - standard_meridian
        )
        * 4.0
    )


def calculate_longitude_offset_seconds(
    longitude: float,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
) -> float:
    """
    経度補正量を秒で返す。
    """

    return (
        calculate_longitude_offset_minutes(
            longitude,
            standard_meridian,
        )
        * 60.0
    )


# ============================================================
# Equation of time
# ============================================================


def calculate_equation_of_time_minutes(
    target_datetime: datetime,
) -> float:
    """
    均時差を分で返す。

    v1では未実装。

    apparent_solarモードは
    将来版で正式対応する。
    """

    _validate_datetime(
        target_datetime
    )

    raise NotImplementedError(
        "均時差計算はtime_correction_v1では未実装です。"
    )


# ============================================================
# Coordinate resolution
# ============================================================


def resolve_coordinates(
    *,
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """
    補正に利用する座標を解決する。

    優先順位
    --------
    1. 明示指定longitude
    2. birth_place内部マスタ

    latitudeは任意。
    longitude直接指定時にlatitudeが無くてもよい。
    """

    normalized_place = (
        _normalize_birth_place(
            birth_place
        )
    )

    resolved_latitude: (
        float | None
    ) = None

    resolved_longitude: (
        float | None
    ) = None

    source = "none"

    if latitude is not None:
        resolved_latitude = (
            _validate_latitude(
                latitude
            )
        )

    if longitude is not None:
        resolved_longitude = (
            _validate_longitude(
                longitude
            )
        )

        source = (
            "explicit_coordinates"
        )

        if (
            resolved_latitude
            is None
            and normalized_place
            in PLACE_COORDINATES
        ):
            resolved_latitude = float(
                PLACE_COORDINATES[
                    normalized_place
                ][
                    "latitude"
                ]
            )

        return {
            "birth_place": (
                normalized_place
            ),
            "latitude": (
                resolved_latitude
            ),
            "longitude": (
                resolved_longitude
            ),
            "source": source,
        }

    if normalized_place is not None:
        coordinates = (
            get_place_coordinates(
                normalized_place
            )
        )

        resolved_longitude = float(
            coordinates[
                "longitude"
            ]
        )

        if resolved_latitude is None:
            resolved_latitude = float(
                coordinates[
                    "latitude"
                ]
            )

        source = (
            "internal_place_master"
        )

    return {
        "birth_place": (
            normalized_place
        ),
        "latitude": (
            resolved_latitude
        ),
        "longitude": (
            resolved_longitude
        ),
        "source": source,
    }


# ============================================================
# Main correction
# ============================================================


def apply_time_correction(
    birth_datetime: datetime,
    *,
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    mode: str = MODE_STANDARD,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
) -> TimeCorrectionResult:
    """
    出生日時へ時刻補正を適用する。

    Parameters
    ----------
    birth_datetime:
        入力出生日時。

    birth_place:
        出生地。
        v1では都道府県代表座標に対応。

    latitude:
        緯度直接指定。
        v1の経度補正では必須ではない。

    longitude:
        経度直接指定。
        birth_placeより優先する。

    mode:
        standard
        longitude
        apparent_solar

    standard_meridian:
        標準時基準経度。
        日本標準時は135度。

    Returns
    -------
    TimeCorrectionResult

    Notes
    -----
    apparent_solarはv1では未実装。
    """

    _validate_datetime(
        birth_datetime
    )

    mode = _validate_mode(
        mode
    )

    standard_meridian = (
        _validate_standard_meridian(
            standard_meridian
        )
    )

    normalized_place = (
        _normalize_birth_place(
            birth_place
        )
    )

    original_datetime = (
        birth_datetime
    )

    if mode == MODE_STANDARD:
        corrected_datetime = (
            original_datetime
        )

        resolved_latitude = (
            _validate_latitude(
                latitude
            )
            if latitude is not None
            else None
        )

        resolved_longitude = (
            _validate_longitude(
                longitude
            )
            if longitude is not None
            else None
        )

        source = "standard"

        return (
            _build_result(
                original_datetime=(
                    original_datetime
                ),
                corrected_datetime=(
                    corrected_datetime
                ),
                mode=mode,
                birth_place=(
                    normalized_place
                ),
                latitude=(
                    resolved_latitude
                ),
                longitude=(
                    resolved_longitude
                ),
                standard_meridian=(
                    standard_meridian
                ),
                longitude_offset_minutes=(
                    0.0
                ),
                equation_of_time_minutes=(
                    0.0
                ),
                source=source,
            )
        )

    if mode == MODE_APPARENT_SOLAR:
        raise NotImplementedError(
            "apparent_solarは"
            "time_correction_v1では未実装です。"
        )

    resolved = resolve_coordinates(
        birth_place=(
            normalized_place
        ),
        latitude=latitude,
        longitude=longitude,
    )

    resolved_longitude = (
        resolved[
            "longitude"
        ]
    )

    if resolved_longitude is None:
        raise ValueError(
            "longitude補正には経度が必要です。 "
            "birth_placeまたはlongitudeを指定してください。"
        )

    longitude_offset_minutes = (
        calculate_longitude_offset_minutes(
            resolved_longitude,
            standard_meridian,
        )
    )

    equation_of_time_minutes = (
        0.0
    )

    total_offset_minutes = (
        longitude_offset_minutes
        + equation_of_time_minutes
    )

    corrected_datetime = (
        original_datetime
        + timedelta(
            minutes=(
                total_offset_minutes
            )
        )
    )

    return _build_result(
        original_datetime=(
            original_datetime
        ),
        corrected_datetime=(
            corrected_datetime
        ),
        mode=mode,
        birth_place=(
            resolved[
                "birth_place"
            ]
        ),
        latitude=(
            resolved[
                "latitude"
            ]
        ),
        longitude=(
            resolved_longitude
        ),
        standard_meridian=(
            standard_meridian
        ),
        longitude_offset_minutes=(
            longitude_offset_minutes
        ),
        equation_of_time_minutes=(
            equation_of_time_minutes
        ),
        source=(
            resolved[
                "source"
            ]
        ),
    )


# ============================================================
# Result builder
# ============================================================


def _build_result(
    *,
    original_datetime: datetime,
    corrected_datetime: datetime,
    mode: str,
    birth_place: str | None,
    latitude: float | None,
    longitude: float | None,
    standard_meridian: float,
    longitude_offset_minutes: float,
    equation_of_time_minutes: float,
    source: str,
) -> TimeCorrectionResult:
    total_offset_minutes = (
        longitude_offset_minutes
        + equation_of_time_minutes
    )

    return TimeCorrectionResult(
        original_datetime=(
            original_datetime
        ),
        corrected_datetime=(
            corrected_datetime
        ),
        mode=mode,
        birth_place=(
            birth_place
        ),
        latitude=(
            latitude
        ),
        longitude=(
            longitude
        ),
        standard_meridian=(
            standard_meridian
        ),
        longitude_offset_minutes=(
            float(
                longitude_offset_minutes
            )
        ),
        equation_of_time_minutes=(
            float(
                equation_of_time_minutes
            )
        ),
        total_offset_minutes=(
            float(
                total_offset_minutes
            )
        ),
        date_changed=(
            original_datetime.date()
            != corrected_datetime.date()
        ),
        year_changed=(
            original_datetime.year
            != corrected_datetime.year
        ),
        month_changed=(
            (
                original_datetime.year,
                original_datetime.month,
            )
            != (
                corrected_datetime.year,
                corrected_datetime.month,
            )
        ),
        day_changed=(
            original_datetime.date()
            != corrected_datetime.date()
        ),
        source=source,
        method=(
            TIME_CORRECTION_METHOD
        ),
        status=(
            TIME_CORRECTION_STATUS
        ),
    )


# ============================================================
# Convenience APIs
# ============================================================


def get_corrected_datetime(
    birth_datetime: datetime,
    *,
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    mode: str = MODE_STANDARD,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
) -> datetime:
    """
    補正後datetimeだけを返す。
    """

    return apply_time_correction(
        birth_datetime,
        birth_place=birth_place,
        latitude=latitude,
        longitude=longitude,
        mode=mode,
        standard_meridian=(
            standard_meridian
        ),
    ).corrected_datetime


def get_time_correction_dict(
    birth_datetime: datetime,
    *,
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    mode: str = MODE_STANDARD,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
    serialize_datetime: bool = True,
) -> dict[str, Any]:
    """
    APIレスポンス向けdictを返す。
    """

    return (
        apply_time_correction(
            birth_datetime,
            birth_place=birth_place,
            latitude=latitude,
            longitude=longitude,
            mode=mode,
            standard_meridian=(
                standard_meridian
            ),
        )
        .to_dict(
            serialize_datetime=(
                serialize_datetime
            )
        )
    )


# ============================================================
# Metadata
# ============================================================


def get_time_correction_metadata() -> dict[str, Any]:
    """
    時刻補正エンジンの計算方式を返す。
    """

    return {
        "version": (
            TIME_CORRECTION_VERSION
        ),
        "method": (
            TIME_CORRECTION_METHOD
        ),
        "status": (
            TIME_CORRECTION_STATUS
        ),
        "default_mode": (
            MODE_STANDARD
        ),
        "supported_modes": list(
            SUPPORTED_TIME_CORRECTION_MODES
        ),
        "implemented_modes": list(
            IMPLEMENTED_TIME_CORRECTION_MODES
        ),
        "standard_meridian": (
            STANDARD_MERIDIAN
        ),
        "longitude_minutes_per_degree": (
            4.0
        ),
        "place_master_count": len(
            PLACE_COORDINATES
        ),
        "external_geocoding": False,
        "equation_of_time": False,
        "apparent_solar": False,
    }


# ============================================================
# Compatibility / serialization helper
# ============================================================


def normalize_time_correction_result(
    value: (
        TimeCorrectionResult
        | Mapping[str, Any]
    ),
    *,
    serialize_datetime: bool = False,
) -> dict[str, Any]:
    """
    TimeCorrectionResultまたはdictを
    標準dictへ変換する。
    """

    if isinstance(
        value,
        TimeCorrectionResult,
    ):
        return value.to_dict(
            serialize_datetime=(
                serialize_datetime
            )
        )

    if isinstance(
        value,
        Mapping,
    ):
        result = deepcopy(
            dict(
                value
            )
        )

        if serialize_datetime:
            for key in (
                "original_datetime",
                "corrected_datetime",
            ):
                item = result.get(
                    key
                )

                if isinstance(
                    item,
                    datetime,
                ):
                    result[
                        key
                    ] = item.isoformat()

        return result

    raise TypeError(
        "valueはTimeCorrectionResultまたはdictで指定してください。"
    )


# ============================================================
# Public API
# ============================================================


__all__ = [
    "TIME_CORRECTION_VERSION",
    "TIME_CORRECTION_METHOD",
    "TIME_CORRECTION_STATUS",
    "STANDARD_MERIDIAN",
    "MODE_STANDARD",
    "MODE_LONGITUDE",
    "MODE_APPARENT_SOLAR",
    "SUPPORTED_TIME_CORRECTION_MODES",
    "IMPLEMENTED_TIME_CORRECTION_MODES",
    "PLACE_COORDINATES",
    "TimeCorrectionResult",
    "get_place_coordinates",
    "get_place_longitude",
    "get_place_latitude",
    "calculate_longitude_offset_minutes",
    "calculate_longitude_offset_seconds",
    "calculate_equation_of_time_minutes",
    "resolve_coordinates",
    "apply_time_correction",
    "get_corrected_datetime",
    "get_time_correction_dict",
    "get_time_correction_metadata",
    "normalize_time_correction_result",
]
