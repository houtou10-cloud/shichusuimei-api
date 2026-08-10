"""
四柱推命 現在大運判定エンジン v1

luck_pillars_v2 が生成した大運一覧から、
指定日時時点で該当する大運を判定する。

主な機能
--------
1. 現在年齢の計算
2. 現在大運の特定
3. 前大運・次大運の特定
4. 大運開始まで／終了までの期間計算
5. 大運全体における進行率の計算
6. luck_pillars_v2 との整合性維持
7. 将来の歳運統合を考慮した構造化出力

Version:
    current_luck_v1
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional


# =========================================================
# Constants
# =========================================================


DAYS_PER_YEAR = 365.2425


SUPPORTED_LUCK_METHODS = {
    "luck_pillars_v1",
    "luck_pillars_v2",
}


# =========================================================
# Validation
# =========================================================


def _validate_datetime(
    value: datetime,
    name: str,
) -> None:
    """
    datetime 型を検証する。
    """

    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(
            f"{name} は datetime 型で指定してください。"
        )


def _validate_luck_pillars(
    luck_pillars: Dict[str, Any],
) -> None:
    """
    luck_pillars の基本構造を検証する。
    """

    if not isinstance(
        luck_pillars,
        dict,
    ):
        raise TypeError(
            "luck_pillars は dict 型で指定してください。"
        )

    if "pillars" not in luck_pillars:
        raise ValueError(
            "luck_pillars に pillars がありません。"
        )

    pillars = luck_pillars[
        "pillars"
    ]

    if not isinstance(
        pillars,
        list,
    ):
        raise TypeError(
            "luck_pillars['pillars'] は "
            "list 型である必要があります。"
        )

    if len(
        pillars
    ) == 0:
        raise ValueError(
            "luck_pillars['pillars'] が空です。"
        )

    for index, pillar in enumerate(
        pillars,
        start=1,
    ):
        if not isinstance(
            pillar,
            dict,
        ):
            raise TypeError(
                f"pillars[{index - 1}] は "
                "dict 型である必要があります。"
            )

        required_keys = {
            "index",
            "ganzhi",
            "stem",
            "branch",
            "start_age",
            "end_age",
        }

        missing_keys = (
            required_keys
            - set(
                pillar.keys()
            )
        )

        if missing_keys:
            raise ValueError(
                f"pillars[{index - 1}] に"
                f"必要なキーがありません: "
                f"{sorted(missing_keys)}"
            )


def _validate_age_range(
    start_age: float,
    end_age: float,
) -> None:
    """
    大運年齢範囲を検証する。
    """

    if not isinstance(
        start_age,
        (int, float),
    ):
        raise TypeError(
            "start_age は数値である必要があります。"
        )

    if isinstance(
        start_age,
        bool,
    ):
        raise TypeError(
            "start_age は数値である必要があります。"
        )

    if not isinstance(
        end_age,
        (int, float),
    ):
        raise TypeError(
            "end_age は数値である必要があります。"
        )

    if isinstance(
        end_age,
        bool,
    ):
        raise TypeError(
            "end_age は数値である必要があります。"
        )

    if start_age < 0:
        raise ValueError(
            "start_age は0以上である必要があります。"
        )

    if end_age <= start_age:
        raise ValueError(
            "end_age は start_age より"
            "大きい必要があります。"
        )


# =========================================================
# Datetime normalization
# =========================================================


def normalize_datetime_pair(
    first: datetime,
    second: datetime,
) -> tuple[
    datetime,
    datetime,
]:
    """
    datetime 同士を比較できる状態へ揃える。

    現在のプロジェクトでは、
    timezone-aware と timezone-naive が
    混在する可能性がある。

    片方だけ timezone-aware の場合は、
    壁時計時刻を維持したまま tzinfo を外す。

    注意
    ----
    これは現在の暫定仕様。

    将来、全エンジンを timezone-aware に
    統一した時点で再設計可能。
    """

    _validate_datetime(
        first,
        "first",
    )

    _validate_datetime(
        second,
        "second",
    )

    first_aware = (
        first.tzinfo is not None
        and first.utcoffset() is not None
    )

    second_aware = (
        second.tzinfo is not None
        and second.utcoffset() is not None
    )

    if (
        first_aware
        != second_aware
    ):
        return (
            first.replace(
                tzinfo=None
            ),
            second.replace(
                tzinfo=None
            ),
        )

    return (
        first,
        second,
    )


# =========================================================
# Age calculation
# =========================================================


def calculate_exact_age(
    birth_datetime: datetime,
    target_datetime: datetime,
) -> float:
    """
    出生日時から指定日時までの
    経過年数を小数年で返す。

    1年 = 365.2425日として計算する。

    Returns
    -------
    float
        小数年齢。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    birth, target = normalize_datetime_pair(
        birth_datetime,
        target_datetime,
    )

    if target < birth:
        raise ValueError(
            "target_datetime は birth_datetime "
            "以降である必要があります。"
        )

    seconds = (
        target
        - birth
    ).total_seconds()

    days = (
        seconds
        / 86400.0
    )

    age = (
        days
        / DAYS_PER_YEAR
    )

    return round(
        age,
        6,
    )


