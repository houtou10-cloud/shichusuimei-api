from datetime import datetime
from zoneinfo import ZoneInfo

from engine.annual_luck import (
    calculate_annual_luck_for_datetime,
)
from engine.climate_useful_gods import (
     evaluate_climate_useful_gods,
)
from engine.current_luck import (
    evaluate_current_luck,
)
from engine.final_strength import (
    calculate_final_strength_judgment,
)
from engine.integrated_luck import (
    calculate_integrated_luck,
)
from engine.luck_pillars import (
    calculate_luck_pillars,
)
from engine.pattern import (
    calculate_pattern_candidates,
    calculate_pattern_judgment,
    calculate_pattern_special_rules,
)
from engine.pattern_useful_gods import (
    calculate_pattern_useful_gods,
)
from engine.pillars import (
    calculate_four_pillars,
)
from engine.strength import (
    calculate_strength,
)
from engine.useful_gods import (
    calculate_useful_gods,
)


JST = ZoneInfo("Asia/Tokyo")


def _normalize_target_datetime(
    target_datetime: datetime | None,
) -> datetime:
    """
    target_datetime を
    四柱推命エンジン内部で扱う
    JSTベースのnaive datetimeへ変換します。

    ルール
    ------
    None:
        現在の日本時間を使用。

    timezone-aware:
        JSTへ変換した後、
        tzinfoを除去。

    timezone-naive:
        そのまま使用。

    注意
    ----
    現在の四柱推命エンジンでは、
    timezone-naiveな日本標準時を
    基準として計算します。
    """

    if target_datetime is None:
        return datetime.now(
            JST
        ).replace(
            tzinfo=None
        )

    if not isinstance(
        target_datetime,
        datetime,
    ):
        raise TypeError(
            "target_datetimeはdatetime型で指定してください。"
        )

    if (
        target_datetime.tzinfo
        is not None
    ):
        return (
            target_datetime
            .astimezone(JST)
            .replace(
                tzinfo=None
            )
        )

    return target_datetime


def _normalize_birth_datetime_for_luck(
    birth_datetime: datetime,
) -> datetime:
    """
    大運・現在大運計算用に
    birth_datetime を
    timezone-naiveへ変換します。

    timezone-awareの場合は、
    入力されたローカル時刻を保持したまま
    tzinfoのみ除去します。

    これは四柱計算側の出生時刻と
    大運計算側の出生時刻を
    同じwall-clock timeとして扱うためです。
    """

    if not isinstance(
        birth_datetime,
        datetime,
    ):
        raise TypeError(
            "birth_datetimeはdatetime型で指定してください。"
        )

    if (
        birth_datetime.tzinfo
        is not None
    ):
        return birth_datetime.replace(
            tzinfo=None
        )

    return birth_datetime


