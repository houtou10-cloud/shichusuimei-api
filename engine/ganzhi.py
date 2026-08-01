from engine.constants import BRANCHES, STEMS


CYCLE_LENGTH = 60


def normalize_index(index: int) -> int:
    """
    任意の整数を六十干支の範囲0～59に正規化します。

    例:
        60  -> 0
        61  -> 1
        -1  -> 59
    """
    return index % CYCLE_LENGTH


def ganzhi_from_index(index: int) -> str:
    """
    六十干支の番号から干支を返します。

    0始まり:
        0  = 甲子
        1  = 乙丑
        2  = 丙寅
        ...
        59 = 癸亥
    """
    normalized_index = normalize_index(index)

    stem = STEMS[normalized_index % len(STEMS)]
    branch = BRANCHES[normalized_index % len(BRANCHES)]

    return stem + branch


def split_ganzhi(ganzhi: str) -> dict[str, str]:
    """
    「甲子」のような干支を天干と地支に分解します。
    """
    if not isinstance(ganzhi, str):
        raise TypeError("干支は文字列で指定してください。")

    if len(ganzhi) != 2:
        raise ValueError("干支は「甲子」のような2文字で指定してください。")

    stem = ganzhi[0]
    branch = ganzhi[1]

    if stem not in STEMS:
        raise ValueError(f"不正な天干です: {stem}")

    if branch not in BRANCHES:
        raise ValueError(f"不正な地支です: {branch}")

    return {
        "stem": stem,
        "branch": branch,
    }


def index_from_ganzhi(ganzhi: str) -> int:
    """
    干支から六十干支の番号を返します。

    例:
        甲子 -> 0
        甲辰 -> 40
        癸亥 -> 59
    """
    parts = split_ganzhi(ganzhi)
    target_stem = parts["stem"]
    target_branch = parts["branch"]

    for index in range(CYCLE_LENGTH):
        if ganzhi_from_index(index) == target_stem + target_branch:
            return index

    raise ValueError(
        f"{ganzhi}は有効な六十干支の組み合わせではありません。"
    )


def next_ganzhi(ganzhi: str, days: int = 1) -> str:
    """
    指定した干支から任意の日数分だけ進めた干支を返します。

    daysに負数を指定すると前へ戻ります。
    """
    current_index = index_from_ganzhi(ganzhi)

    return ganzhi_from_index(current_index + days)


def generate_sixty_ganzhi() -> list[str]:
    """
    甲子から癸亥までの六十干支一覧を返します。
    """
    return [
        ganzhi_from_index(index)
        for index in range(CYCLE_LENGTH)
    ]
