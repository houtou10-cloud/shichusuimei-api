WEIGHTS_BY_COUNT = {
    1: [1.0],
    2: [0.7, 0.3],
    3: [0.6, 0.3, 0.1],
}


def get_hidden_stem_weights(
    hidden_stems: list[str],
) -> list[dict]:
    """
    蔵干の並び順に応じて暫定的な重みを返します。

    現在のデータ構造では、
    蔵干は主蔵干から順番に並んでいる前提です。

    1干：
        1.0

    2干：
        0.7、0.3

    3干：
        0.6、0.3、0.1

    この比率は調整可能な暫定値です。
    """
    if not isinstance(hidden_stems, list):
        raise TypeError(
            "hidden_stemsはlist型で指定してください。"
        )

    count = len(hidden_stems)

    if count not in WEIGHTS_BY_COUNT:
        raise ValueError(
            "蔵干の数は1～3個で指定してください。"
        )

    weights = WEIGHTS_BY_COUNT[count]

    return [
        {
            "stem": stem,
            "weight": weight,
            "rank": index + 1,
        }
        for index, (stem, weight) in enumerate(
            zip(hidden_stems, weights)
        )
    ]