def calculate_chart(
    birth_datetime: datetime,
    gender: str | None = None,
    target_datetime: datetime | None = None,
) -> dict:
    """
    四柱推命命式を総合計算します。

    現在の計算フロー
    ----------------

    1. 四柱
    2. 身強身弱
    3. 最終身強身弱判定
    4. 格局候補
    5. 格局特殊ルール
    6. 格局判定
    7. 調候用神
    8. 格局用神
    9. 総合用神 useful_gods_v3
    10. 大運 luck_pillars_v2
    11. 現在大運 current_luck_v1
    12. 歳運 annual_luck_v1
    13. 大運×歳運×用神統合
        integrated_luck_v1

    Parameters
    ----------
    birth_datetime:
        出生日時。

    gender:
        性別。
        大運の順逆判定に使用します。

    target_datetime:
        現在大運・歳運・統合運を
        評価する対象日時。

        Noneの場合は現在の日本時間を使用。

    Returns
    -------
    dict
        四柱推命の総合計算結果。
    """

    if not isinstance(
        birth_datetime,
        datetime,
    ):
        raise TypeError(
            "birth_datetimeはdatetime型で指定してください。"
        )

    # =====================================================
    # 1. 四柱
    # =====================================================

    pillars = calculate_four_pillars(
        birth_datetime
    )

    day_master_stem = (
        pillars[
            "day_master"
        ][
            "stem"
        ]
    )

    year_stem = (
        pillars[
            "year"
        ][
            "stem"
        ]
    )

    month_ganzhi = (
        pillars[
            "month"
        ][
            "pillar"
        ]
    )

    # =====================================================
    # 2. 身強身弱
    # =====================================================

    strength = calculate_strength(
        pillars
    )

    # =====================================================
    # 3. 最終身強身弱判定
    # =====================================================

    final_strength_judgment = (
        calculate_final_strength_judgment(
            pillars=pillars,
            strength=strength,
        )
    )

    # =====================================================
    # 4. 格局候補
    # =====================================================

    pattern_candidates = (
        calculate_pattern_candidates(
            pillars
        )
    )

    # =====================================================
    # 5. 格局特殊ルール
    # =====================================================

    pattern_special_rules = (
        calculate_pattern_special_rules(
            pillars=pillars,
            strength=(
                final_strength_judgment
            ),
            pattern_candidates=(
                pattern_candidates
            ),
        )
    )

    # =====================================================
    # 6. 格局判定
    # =====================================================

    pattern_judgment = (
        calculate_pattern_judgment(
            pillars=pillars,
            pattern_candidates=(
                pattern_candidates
            ),
            strength=(
                final_strength_judgment
            ),
            special_rules=(
                pattern_special_rules
            ),
        )
    )

    # =====================================================
    # 7. 調候用神
    # =====================================================

    climate_useful_gods = (
        calculate_climate_useful_gods(
            pillars
        )
    )

    # =====================================================
    # 8. 格局用神
    # =====================================================

    pattern_useful_gods = (
        calculate_pattern_useful_gods(
            pillars=pillars,
            pattern_judgment=(
                pattern_judgment
            ),
        )
    )

    # =====================================================
    # 9. 総合用神 useful_gods_v3
    # =====================================================

    useful_gods = (
        calculate_useful_gods(
            pillars=pillars,
            final_strength_judgment=(
                final_strength_judgment
            ),
            climate_useful_gods=(
                climate_useful_gods
            ),
            pattern_useful_gods=(
                pattern_useful_gods
            ),
            pattern_judgment=(
                pattern_judgment
            ),
        )
    )

    # =====================================================
    # 10. 大運
    # =====================================================

    luck_birth_datetime = (
        _normalize_birth_datetime_for_luck(
            birth_datetime
        )
    )

    luck_pillars = None

    if gender is not None:
        luck_pillars = (
            calculate_luck_pillars(
                year_stem=year_stem,
                month_ganzhi=month_ganzhi,
                day_master_stem=(
                    day_master_stem
                ),
                gender=gender,
                birth_datetime=(
                    luck_birth_datetime
                ),
                useful_gods=(
                    useful_gods
                ),
            )
        )

    # =====================================================
    # 11. target datetime
    # =====================================================

    current_target_datetime = (
        _normalize_target_datetime(
            target_datetime
        )
    )

    # =====================================================
    # 12. 現在大運
    # =====================================================

    current_luck = None

    if luck_pillars is not None:
        current_luck = (
            evaluate_current_luck(
                birth_datetime=(
                    luck_birth_datetime
                ),
                target_datetime=(
                    current_target_datetime
                ),
                luck_pillars=(
                    luck_pillars
                ),
            )
        )

    # =====================================================
    # 13. 歳運 annual_luck_v1
    # =====================================================

    annual_luck = (
        calculate_annual_luck_for_datetime(
            target_datetime=(
                current_target_datetime
            ),
            day_master_stem=(
                day_master_stem
            ),
            useful_gods=(
                useful_gods
            ),
            current_luck=(
                current_luck
            ),
        )
    )

    # =====================================================
    # 14. 統合運 integrated_luck_v1
    # =====================================================

    integrated_luck = None

    if current_luck is not None:
        integrated_luck = (
            calculate_integrated_luck(
                current_luck=(
                    current_luck
                ),
                annual_luck=(
                    annual_luck
                ),
                useful_gods=(
                    useful_gods
                ),
            )
        )

    # =====================================================
    # 15. 結果
    # =====================================================

    result = {
        **pillars,

        "strength": (
            strength
        ),

        "final_strength_judgment": (
            final_strength_judgment
        ),

        "pattern_candidates": (
            pattern_candidates
        ),

        "pattern_special_rules": (
            pattern_special_rules
        ),

        "pattern_judgment": (
            pattern_judgment
        ),

        "climate_useful_gods": (
            climate_useful_gods
        ),

        "pattern_useful_gods": (
            pattern_useful_gods
        ),

        "useful_gods": (
            useful_gods
        ),

        "luck_pillars": (
            luck_pillars
        ),

        "current_luck": (
            current_luck
        ),

        "annual_luck": (
            annual_luck
        ),

        "integrated_luck": (
            integrated_luck
        ),
    }

    return result


def build_chart(
    birth_datetime: datetime,
    gender: str | None = None,
    target_datetime: datetime | None = None,
) -> dict:
    """
    calculate_chart の互換alias。
    """

    return calculate_chart(
        birth_datetime=(
            birth_datetime
        ),
        gender=gender,
        target_datetime=(
            target_datetime
        ),
    )


def create_chart(
    birth_datetime: datetime,
    gender: str | None = None,
    target_datetime: datetime | None = None,
) -> dict:
    """
    calculate_chart の互換alias。
    """

    return calculate_chart(
        birth_datetime=(
            birth_datetime
        ),
        gender=gender,
        target_datetime=(
            target_datetime
        ),
    )
