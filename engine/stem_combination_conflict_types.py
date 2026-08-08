"""
天干五合の競合状態を、
より詳細な技術分類へ変換するモジュール。

このモジュールは、
stem_combination_conflicts.py が検出した
競合情報を受け取り、

- 争合候補
- 複合競合
- 重複干合候補
- 未分類競合

として暫定分類します。

重要:
古典上の「争合」「妬合」を
この段階で最終確定するものではありません。

v1では、
構造的に確認できる競合状態だけを
技術分類します。

将来的には、

- 陰陽
- 日主との関係
- 柱の位置
- 隣接性
- 月令
- 通根
- 透干
- 化神の勢力

などを追加して、
より厳密な争合・妬合判定へ拡張します。
"""


VALID_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


def validate_conflict_data(
    stem_combination_conflicts: dict,
) -> None:
    """
    stem_combination_conflicts の
    基本構造を検証します。
    """
    if not isinstance(
        stem_combination_conflicts,
        dict,
    ):
        raise TypeError(
            "stem_combination_conflictsは"
            "dict型で指定してください。"
        )

    position_conflicts = (
        stem_combination_conflicts.get(
            "position_conflicts",
            [],
        )
    )

    duplicate_combinations = (
        stem_combination_conflicts.get(
            "duplicate_combinations",
            [],
        )
    )

    if not isinstance(
        position_conflicts,
        list,
    ):
        raise TypeError(
            "position_conflictsは"
            "list型で指定してください。"
        )

    if not isinstance(
        duplicate_combinations,
        list,
    ):
        raise TypeError(
            "duplicate_combinationsは"
            "list型で指定してください。"
        )


def normalize_combination_names(
    combination_names: list,
) -> list[str]:
    """
    combination_namesから
    Noneを除外し、
    文字列だけを返します。
    """
    if not isinstance(
        combination_names,
        list,
    ):
        raise TypeError(
            "combination_namesは"
            "list型で指定してください。"
        )

    result: list[str] = []

    for name in combination_names:
        if name is None:
            continue

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "combination_nameは"
                "str型で指定してください。"
            )

        result.append(
            name
        )

    return result


def classify_position_conflict(
    conflict: dict,
) -> dict:
    """
    position_conflictを
    技術分類します。

    v1の基本ルール:

    1.
    同一positionが、
    同じcombination_nameの
    複数候補に参加している

    -> 争合候補
    -> competing_same_combination

    2.
    同一positionが、
    異なるcombination_nameへ
    同時に参加している

    -> 複合競合
    -> competing_multiple_combinations

    3.
    情報不足

    -> 未分類競合
    """
    if not isinstance(
        conflict,
        dict,
    ):
        raise TypeError(
            "conflictはdict型で指定してください。"
        )

    position = conflict.get(
        "position"
    )

    if (
        position is not None
        and position
        not in VALID_POSITIONS
    ):
        raise ValueError(
            "不正なpositionです: "
            f"{position}"
        )

    stem = conflict.get(
        "stem"
    )

    combination_count = (
        conflict.get(
            "combination_count",
            0,
        )
    )

    combination_names = (
        normalize_combination_names(
            conflict.get(
                "combination_names",
                [],
            )
        )
    )

    partner_positions = (
        conflict.get(
            "partner_positions",
            [],
        )
    )

    if not isinstance(
        partner_positions,
        list,
    ):
        raise TypeError(
            "partner_positionsは"
            "list型で指定してください。"
        )

    unique_names = set(
        combination_names
    )

    if (
        combination_count >= 2
        and len(unique_names) == 1
        and len(combination_names) >= 2
    ):
        conflict_type = (
            "争合候補"
        )

        technical_type = (
            "competing_same_combination"
        )

        severity = "medium"

        reason = (
            "同一の天干位置が、"
            "同じ五合関係の複数候補に"
            "参加しています。"
        )

    elif (
        combination_count >= 2
        and len(unique_names) >= 2
    ):
        conflict_type = (
            "複合競合"
        )

        technical_type = (
            "competing_multiple_combinations"
        )

        severity = "high"

        reason = (
            "同一の天干位置が、"
            "異なる複数の干合候補に"
            "参加しています。"
        )

    else:
        conflict_type = (
            "未分類競合"
        )

        technical_type = (
            "unclassified_position_conflict"
        )

        severity = "low"

        reason = (
            "競合は検出されていますが、"
            "v1の分類条件だけでは"
            "詳細分類できません。"
        )

    return {
        "source_type": (
            "position_conflict"
        ),
        "position": position,
        "stem": stem,
        "combination_count": (
            combination_count
        ),
        "combination_names": (
            combination_names
        ),
        "partner_positions": (
            partner_positions
        ),
        "conflict_type": (
            conflict_type
        ),
        "technical_type": (
            technical_type
        ),
        "severity": (
            severity
        ),
        "reason": (
            reason
        ),
        "is_provisional": True,
    }


