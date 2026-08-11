"""
engine/pillars.py

四柱推命 四柱計算統合エンジン v4

目的
----
出生日時から、

・年柱
・月柱
・日柱
・時柱
・日主

を一貫したルールで計算する。

v4では出生時刻補正エンジン
engine/time_correction.py を統合する。

設計原則
--------
・既存呼び出しとの後方互換を維持する。
・補正モードのデフォルトはstandard。
・standardでは従来と同じ出生日時を使う。
・longitudeでは経度補正後日時を使う。
・補正後日時は時柱だけではなく、
  年柱・月柱・日柱・時柱すべてへ適用する。
・日付を跨いだ場合は日柱と日主を再計算する。
・立春を跨いだ場合は年柱と月柱を再計算する。
・月の節入りを跨いだ場合は月柱を再計算する。
・23:00は時支だけ子へ切り替わり、
  日柱の日界は00:00とする。
・子刻は23:00〜00:59とする。

現行境界仕様
------------
年柱:
    実際の立春日時で切替。

月柱:
    実際の12節の節入り日時で切替。

日柱:
    00:00で切替。

時柱:
    子 23:00〜00:59
    丑 01:00〜02:59
    寅 03:00〜04:59
    ...
    亥 21:00〜22:59

出生時刻補正
------------
standard:
    補正なし。
    既存仕様と互換。

longitude:
    (出生地経度 - 標準時基準経度) × 4分

apparent_solar:
    time_correction_v1では未実装。

Version
-------
pillars_v4_time_correction
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from engine.day import (
    calculate_day_pillar,
)
from engine.ganzhi import (
    split_ganzhi,
)
from engine.hidden_stems import (
    get_hidden_stems,
)
from engine.hour import (
    calculate_hour_pillar,
)
from engine.month import (
    calculate_month_pillar,
)
from engine.ten_gods import (
    calculate_ten_god,
)
from engine.time_correction import (
    MODE_STANDARD,
    STANDARD_MERIDIAN,
    TimeCorrectionResult,
    apply_time_correction,
)
from engine.twelve_stages import (
    calculate_twelve_stage,
)
from engine.year import (
    calculate_year_pillar,
)


# ============================================================
# Constants
# ============================================================


PILLARS_VERSION = (
    "pillars_v4_time_correction"
)

PILLARS_METHOD = (
    "astronomical_boundaries_with_optional_"
    "time_correction_v4"
)

PILLARS_STATUS = (
    "time_correction_integrated"
)


# ============================================================
# Validation
# ============================================================


def _validate_birth_datetime(
    birth_datetime: datetime,
) -> None:
    """
    出生日時を検証する。
    """

    if not isinstance(
        birth_datetime,
        datetime,
    ):
        raise TypeError(
            "birth_datetimeはdatetime型で指定してください。"
        )


# ============================================================
# Pillar data helpers
# ============================================================


def _extract_stem_branch(
    pillar: str,
) -> tuple[str, str]:
    """
    干支文字列を天干・地支へ分解する。

    engine.ganzhi.split_ganzhi() は
    {"stem": "...", "branch": "..."} のdictを返すため、
    明示的に値を取り出してtupleへ変換する。
    """

    result = split_ganzhi(
        pillar
    )

    if not isinstance(
        result,
        dict,
    ):
        raise TypeError(
            "split_ganzhi()の戻り値がdictではありません。"
        )

    if (
        "stem"
        not in result
        or "branch"
        not in result
    ):
        raise ValueError(
            "split_ganzhi()の戻り値に"
            "stemまたはbranchがありません。"
        )

    stem = result[
        "stem"
    ]

    branch = result[
        "branch"
    ]

    if not isinstance(
        stem,
        str,
    ):
        raise TypeError(
            "stemは文字列である必要があります。"
        )

    if not isinstance(
        branch,
        str,
    ):
        raise TypeError(
            "branchは文字列である必要があります。"
        )

    return (
        stem,
        branch,
    )


def _get_main_hidden_stem(
    hidden_stems: list[str],
) -> str | None:
    """
    蔵干リストから主蔵干を取得する。

    現行 hidden_stems エンジンでは
    先頭要素を主蔵干として扱う。
    """

    if not hidden_stems:
        return None

    return hidden_stems[
        0
    ]


def build_pillar_data(
    pillar: str,
    day_stem: str,
    *,
    is_day_pillar: bool = False,
) -> dict[str, Any]:
    """
    干支文字列から柱データを作成する。

    既存下流モジュールとの互換性を維持するため、
    旧スキーマの正式キーを返す。

    Returns
    -------
    dict
        pillar
        ganzhi
        stem
        branch
        stem_ten_god
        ten_god
        hidden_stems
        main_hidden_stem
        main_hidden_stem_ten_god
        hidden_stem_ten_god
        hidden_stem_ten_gods
        twelve_stage
    """

    if not isinstance(
        pillar,
        str,
    ):
        raise TypeError(
            "pillarは文字列で指定してください。"
        )

    if not isinstance(
        day_stem,
        str,
    ):
        raise TypeError(
            "day_stemは文字列で指定してください。"
        )

    stem, branch = (
        _extract_stem_branch(
            pillar
        )
    )

    hidden_stems = list(
        get_hidden_stems(
            branch
        )
    )

    main_hidden_stem = (
        _get_main_hidden_stem(
            hidden_stems
        )
    )

    if is_day_pillar:
        stem_ten_god = None
    else:
        stem_ten_god = (
            calculate_ten_god(
                day_stem,
                stem,
            )
        )

    hidden_stem_ten_gods = [
        {
            "stem": hidden_stem,
            "ten_god": (
                calculate_ten_god(
                    day_stem,
                    hidden_stem,
                )
            ),
        }
        for hidden_stem
        in hidden_stems
    ]

    main_hidden_stem_ten_god = (
        calculate_ten_god(
            day_stem,
            main_hidden_stem,
        )
        if main_hidden_stem
        is not None
        else None
    )

    twelve_stage = (
        calculate_twelve_stage(
            day_stem,
            branch,
        )
    )

    return {
        "pillar": pillar,
        "ganzhi": pillar,
        "stem": stem,
        "branch": branch,
        "stem_ten_god": (
            stem_ten_god
        ),
        # 互換エイリアス
        "ten_god": (
            stem_ten_god
        ),
        "hidden_stems": (
            hidden_stems
        ),
        "main_hidden_stem": (
            main_hidden_stem
        ),
        "main_hidden_stem_ten_god": (
            main_hidden_stem_ten_god
        ),
        # 互換エイリアス
        "hidden_stem_ten_god": (
            main_hidden_stem_ten_god
        ),
        "hidden_stem_ten_gods": (
            hidden_stem_ten_gods
        ),
        "twelve_stage": (
            twelve_stage
        ),
    }


# ============================================================
# Raw four pillars
# ============================================================


def _calculate_raw_four_pillars(
    calculation_datetime: datetime,
) -> dict[str, Any]:
    """
    1つのdatetimeから四柱を計算する。

    ここへ渡すdatetimeは、
    standardなら元日時、
    longitudeなら補正後日時。

    この関数内では時刻補正を行わない。
    """

    _validate_birth_datetime(
        calculation_datetime
    )

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    year_pillar = (
        calculate_year_pillar(
            calculation_datetime
        )
    )

    year_stem = (
        year_pillar[
            0
        ]
    )

    # --------------------------------------------------------
    # Month
    # --------------------------------------------------------

    month_pillar = (
        calculate_month_pillar(
            calculation_datetime,
            year_stem,
        )
    )

    # --------------------------------------------------------
    # Day
    # --------------------------------------------------------

    # 現行仕様の日界は00:00。
    #
    # 23:00で翌日柱へ切り替えない。
    day_pillar = (
        calculate_day_pillar(
            calculation_datetime.date()
        )
    )

    day_stem = (
        day_pillar[
            0
        ]
    )

    # --------------------------------------------------------
    # Hour
    # --------------------------------------------------------

    # 現行hourエンジンでは
    # 子刻 = 23:00〜00:59。
    #
    # 時干は補正後の日干から必ず再計算する。
    hour_pillar = (
        calculate_hour_pillar(
            day_stem,
            calculation_datetime.hour,
        )
    )

    # --------------------------------------------------------
    # Structured pillar data
    # --------------------------------------------------------

    return {
        "year": build_pillar_data(
            year_pillar,
            day_stem,
        ),
        "month": build_pillar_data(
            month_pillar,
            day_stem,
        ),
        "day": build_pillar_data(
            day_pillar,
            day_stem,
            is_day_pillar=True,
        ),
        "hour": build_pillar_data(
            hour_pillar,
            day_stem,
        ),
        "day_master": {
            "stem": day_stem,
        },
    }


# ============================================================
# Time correction helpers
# ============================================================


def _build_time_correction_data(
    correction: TimeCorrectionResult,
) -> dict[str, Any]:
    """
    TimeCorrectionResultを
    API/JSONへ載せやすいdictへ変換する。

    datetimeはISO 8601文字列へ変換する。
    """

    return correction.to_dict(
        serialize_datetime=True
    )


def _build_time_correction_warnings(
    correction: TimeCorrectionResult,
) -> list[str]:
    """
    時刻補正に伴う重要な境界変更を警告として返す。

    standardでは空リスト。
    """

    warnings: list[str] = []

    if (
        correction.mode
        == MODE_STANDARD
    ):
        return warnings

    if correction.year_changed:
        warnings.append(
            "出生時刻補正により西暦年を跨ぎました。"
            "年柱・月柱・日柱・時柱は補正後日時から"
            "再計算されています。"
        )

    elif correction.month_changed:
        warnings.append(
            "出生時刻補正により暦月を跨ぎました。"
            "四柱は補正後日時から再計算されています。"
        )

    elif correction.date_changed:
        warnings.append(
            "出生時刻補正により日付を跨ぎました。"
            "日柱・日主・時柱を含め、"
            "四柱は補正後日時から再計算されています。"
        )

    return warnings


# ============================================================
# Main public calculation
# ============================================================


def calculate_four_pillars(
    birth_datetime: datetime,
    *,
    solar_time_mode: str = (
        MODE_STANDARD
    ),
    birth_place: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    standard_meridian: float = (
        STANDARD_MERIDIAN
    ),
) -> dict[str, Any]:
    """
    出生日時から四柱を計算する。

    Parameters
    ----------
    birth_datetime:
        出生日時。

    solar_time_mode:
        出生時刻補正モード。

        standard:
            補正なし。
            デフォルト。
            従来仕様と互換。

        longitude:
            経度差による地方平均太陽時補正。

        apparent_solar:
            将来対応予定。
            time_correction_v1では未実装。

    birth_place:
        出生地。
        longitudeモードでは、
        time_correction内部マスタから
        都道府県代表経度を解決できる。

    latitude:
        緯度直接指定。
        v1のlongitude補正では必須ではない。

    longitude:
        経度直接指定。
        birth_placeより優先される。

    standard_meridian:
        標準時基準経度。
        日本標準時は東経135度。

    Returns
    -------
    dict
        year
        month
        day
        hour
        day_master
        time_correction
        warnings
        calculation_rules

    Backward compatibility
    ----------------------
    calculate_four_pillars(
        birth_datetime
    )

    という従来呼び出しでは
    solar_time_mode="standard" が使われ、
    四柱そのものの計算結果は従来と同じになる。

    Important
    ---------
    longitude補正を使う場合、
    corrected_datetimeを時柱だけに使わない。

    年柱・月柱・日柱・時柱の
    全計算をcorrected_datetimeから行う。
    """

    _validate_birth_datetime(
        birth_datetime
    )

    # --------------------------------------------------------
    # Time correction
    # --------------------------------------------------------

    correction = apply_time_correction(
        birth_datetime,
        birth_place=birth_place,
        latitude=latitude,
        longitude=longitude,
        mode=solar_time_mode,
        standard_meridian=(
            standard_meridian
        ),
    )

    calculation_datetime = (
        correction.corrected_datetime
    )

    # --------------------------------------------------------
    # Four pillars
    # --------------------------------------------------------

    result = (
        _calculate_raw_four_pillars(
            calculation_datetime
        )
    )

    # --------------------------------------------------------
    # Correction metadata
    # --------------------------------------------------------

    result[
        "time_correction"
    ] = (
        _build_time_correction_data(
            correction
        )
    )

    result[
        "warnings"
    ] = (
        _build_time_correction_warnings(
            correction
        )
    )

    # --------------------------------------------------------
    # Calculation rules
    # --------------------------------------------------------

    result[
        "calculation_rules"
    ] = {
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
        "solar_time_mode": (
            correction.mode
        ),
        "time_correction_applied": (
            correction.mode
            != MODE_STANDARD
        ),
        "calculation_datetime": (
            calculation_datetime.isoformat()
        ),
        "original_datetime": (
            birth_datetime.isoformat()
        ),
        "standard_meridian": (
            standard_meridian
        ),
        "true_solar_time": False,
    }

    return result


# ============================================================
# Compatibility API
# ============================================================


def calculate_four_pillars_standard(
    birth_datetime: datetime,
) -> dict[str, Any]:
    """
    補正なしで四柱を計算する。

    明示的にstandardモードを使いたい
    呼び出し側向けの補助API。
    """

    return calculate_four_pillars(
        birth_datetime,
        solar_time_mode=(
            MODE_STANDARD
        ),
    )


# ============================================================
# Metadata
# ============================================================


def get_pillars_metadata() -> dict[str, Any]:
    """
    四柱統合エンジンの計算方式を返す。
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
        "default_solar_time_mode": (
            MODE_STANDARD
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
        "standard_meridian": (
            STANDARD_MERIDIAN
        ),
        "time_correction": True,
        "true_solar_time": False,
    }


# ============================================================
# Public API
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