def calculate_calendar_age(
    birth_datetime: datetime,
    target_datetime: datetime,
) -> int:
    """
    満年齢を返す。

    小数年齢とは別に、
    人間向け表示で利用する。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    birth, target = normalize_datetime_pair(
        birth_datetime,
        target_datetime,
    )

    if target < birth:
        raise ValueError(
            "target_datetime は birth_datetime "
            "以降である必要があります。"
        )

    age = (
        target.year
        - birth.year
    )

    birthday_passed = (
        (
            target.month,
            target.day,
            target.hour,
            target.minute,
            target.second,
            target.microsecond,
        )
        >=
        (
            birth.month,
            birth.day,
            birth.hour,
            birth.minute,
            birth.second,
            birth.microsecond,
        )
    )

    if not birthday_passed:
        age -= 1

    return age


# =========================================================
# Pillar search
# =========================================================


def is_age_in_luck_pillar(
    age: float,
    pillar: Dict[str, Any],
) -> bool:
    """
    指定年齢が大運区間内か判定する。

    区間:
        start_age <= age < end_age

    終了年齢を排他的にすることで、
    大運切替点で二重判定しない。
    """

    if not isinstance(
        age,
        (int, float),
    ):
        raise TypeError(
            "age は数値である必要があります。"
        )

    if isinstance(
        age,
        bool,
    ):
        raise TypeError(
            "age は数値である必要があります。"
        )

    start_age = pillar[
        "start_age"
    ]

    end_age = pillar[
        "end_age"
    ]

    _validate_age_range(
        start_age,
        end_age,
    )

    return (
        start_age
        <= age
        < end_age
    )


def find_current_luck_index(
    age: float,
    pillars: List[
        Dict[str, Any]
    ],
) -> Optional[int]:
    """
    現在大運の list index を返す。

    該当しない場合は None。
    """

    if not isinstance(
        pillars,
        list,
    ):
        raise TypeError(
            "pillars は list 型で指定してください。"
        )

    for index, pillar in enumerate(
        pillars
    ):
        if is_age_in_luck_pillar(
            age,
            pillar,
        ):
            return index

    return None


def find_next_luck_index(
    age: float,
    pillars: List[
        Dict[str, Any]
    ],
) -> Optional[int]:
    """
    指定年齢より後に開始する
    最初の大運 index を返す。
    """

    if not isinstance(
        age,
        (int, float),
    ):
        raise TypeError(
            "age は数値である必要があります。"
        )

    if isinstance(
        age,
        bool,
    ):
        raise TypeError(
            "age は数値である必要があります。"
        )

    if not isinstance(
        pillars,
        list,
    ):
        raise TypeError(
            "pillars は list 型で指定してください。"
        )

    for index, pillar in enumerate(
        pillars
    ):
        start_age = pillar[
            "start_age"
        ]

        if start_age > age:
            return index

    return None


# =========================================================
# Pillar decoration
# =========================================================


def build_luck_pillar_view(
    pillar: Optional[
        Dict[str, Any]
    ],
    *,
    is_current: bool = False,
    is_previous: bool = False,
    is_next: bool = False,
) -> Optional[
    Dict[str, Any]
]:
    """
    大運データをコピーし、
    現在・前・次フラグを付加する。

    元の luck_pillars を変更しない。
    """

    if pillar is None:
        return None

    if not isinstance(
        pillar,
        dict,
    ):
        raise TypeError(
            "pillar は dict 型で指定してください。"
        )

    result = deepcopy(
        pillar
    )

    result[
        "is_current"
    ] = is_current

    result[
        "is_previous"
    ] = is_previous

    result[
        "is_next"
    ] = is_next

    return result


# =========================================================
# Progress
# =========================================================


def calculate_luck_progress(
    age: float,
    pillar: Dict[str, Any],
) -> Dict[str, Any]:
    """
    現在大運内の進行状況を計算する。
    """

    if not isinstance(
        age,
        (int, float),
    ):
        raise TypeError(
            "age は数値である必要があります。"
        )

    if isinstance(
        age,
        bool,
    ):
        raise TypeError(
            "age は数値である必要があります。"
        )

    if not isinstance(
        pillar,
        dict,
    ):
        raise TypeError(
            "pillar は dict 型で指定してください。"
        )

    start_age = float(
        pillar[
            "start_age"
        ]
    )

    end_age = float(
        pillar[
            "end_age"
        ]
    )

    _validate_age_range(
        start_age,
        end_age,
    )

    duration = (
        end_age
        - start_age
    )

    elapsed = (
        age
        - start_age
    )

    remaining = (
        end_age
        - age
    )

    progress = (
        elapsed
        / duration
    )

    progress = max(
        0.0,
        min(
            progress,
            1.0,
        ),
    )

    return {
        "start_age": round(
            start_age,
            6,
        ),
        "end_age": round(
            end_age,
            6,
        ),
        "duration_years": round(
            duration,
            6,
        ),
        "elapsed_years": round(
            max(
                elapsed,
                0.0,
            ),
            6,
        ),
        "remaining_years": round(
            max(
                remaining,
                0.0,
            ),
            6,
        ),
        "progress_ratio": round(
            progress,
            6,
        ),
        "progress_percent": round(
            progress
            * 100.0,
            2,
        ),
    }


# =========================================================
# Main evaluator
# =========================================================


def evaluate_current_luck(
    *,
    birth_datetime: datetime,
    target_datetime: datetime,
    luck_pillars: Dict[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    指定日時時点の大運を判定する。

    Parameters
    ----------
    birth_datetime:
        出生日時。

    target_datetime:
        判定したい日時。

        この関数内では datetime.now() を
        呼ばない。

        呼び出し側から対象日時を渡すことで、
        テスト再現性を維持する。

    luck_pillars:
        calculate_luck_pillars()
        の戻り値。

    Returns
    -------
    dict
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    _validate_luck_pillars(
        luck_pillars
    )

    exact_age = calculate_exact_age(
        birth_datetime,
        target_datetime,
    )

    calendar_age = (
        calculate_calendar_age(
            birth_datetime,
            target_datetime,
        )
    )

    pillars = luck_pillars[
        "pillars"
    ]

    current_index = (
        find_current_luck_index(
            exact_age,
            pillars,
        )
    )

    # -----------------------------------------------------
    # 現在大運が見つからない
    # -----------------------------------------------------

    if current_index is None:
        next_index = (
            find_next_luck_index(
                exact_age,
                pillars,
            )
        )

        # -------------------------------------------------
        # 起運前
        # -------------------------------------------------

        if next_index is not None:
            next_pillar = (
                build_luck_pillar_view(
                    pillars[
                        next_index
                    ],
                    is_next=True,
                )
            )

            years_until_start = (
                float(
                    pillars[
                        next_index
                    ][
                        "start_age"
                    ]
                )
                - exact_age
            )

            return {
                "has_current_luck": False,
                "phase": (
                    "before_first_luck"
                ),
                "exact_age": exact_age,
                "calendar_age": (
                    calendar_age
                ),
                "current_luck_pillar": None,
                "previous_luck_pillar": None,
                "next_luck_pillar": (
                    next_pillar
                ),
                "progress": None,
                "years_until_next_luck": round(
                    max(
                        years_until_start,
                        0.0,
                    ),
                    6,
                ),
                "method": (
                    "current_luck_v1"
                ),
                "status": (
                    "before_first_luck"
                ),
                "notes": [
                    (
                        "指定日時は第1大運の"
                        "開始前です。"
                    ),
                    (
                        "大運区間は"
                        "start_age <= age < end_age "
                        "として判定します。"
                    ),
                ],
            }

        # -------------------------------------------------
        # 登録済み大運終了後
        # -------------------------------------------------

        previous_pillar = (
            build_luck_pillar_view(
                pillars[-1],
                is_previous=True,
            )
        )

        return {
            "has_current_luck": False,
            "phase": (
                "after_last_luck"
            ),
            "exact_age": exact_age,
            "calendar_age": (
                calendar_age
            ),
            "current_luck_pillar": None,
            "previous_luck_pillar": (
                previous_pillar
            ),
            "next_luck_pillar": None,
            "progress": None,
            "years_until_next_luck": None,
            "method": (
                "current_luck_v1"
            ),
            "status": (
                "after_last_luck"
            ),
            "notes": [
                (
                    "指定日時は生成済みの"
                    "大運範囲を超えています。"
                ),
                (
                    "必要に応じて "
                    "calculate_luck_pillars() の "
                    "count を増やしてください。"
                ),
            ],
        }

    # -----------------------------------------------------
    # 現在大運あり
    # -----------------------------------------------------

    current_pillar = (
        build_luck_pillar_view(
            pillars[
                current_index
            ],
            is_current=True,
        )
    )

    previous_pillar = None

    if current_index > 0:
        previous_pillar = (
            build_luck_pillar_view(
                pillars[
                    current_index
                    - 1
                ],
                is_previous=True,
            )
        )

    next_pillar = None

    if (
        current_index
        + 1
        < len(
            pillars
        )
    ):
        next_pillar = (
            build_luck_pillar_view(
                pillars[
                    current_index
                    + 1
                ],
                is_next=True,
            )
        )

    progress = (
        calculate_luck_progress(
            exact_age,
            pillars[
                current_index
            ],
        )
    )

    years_until_next_luck = (
        progress[
            "remaining_years"
        ]
    )

    return {
        "has_current_luck": True,
        "phase": (
            "in_luck_pillar"
        ),
        "exact_age": exact_age,
        "calendar_age": (
            calendar_age
        ),
        "current_luck_pillar": (
            current_pillar
        ),
        "previous_luck_pillar": (
            previous_pillar
        ),
        "next_luck_pillar": (
            next_pillar
        ),
        "progress": progress,
        "years_until_next_luck": (
            years_until_next_luck
        ),
        "method": (
            "current_luck_v1"
        ),
        "status": (
            "current_luck_resolved"
        ),
        "notes": [
            (
                "現在大運は小数年齢を用いて"
                "判定しています。"
            ),
            (
                "大運区間は"
                "start_age <= age < end_age "
                "として判定します。"
            ),
            (
                "終了年齢を排他的にすることで、"
                "大運切替時の二重判定を防止します。"
            ),
        ],
    }


# =========================================================
# Convenience aliases
# =========================================================


def calculate_current_luck(
    *,
    birth_datetime: datetime,
    target_datetime: datetime,
    luck_pillars: Dict[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    evaluate_current_luck() の別名。
    """

    return evaluate_current_luck(
        birth_datetime=birth_datetime,
        target_datetime=target_datetime,
        luck_pillars=luck_pillars,
    )


def get_current_luck_pillar(
    *,
    birth_datetime: datetime,
    target_datetime: datetime,
    luck_pillars: Dict[
        str,
        Any,
    ],
) -> Optional[
    Dict[str, Any]
]:
    """
    現在大運だけを取得する
    簡易インターフェース。
    """

    result = (
        evaluate_current_luck(
            birth_datetime=(
                birth_datetime
            ),
            target_datetime=(
                target_datetime
            ),
            luck_pillars=(
                luck_pillars
            ),
        )
    )

    return result[
        "current_luck_pillar"
    ]


# =========================================================
# Public API
# =========================================================


__all__ = [
    "DAYS_PER_YEAR",
    "SUPPORTED_LUCK_METHODS",
    "normalize_datetime_pair",
    "calculate_exact_age",
    "calculate_calendar_age",
    "is_age_in_luck_pillar",
    "find_current_luck_index",
    "find_next_luck_index",
    "build_luck_pillar_view",
    "calculate_luck_progress",
    "evaluate_current_luck",
    "calculate_current_luck",
    "get_current_luck_pillar",
]
