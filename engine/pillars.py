"""
engine/pillars.py

四柱（年柱・月柱・日柱・時柱）を統合して計算するモジュール。

設計方針
--------
- 年柱・月柱・日柱・時柱の既存計算エンジンを統合する。
- 蔵干・通変星・十二運を柱データへ付加する。
- 日主は日柱天干を基準とする。
- solar_time_mode による時刻補正へ対応する。
- 時刻補正後は時柱だけでなく四柱すべてを再計算する。
- calculation_rules / calculation_status を公開する。
- 既存 API・chart.py・テストとの後方互換性を維持する。

重要
----
calculation_status は calculation_rules["status"] とは別に
トップレベルにも保持する。

これは engine/chart.py が

    pillars["calculation_status"]

を直接参照するためである。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


from engine.year import calculate_year_pillar
from engine.month import calculate_month_pillar
from engine.day import calculate_day_pillar
from engine.hour import calculate_hour_pillar

from engine.hidden_stems import get_hidden_stems
from engine.ten_gods import get_ten_god
from engine.twelve_stages import get_twelve_stage


# ============================================================
# Time correction
# ============================================================

try:
    from engine.time_correction import (
        STANDARD_MERIDIAN,
        calculate_time_correction,
    )
except ImportError:
    # 既存環境との互換性確保
    STANDARD_MERIDIAN = 135.0
    calculate_time_correction = None


# ============================================================
# Version / metadata
# ============================================================

PILLARS_VERSION = "2.1"

PILLARS_METHOD = "astronomical_four_pillars"

PILLARS_STATUS = "verified"


# ============================================================
# Internal helpers
# ============================================================


def _extract_stem_branch(
    pillar: Any,
) -> tuple[str, str]:
    """
    年柱・月柱・日柱・時柱計算関数の戻り値から
    天干・地支を取得する。

    対応形式
    --------
    dict:
        {
            "stem": "甲",
            "branch": "子",
        }

    dict:
        {
            "heavenly_stem": "甲",
            "earthly_branch": "子",
        }

    tuple/list:
        ("甲", "子")

    string:
        "甲子"
    """

    if isinstance(pillar, dict):

        stem = (
            pillar.get("stem")
            or pillar.get("heavenly_stem")
        )

        branch = (
            pillar.get("branch")
            or pillar.get("earthly_branch")
        )

        if stem and branch:
            return str(stem), str(branch)

        ganzhi = (
            pillar.get("pillar")
            or pillar.get("ganzhi")
        )

        if (
            isinstance(ganzhi, str)
            and len(ganzhi) >= 2
        ):
            return ganzhi[0], ganzhi[1]

    if isinstance(pillar, (tuple, list)):

        if len(pillar) >= 2:
            return str(pillar[0]), str(pillar[1])

    if isinstance(pillar, str):

        if len(pillar) >= 2:
            return pillar[0], pillar[1]

    raise ValueError(
        f"Unsupported pillar format: {pillar!r}"
    )


def _extract_hidden_stem_name(
    value: Any,
) -> Optional[str]:
    """
    蔵干データから干名だけを取り出す。
    """

    if isinstance(value, str):
        return value

    if isinstance(value, dict):

        return (
            value.get("stem")
            or value.get("heavenly_stem")
            or value.get("name")
        )

    return None


def _extract_main_hidden_stem(
    hidden_stems: Any,
) -> Optional[str]:
    """
    蔵干データから本気（主蔵干）を取得する。

    hidden_stems.py の戻り値形式が多少変化しても
    pillars.py 側で吸収できるようにする。
    """

    if hidden_stems is None:
        return None

    if isinstance(hidden_stems, dict):

        # 明示的な主蔵干
        for key in (
            "main_hidden_stem",
            "main",
            "principal",
            "primary",
        ):
            if key in hidden_stems:

                result = _extract_hidden_stem_name(
                    hidden_stems[key]
                )

                if result:
                    return result

        # 一般的な蔵干順
        for key in (
            "main_qi",
            "middle_qi",
            "residual_qi",
        ):
            if key in hidden_stems:

                result = _extract_hidden_stem_name(
                    hidden_stems[key]
                )

                if result:
                    return result

        # dict の最初の有効値
        for value in hidden_stems.values():

            result = _extract_hidden_stem_name(
                value
            )

            if result:
                return result

    if isinstance(hidden_stems, (list, tuple)):

        if not hidden_stems:
            return None

        # weight がある場合は最大値を本気とする
        weighted = []

        for item in hidden_stems:

            if isinstance(item, dict):

                stem = _extract_hidden_stem_name(
                    item
                )

                weight = item.get("weight")

                if stem and isinstance(
                    weight,
                    (int, float),
                ):
                    weighted.append(
                        (weight, stem)
                    )

        if weighted:

            weighted.sort(
                reverse=True
            )

            return weighted[0][1]

        # weight がなければ先頭
        return _extract_hidden_stem_name(
            hidden_stems[0]
        )

    if isinstance(hidden_stems, str):
        return hidden_stems

    return None


# ============================================================
# Pillar data builder
# ============================================================


def build_pillar_data(
    stem: str,
    branch: str,
    day_stem: str,
    *,
    is_day_pillar: bool = False,
) -> Dict[str, Any]:
    """
    1柱分の詳細データを生成する。

    Parameters
    ----------
    stem:
        柱の天干。

    branch:
        柱の地支。

    day_stem:
        日主。

    is_day_pillar:
        日柱の場合 True。

    Returns
    -------
    dict
        {
            "stem": ...,
            "branch": ...,
            "pillar": ...,
            "hidden_stems": ...,
            "main_hidden_stem": ...,
            "ten_god": ...,
            "main_hidden_stem_ten_god": ...,
            "twelve_stage": ...
        }
    """

    hidden_stems = get_hidden_stems(
        branch
    )

    main_hidden_stem = (
        _extract_main_hidden_stem(
            hidden_stems
        )
    )

    # --------------------------------------------------------
    # 天干通変星
    #
    # 日柱天干は日主自身なので None とする。
    # --------------------------------------------------------

    if is_day_pillar:

        ten_god = None

    else:

        ten_god = get_ten_god(
            day_stem,
            stem,
        )

    # --------------------------------------------------------
    # 蔵干通変星
    # --------------------------------------------------------

    if main_hidden_stem is None:

        main_hidden_stem_ten_god = None

    else:

        main_hidden_stem_ten_god = (
            get_ten_god(
                day_stem,
                main_hidden_stem,
            )
        )

    # --------------------------------------------------------
    # 十二運
    # --------------------------------------------------------

    twelve_stage = get_twelve_stage(
        day_stem,
        branch,
    )

    return {
        "stem": stem,
        "branch": branch,
        "pillar": f"{stem}{branch}",
        "hidden_stems": hidden_stems,
        "main_hidden_stem": (
            main_hidden_stem
        ),
        "ten_god": ten_god,
        "main_hidden_stem_ten_god": (
            main_hidden_stem_ten_god
        ),
        "twelve_stage": twelve_stage,
    }


# ============================================================
# Time correction helpers
# ============================================================


def _identity_time_correction(
    birth_datetime: datetime,
    solar_time_mode: str,
    birth_place: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    standard_meridian: float,
) -> Dict[str, Any]:
    """
    time_correction モジュールが使用できない場合、
    または standard モードの場合に使用する
    後方互換用の補正情報。
    """

    return {
        "mode": solar_time_mode,
        "applied": False,
        "original_datetime": (
            birth_datetime.isoformat()
        ),
        "corrected_datetime": (
            birth_datetime.isoformat()
        ),
        "birth_place": birth_place,
        "latitude": latitude,
        "longitude": longitude,
        "standard_meridian": (
            standard_meridian
        ),
        "correction_minutes": 0.0,
        "true_solar_time": False,
    }


def _normalize_time_correction(
    correction: Any,
    birth_datetime: datetime,
    solar_time_mode: str,
    birth_place: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    standard_meridian: float,
) -> tuple[datetime, Dict[str, Any]]:
    """
    time_correction の戻り値を正規化する。

    corrected_datetime と API 出力用 metadata を返す。
    """

    if correction is None:

        metadata = (
            _identity_time_correction(
                birth_datetime,
                solar_time_mode,
                birth_place,
                latitude,
                longitude,
                standard_meridian,
            )
        )

        return birth_datetime, metadata

    # --------------------------------------------------------
    # dataclass / object
    # --------------------------------------------------------

    if hasattr(
        correction,
        "corrected_datetime",
    ):

        corrected_datetime = (
            correction.corrected_datetime
        )

        metadata = {}

        if hasattr(
            correction,
            "__dict__",
        ):
            metadata.update(
                correction.__dict__
            )

    # --------------------------------------------------------
    # dict
    # --------------------------------------------------------

    elif isinstance(
        correction,
        dict,
    ):

        corrected_datetime = (
            correction.get(
                "corrected_datetime",
                birth_datetime,
            )
        )

        metadata = dict(
            correction
        )

    # --------------------------------------------------------
    # datetime
    # --------------------------------------------------------

    elif isinstance(
        correction,
        datetime,
    ):

        corrected_datetime = correction

        metadata = {}

    else:

        corrected_datetime = (
            birth_datetime
        )

        metadata = {}

    # ISO string → datetime
    if isinstance(
        corrected_datetime,
        str,
    ):

        corrected_datetime = (
            datetime.fromisoformat(
                corrected_datetime
            )
        )

    metadata.setdefault(
        "mode",
        solar_time_mode,
    )

    metadata.setdefault(
        "applied",
        corrected_datetime
        != birth_datetime,
    )

    metadata.setdefault(
        "birth_place",
        birth_place,
    )

    metadata.setdefault(
        "latitude",
        latitude,
    )

    metadata.setdefault(
        "longitude",
        longitude,
    )

    metadata.setdefault(
        "standard_meridian",
        standard_meridian,
    )

    metadata.setdefault(
        "true_solar_time",
        False,
    )

    metadata[
        "original_datetime"
    ] = birth_datetime.isoformat()

    metadata[
        "corrected_datetime"
    ] = corrected_datetime.isoformat()

    return (
        corrected_datetime,
        metadata,
    )


def _calculate_corrected_datetime(
    birth_datetime: datetime,
    *,
    solar_time_mode: str,
    birth_place: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    standard_meridian: float,
) -> tuple[datetime, Dict[str, Any]]:
    """
    入力日時に必要な時刻補正を適用する。
    """

    # --------------------------------------------------------
    # standard
    #
    # 従来動作を完全維持する。
    # --------------------------------------------------------

    if solar_time_mode == "standard":

        metadata = (
            _identity_time_correction(
                birth_datetime,
                solar_time_mode,
                birth_place,
                latitude,
                longitude,
                standard_meridian,
            )
        )

        return (
            birth_datetime,
            metadata,
        )

    if calculate_time_correction is None:

        raise RuntimeError(
            "solar_time_mode requires "
            "engine.time_correction"
        )

    # --------------------------------------------------------
    # 現在の time_correction API を呼び出す。
    #
    # 実装差異を吸収するため、
    # TypeError の場合は段階的に呼び出しを簡略化する。
    # --------------------------------------------------------

    try:

        correction = (
            calculate_time_correction(
                birth_datetime,
                solar_time_mode=(
                    solar_time_mode
                ),
                birth_place=(
                    birth_place
                ),
                latitude=latitude,
                longitude=longitude,
                standard_meridian=(
                    standard_meridian
                ),
            )
        )

    except TypeError:

        try:

            correction = (
                calculate_time_correction(
                    birth_datetime,
                    mode=solar_time_mode,
                    birth_place=(
                        birth_place
                    ),
                    latitude=latitude,
                    longitude=longitude,
                    standard_meridian=(
                        standard_meridian
                    ),
                )
            )

        except TypeError:

            correction = (
                calculate_time_correction(
                    birth_datetime,
                    longitude=longitude,
                    standard_meridian=(
                        standard_meridian
                    ),
                )
            )

    return _normalize_time_correction(
        correction,
        birth_datetime,
        solar_time_mode,
        birth_place,
        latitude,
        longitude,
        standard_meridian,
    )


# ============================================================
# Warning builder
# ============================================================


def _build_time_correction_warnings(
    original_datetime: datetime,
    calculation_datetime: datetime,
    correction: Dict[str, Any],
) -> list[str]:
    """
    時刻補正によって日付・月・年を跨いだ場合の警告を作る。
    """

    warnings: list[str] = []

    if not correction.get(
        "applied",
        False,
    ):
        return warnings

    if (
        original_datetime.date()
        != calculation_datetime.date()
    ):

        warnings.append(
            "Time correction crossed a date "
            "boundary; all four pillars were "
            "recalculated using the corrected "
            "datetime."
        )

    if (
        original_datetime.month
        != calculation_datetime.month
        or
        original_datetime.year
        != calculation_datetime.year
    ):

        warnings.append(
            "Time correction crossed a "
            "calendar month/year boundary; "
            "year and month pillars were "
            "re-evaluated using the corrected "
            "datetime."
        )

    return warnings


# ============================================================
# Four pillars
# ============================================================


def calculate_four_pillars(
    birth_datetime: datetime,
    *,
    solar_time_mode: str = "standard",
    birth_place: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
) -> Dict[str, Any]:
    """
    四柱を計算する。

    Parameters
    ----------
    birth_datetime:
        出生日時。

    solar_time_mode:
        時刻補正方式。

        "standard" の場合は従来仕様を維持する。

    birth_place:
        出生地。

    latitude:
        緯度。

    longitude:
        経度。

    standard_meridian:
        標準子午線。
        日本標準時は 135.0。

    Returns
    -------
    dict
        四柱・日主・時刻補正情報・計算規則・計算状態。
    """

    if not isinstance(
        birth_datetime,
        datetime,
    ):

        raise TypeError(
            "birth_datetime must be datetime"
        )

    # ========================================================
    # 1. 時刻補正
    # ========================================================

    (
        calculation_datetime,
        time_correction,
    ) = _calculate_corrected_datetime(
        birth_datetime,
        solar_time_mode=(
            solar_time_mode
        ),
        birth_place=birth_place,
        latitude=latitude,
        longitude=longitude,
        standard_meridian=(
            standard_meridian
        ),
    )

    # ========================================================
    # 2. 基本四柱
    #
    # 重要：
    # 補正後日時を四柱すべてに使用する。
    # ========================================================

    raw_year = calculate_year_pillar(
        calculation_datetime
    )

    raw_month = calculate_month_pillar(
        calculation_datetime
    )

    raw_day = calculate_day_pillar(
        calculation_datetime
    )

    day_stem, day_branch = (
        _extract_stem_branch(
            raw_day
        )
    )

    # 時柱は日干が必要な実装があるため、
    # 複数 API 形式を吸収する。

    try:

        raw_hour = (
            calculate_hour_pillar(
                calculation_datetime,
                day_stem,
            )
        )

    except TypeError:

        raw_hour = (
            calculate_hour_pillar(
                calculation_datetime
            )
        )

    year_stem, year_branch = (
        _extract_stem_branch(
            raw_year
        )
    )

    month_stem, month_branch = (
        _extract_stem_branch(
            raw_month
        )
    )

    hour_stem, hour_branch = (
        _extract_stem_branch(
            raw_hour
        )
    )

    # ========================================================
    # 3. 詳細柱データ
    # ========================================================

    year_data = build_pillar_data(
        year_stem,
        year_branch,
        day_stem,
    )

    month_data = build_pillar_data(
        month_stem,
        month_branch,
        day_stem,
    )

    day_data = build_pillar_data(
        day_stem,
        day_branch,
        day_stem,
        is_day_pillar=True,
    )

    hour_data = build_pillar_data(
        hour_stem,
        hour_branch,
        day_stem,
    )

    # ========================================================
    # 4. warnings
    # ========================================================

    warnings = (
        _build_time_correction_warnings(
            birth_datetime,
            calculation_datetime,
            time_correction,
        )
    )

    # ========================================================
    # 5. calculation_status
    #
    # ここが今回の重要修正。
    #
    # chart.py は
    #
    # pillars["calculation_status"]
    #
    # を直接読むためトップレベルに必須。
    # ========================================================

    calculation_status = (
        PILLARS_STATUS
    )

    # ========================================================
    # 6. calculation_rules
    # ========================================================

    calculation_rules = {

        "version": (
            PILLARS_VERSION
        ),

        "method": (
            PILLARS_METHOD
        ),

        "status": (
            calculation_status
        ),

        # -----------------------------------------------
        # 四柱境界規則
        # -----------------------------------------------

        "year_boundary": (
            "astronomical_lichun"
        ),

        "month_boundary": (
            "astronomical_12_sekki"
        ),

        "day_boundary": (
            "00:00"
        ),

        "hour_boundary": (
            "子刻23:00-00:59"
        ),

        # -----------------------------------------------
        # 時刻補正
        # -----------------------------------------------

        "solar_time_mode": (
            solar_time_mode
        ),

        "time_correction_applied": (
            bool(
                time_correction.get(
                    "applied",
                    False,
                )
            )
        ),

        "original_datetime": (
            birth_datetime.isoformat()
        ),

        "calculation_datetime": (
            calculation_datetime.isoformat()
        ),

        "standard_meridian": (
            standard_meridian
        ),

        # 現段階では真太陽時補正ではない
        "true_solar_time": False,
    }

    # ========================================================
    # 7. Result
    # ========================================================

    return {

        "year": year_data,

        "month": month_data,

        "day": day_data,

        "hour": hour_data,

        "day_master": (
            day_stem
        ),

        "time_correction": (
            time_correction
        ),

        "warnings": warnings,

        "calculation_rules": (
            calculation_rules
        ),

        # ----------------------------------------------------
        # 後方互換
        #
        # engine/chart.py が直接参照する。
        # 絶対に削除しない。
        # ----------------------------------------------------

        "calculation_status": (
            calculation_status
        ),
    }


# ============================================================
# Standard compatibility API
# ============================================================


def calculate_four_pillars_standard(
    birth_datetime: datetime,
) -> Dict[str, Any]:
    """
    従来の標準時方式で四柱を計算する。

    calculate_four_pillars(dt)

    と同じ結果を返す。
    """

    return calculate_four_pillars(
        birth_datetime,
        solar_time_mode="standard",
    )


# ============================================================
# Metadata
# ============================================================


def get_pillars_metadata() -> Dict[str, Any]:
    """
    四柱計算エンジンの metadata を返す。
    """

    return {

        "version": (
            PILLARS_VERSION
        ),

        "method": (
            PILLARS_METHOD
        ),

        "status": (
            PILLARS_STATUS
        ),

        "year_boundary": (
            "astronomical_lichun"
        ),

        "month_boundary": (
            "astronomical_12_sekki"
        ),

        "day_boundary": (
            "00:00"
        ),

        "hour_boundary": (
            "子刻23:00-00:59"
        ),

        "default_solar_time_mode": (
            "standard"
        ),

        "standard_meridian": (
            STANDARD_MERIDIAN
        ),

        "true_solar_time": False,
    }


# ============================================================
# Public exports
# ============================================================


__all__ = [

    "PILLARS_VERSION",

    "PILLARS_METHOD",

    "PILLARS_STATUS",

    "build_pillar_data",

    "calculate_four_pillars",

    "calculate_four_pillars_standard",

    "get_pillars_metadata",
]
