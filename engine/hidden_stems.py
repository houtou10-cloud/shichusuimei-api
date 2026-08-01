from engine.constants import (
    BRANCHES,
    HIDDEN_STEMS,
    MAIN_HIDDEN_STEMS,
)


def get_hidden_stems(branch: str) -> list[str]:
    """
    地支に含まれる蔵干をすべて返します。

    例：
        子 -> ["癸"]
        丑 -> ["己", "癸", "辛"]
        未 -> ["己", "丁", "乙"]
    """
    if branch not in BRANCHES:
        raise ValueError(
            f"不正な地支です: {branch}"
        )

    # 元データを書き換えられないよう、
    # 新しいlistとして返します。
    return list(HIDDEN_STEMS[branch])


def get_main_hidden_stem(branch: str) -> str:
    """
    地支の主蔵干を返します。

    例：
        子 -> 癸
        丑 -> 己
        未 -> 己
        亥 -> 壬
    """
    if branch not in BRANCHES:
        raise ValueError(
            f"不正な地支です: {branch}"
        )

    return MAIN_HIDDEN_STEMS[branch]


def build_hidden_stem_data(
    branch: str,
) -> dict:
    """
    地支について、蔵干一覧と主蔵干を
    辞書形式で返します。
    """
    hidden_stems = get_hidden_stems(branch)
    main_hidden_stem = get_main_hidden_stem(
        branch
    )

    return {
        "branch": branch,
        "hidden_stems": hidden_stems,
        "main_hidden_stem": main_hidden_stem,
    }
