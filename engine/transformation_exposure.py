"""
天干五合の化神が、
命式内の天干に透干しているかを
評価するモジュール。

v1では以下を行います。

- 化神五行を受け取る
- 年干・月干・日干・時干を確認する
- 化神と同じ五行の天干を検出する
- 干合に参加している2干を区別する
- 干合参加者以外の透干を
  external_exposureとして評価する

重要:
透干があるだけで、
天干五合の「化成立」を
確定するものではありません。

月令・通根・妨害条件・争合などと
後で統合して最終判定します。
"""


STEM_ELEMENT = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}


VALID_ELEMENTS = {
    "木",
    "火",
    "土",
    "金",
    "水",
}


PILLAR_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


POSITION_WEIGHTS = {
    "year": 0.8,
    "month": 1.3,
    "day": 1.2,
    "hour": 1.0,
}


def get_stem_element(
    stem: str,
) -> str:
    """
    天干の五行を返します。
    """
    if stem not in STEM_ELEMENT:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENT[
        stem
    ]


def get_available_positions(
    chart_data: dict,
) -> list[str]:
    """
    命式内で利用可能な柱位置を返します。

    出生時間不明でhourがNoneの場合は、
    時柱を除外します。
    """
    return [
        position
        for position in PILLAR_POSITIONS
        if chart_data.get(position) is not None
    ]


def find_element_exposures(
    result_element: str,
    chart_data: dict,
) -> list[dict]:
    """
    化神五行と同じ五行を持つ天干を
    命式内から検出します。
    """
    if result_element not in VALID_ELEMENTS:
        raise ValueError(
            f"不正な五行です: {result_element}"
        )

    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    available_positions = (
        get_available_positions(
            chart_data
        )
    )

    exposures: list[dict] = []

    for position in available_positions:
        pillar_data = chart_data[
            position
        ]

        if not isinstance(
            pillar_data,
            dict,
        ):
            raise TypeError(
                f"{position}柱はdict型で指定してください。"
            )

        stem = pillar_data.get(
            "stem"
        )

        if stem is None:
            raise ValueError(
                f"{position}柱にstemが必要です。"
            )

        element = get_stem_element(
            stem
        )

        if element != result_element:
            continue

        position_weight = (
            POSITION_WEIGHTS[
                position
            ]
        )

        exposures.append(
            {
                "position": position,
                "stem": stem,
                "element": element,
                "position_weight": (
                    position_weight
                ),
            }
        )

    return exposures


def evaluate_transformation_exposure(
    transformation: dict,
    chart_data: dict,
) -> dict:
    """
    1件の干合候補について、
    化神の透干状況を評価します。

    干合に参加しているposition_a、
    position_bの透干と、

    それ以外の柱に存在する
    external_exposureを区別します。
    """
    if not isinstance(
        transformation,
        dict,
    ):
        raise TypeError(
            "transformationはdict型で指定してください。"
        )

    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    result_element = (
        transformation.get(
            "result_element"
        )
    )

    if result_element is None:
        raise ValueError(
            "transformationにresult_elementが必要です。"
        )

    if result_element not in VALID_ELEMENTS:
        raise ValueError(
            f"不正な五行です: {result_element}"
        )

    position_a = (
        transformation.get(
            "position_a"
        )
    )

    position_b = (
        transformation.get(
            "position_b"
        )
    )

    participant_positions = {
        position
        for position in (
            position_a,
            position_b,
        )
        if position is not None
    }

    exposures = (
        find_element_exposures(
            result_element,
            chart_data,
        )
    )

    participant_exposures = [
        exposure
        for exposure in exposures
        if (
            exposure["position"]
            in participant_positions
        )
    ]

    external_exposures = [
        exposure
        for exposure in exposures
        if (
            exposure["position"]
            not in participant_positions
        )
    ]

    exposure_count = len(
        exposures
    )

    external_exposure_count = len(
        external_exposures
    )

    has_exposure = (
        exposure_count > 0
    )

    has_external_exposure = (
        external_exposure_count > 0
    )

    total_exposure_score = round(
        sum(
            exposure[
                "position_weight"
            ]
            for exposure in exposures
        ),
        2,
    )

    external_exposure_score = round(
        sum(
            exposure[
                "position_weight"
            ]
            for exposure in external_exposures
        ),
        2,
    )

    if has_external_exposure:
        exposure_strength = "strong"

    elif has_exposure:
        exposure_strength = "participant_only"

    else:
        exposure_strength = "none"

    return {
        "combination_name": (
            transformation.get(
                "combination_name"
            )
        ),
        "result_element": (
            result_element
        ),
        "position_a": (
            position_a
        ),
        "position_b": (
            position_b
        ),
        "has_exposure": (
            has_exposure
        ),
        "exposure_count": (
            exposure_count
        ),
        "exposure_positions": [
            exposure[
                "position"
            ]
            for exposure in exposures
        ],
        "exposures": exposures,
        "participant_exposure_count": (
            len(
                participant_exposures
            )
        ),
        "participant_exposures": (
            participant_exposures
        ),
        "has_external_exposure": (
            has_external_exposure
        ),
        "external_exposure_count": (
            external_exposure_count
        ),
        "external_exposure_positions": [
            exposure[
                "position"
            ]
            for exposure in external_exposures
        ],
        "external_exposures": (
            external_exposures
        ),
        "total_exposure_score": (
            total_exposure_score
        ),
        "external_exposure_score": (
            external_exposure_score
        ),
        "exposure_strength": (
            exposure_strength
        ),
        "method": (
            "transformation_exposure_v1"
        ),
        "status": (
            "provisional_transformation_exposure"
        ),
        "notes": [
            (
                "化神五行と同じ五行を持つ"
                "天干を透干候補として"
                "評価しています。"
            ),
            (
                "干合に参加している天干と、"
                "それ以外の天干を"
                "分けて評価しています。"
            ),
            (
                "干合参加者以外の透干を"
                "external_exposureとして"
                "扱っています。"
            ),
            (
                "透干が存在しても、"
                "それだけで化成立とは"
                "判定しません。"
            ),
        ],
    }