def classify_duplicate_combination(
    conflict: dict,
) -> dict:
    """
    duplicate_combinationを
    技術分類します。

    同じcombination_nameが
    複数存在する状態を、
    重複干合候補として分類します。

    これは争合候補と
    同時に存在する場合があります。
    """
    if not isinstance(
        conflict,
        dict,
    ):
        raise TypeError(
            "conflictはdict型で指定してください。"
        )

    combination_name = (
        conflict.get(
            "combination_name"
        )
    )

    combination_count = (
        conflict.get(
            "combination_count",
            0,
        )
    )

    pairs = conflict.get(
        "pairs",
        [],
    )

    if not isinstance(
        pairs,
        list,
    ):
        raise TypeError(
            "pairsはlist型で指定してください。"
        )

    return {
        "source_type": (
            "duplicate_combination"
        ),
        "combination_name": (
            combination_name
        ),
        "combination_count": (
            combination_count
        ),
        "pairs": pairs,
        "conflict_type": (
            "重複干合候補"
        ),
        "technical_type": (
            "duplicated_combination"
        ),
        "severity": (
            "low"
        ),
        "reason": (
            "同じ干合名称の候補が"
            "複数存在しています。"
        ),
        "is_provisional": True,
    }


def count_severity(
    conflicts: list[dict],
) -> dict:
    """
    severity別の件数を集計します。
    """
    counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for conflict in conflicts:
        severity = conflict.get(
            "severity"
        )

        if severity in counts:
            counts[
                severity
            ] += 1

    return counts


def determine_overall_severity(
    severity_counts: dict,
) -> str:
    """
    全競合の最大severityを返します。
    """
    if (
        severity_counts.get(
            "high",
            0,
        )
        > 0
    ):
        return "high"

    if (
        severity_counts.get(
            "medium",
            0,
        )
        > 0
    ):
        return "medium"

    if (
        severity_counts.get(
            "low",
            0,
        )
        > 0
    ):
        return "low"

    return "none"


def evaluate_stem_combination_conflict_types(
    stem_combination_conflicts: dict,
) -> dict:
    """
    干合競合情報を受け取り、
    競合タイプを暫定分類します。

    入力:
        evaluate_stem_combination_conflicts()
        の戻り値

    出力:
        typed_conflicts
        severity
        件数
        暫定分類状態
    """
    validate_conflict_data(
        stem_combination_conflicts
    )

    position_conflicts = (
        stem_combination_conflicts.get(
            "position_conflicts",
            [],
        )
    )

    duplicate_combinations = (
        stem_combination_conflicts.get(
            "duplicate_combinations",
            [],
        )
    )

    typed_position_conflicts = [
        classify_position_conflict(
            conflict
        )
        for conflict
        in position_conflicts
    ]

    typed_duplicate_conflicts = [
        classify_duplicate_combination(
            conflict
        )
        for conflict
        in duplicate_combinations
    ]

    typed_conflicts = (
        typed_position_conflicts
        + typed_duplicate_conflicts
    )

    severity_counts = (
        count_severity(
            typed_conflicts
        )
    )

    overall_severity = (
        determine_overall_severity(
            severity_counts
        )
    )

    tranh_count = sum(
        1
        for conflict
        in typed_position_conflicts
        if (
            conflict.get(
                "technical_type"
            )
            == "competing_same_combination"
        )
    )

    multiple_conflict_count = sum(
        1
        for conflict
        in typed_position_conflicts
        if (
            conflict.get(
                "technical_type"
            )
            == "competing_multiple_combinations"
        )
    )

    duplicate_count = len(
        typed_duplicate_conflicts
    )

    unclassified_count = sum(
        1
        for conflict
        in typed_position_conflicts
        if (
            conflict.get(
                "technical_type"
            )
            == "unclassified_position_conflict"
        )
    )

    has_typed_conflict = bool(
        typed_conflicts
    )

    if not has_typed_conflict:
        overall_status = (
            "not_applicable"
        )

    elif (
        unclassified_count
        == len(
            typed_position_conflicts
        )
        and duplicate_count == 0
    ):
        overall_status = (
            "partially_classified"
        )

    else:
        overall_status = (
            "classified"
        )

    return {
        "has_typed_conflict": (
            has_typed_conflict
        ),
        "typed_conflict_count": (
            len(
                typed_conflicts
            )
        ),
        "position_conflict_count": (
            len(
                typed_position_conflicts
            )
        ),
        "duplicate_conflict_count": (
            len(
                typed_duplicate_conflicts
            )
        ),
        "争合_candidate_count": (
            tranh_count
        ),
        "multiple_conflict_count": (
            multiple_conflict_count
        ),
        "unclassified_count": (
            unclassified_count
        ),
        "severity_counts": (
            severity_counts
        ),
        "overall_severity": (
            overall_severity
        ),
        "position_conflicts": (
            typed_position_conflicts
        ),
        "duplicate_conflicts": (
            typed_duplicate_conflicts
        ),
        "conflicts": (
            typed_conflicts
        ),
        "overall_status": (
            overall_status
        ),
        "method": (
            "stem_combination_conflict_types_v1"
        ),
        "status": (
            "provisional_conflict_typing"
        ),
        "notes": [
            (
                "この判定は干合競合の"
                "構造的な暫定分類です。"
            ),
            (
                "争合候補は古典上の争合を"
                "最終確定したものではありません。"
            ),
            (
                "同一positionが同じ干合関係へ"
                "複数参加する場合を"
                "争合候補として扱っています。"
            ),
            (
                "異なる干合名称への同時参加は"
                "複合競合として分類しています。"
            ),
            (
                "重複干合候補はposition競合とは"
                "別の観点で記録しています。"
            ),
            (
                "今後、陰陽・位置関係・隣接性・"
                "月令などを加えて"
                "争合・妬合判定を精密化します。"
            ),
        ],
    }