def evaluate_transformation_exposures(
    stem_transformations: dict,
    chart_data: dict,
) -> dict:
    """
    stem_transformations内の
    各化神候補について、
    透干状況をまとめて評価します。
    """
    if not isinstance(
        stem_transformations,
        dict,
    ):
        raise TypeError(
            "stem_transformationsはdict型で指定してください。"
        )

    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    transformations = (
        stem_transformations.get(
            "transformations",
            [],
        )
    )

    if not isinstance(
        transformations,
        list,
    ):
        raise TypeError(
            "transformationsはlist型で指定してください。"
        )

    results: list[dict] = []

    for transformation in transformations:
        result_element = (
            transformation.get(
                "result_element"
            )
        )

        if result_element is None:
            raise ValueError(
                "transformationにresult_elementが必要です。"
            )

        exposure_result = (
            evaluate_transformation_exposure(
                transformation,
                chart_data,
            )
        )

        results.append(
            {
                "combination_name": (
                    transformation.get(
                        "combination_name"
                    )
                ),
                "result_element": (
                    result_element
                ),
                "transformation_status": (
                    transformation.get(
                        "transformation_status"
                    )
                ),
                "confidence": (
                    transformation.get(
                        "confidence"
                    )
                ),
                "exposure_evaluation": (
                    exposure_result
                ),
            }
        )

    exposed_count = sum(
        1
        for item in results
        if (
            item[
                "exposure_evaluation"
            ][
                "has_exposure"
            ]
        )
    )

    external_exposed_count = sum(
        1
        for item in results
        if (
            item[
                "exposure_evaluation"
            ][
                "has_external_exposure"
            ]
        )
    )

    if not results:
        overall_exposure_status = (
            "not_applicable"
        )

    elif (
        external_exposed_count
        == len(results)
    ):
        overall_exposure_status = (
            "externally_exposed"
        )

    elif external_exposed_count > 0:
        overall_exposure_status = (
            "mixed"
        )

    elif exposed_count > 0:
        overall_exposure_status = (
            "participant_only"
        )

    else:
        overall_exposure_status = (
            "unexposed"
        )

    return {
        "has_transformation_candidate": (
            bool(results)
        ),
        "transformation_count": (
            len(results)
        ),
        "exposed_count": (
            exposed_count
        ),
        "external_exposed_count": (
            external_exposed_count
        ),
        "overall_exposure_status": (
            overall_exposure_status
        ),
        "results": results,
        "method": (
            "transformation_exposures_v1"
        ),
        "status": (
            "provisional_transformation_exposures"
        ),
        "notes": [
            (
                "干合の化神候補について、"
                "命式内の天干への透干状況を"
                "評価しています。"
            ),
            (
                "干合に参加していない柱への"
                "透干を特に"
                "external_exposureとして"
                "評価しています。"
            ),
            (
                "external_exposureは"
                "化を支持する材料の一つですが、"
                "化成立の確定条件ではありません。"
            ),
            (
                "今後、月令・通根・妨害・"
                "争合などと統合します。"
            ),
        ],
    }
