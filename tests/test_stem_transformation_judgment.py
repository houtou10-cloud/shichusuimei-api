import pytest

from engine.stem_transformation_judgment import (
    classify_judgment,
    evaluate_single_transformation_judgment,
    evaluate_stem_transformation_judgment,
    find_result_by_combination,
    get_exposure_strength_score,
    get_month_support_score,
    get_root_strength_score,
)


def make_transformation(
    combination_name="甲己",
    result_element="土",
    support_level="strong",
):
    return {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "possible",
        "confidence": "high",
        "month_support": {
            "month_branch": "未",
            "month_element": "土",
            "result_element": result_element,
            "support_level": support_level,
            "support_score": 2.0,
        },
    }


def make_root_result(
    combination_name="甲己",
    result_element="土",
    root_strength="strong",
    has_root=True,
    has_month_root=True,
):
    return {
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "possible",
        "confidence": "high",
        "root_evaluation": {
            "result_element": result_element,
            "has_root": has_root,
            "has_month_root": has_month_root,
            "root_count": (
                1 if has_root else 0
            ),
            "root_positions": (
                ["month"]
                if has_root
                else []
            ),
            "total_root_score": (
                1.5 if has_root else 0.0
            ),
            "month_root_score": (
                1.5
                if has_month_root
                else 0.0
            ),
            "root_strength": root_strength,
            "roots": [],
        },
    }


def make_exposure_result(
    combination_name="甲己",
    result_element="土",
    exposure_strength="strong",
    has_exposure=True,
    has_external_exposure=True,
):
    return {
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "possible",
        "confidence": "high",
        "exposure_evaluation": {
            "combination_name": (
                combination_name
            ),
            "result_element": result_element,
            "has_exposure": has_exposure,
            "exposure_count": (
                1 if has_exposure else 0
            ),
            "has_external_exposure": (
                has_external_exposure
            ),
            "external_exposure_count": (
                1
                if has_external_exposure
                else 0
            ),
            "exposure_strength": (
                exposure_strength
            ),
        },
    }


# =========================================================
# Score conversion
# =========================================================


def test_get_month_support_score():
    assert (
        get_month_support_score(
            "strong"
        )
        == 4.0
    )

    assert (
        get_month_support_score(
            "supportive"
        )
        == 2.0
    )

    assert (
        get_month_support_score(
            "weak"
        )
        == 0.0
    )


def test_invalid_month_support_score():
    with pytest.raises(
        ValueError,
        match=(
            "不正なmonth support level"
        ),
    ):
        get_month_support_score(
            "invalid"
        )


def test_get_root_strength_score():
    assert (
        get_root_strength_score(
            "strong"
        )
        == 3.0
    )

    assert (
        get_root_strength_score(
            "present"
        )
        == 1.5
    )

    assert (
        get_root_strength_score(
            "none"
        )
        == 0.0
    )


def test_invalid_root_strength_score():
    with pytest.raises(
        ValueError,
        match="不正なroot strength",
    ):
        get_root_strength_score(
            "invalid"
        )


def test_get_exposure_strength_score():
    assert (
        get_exposure_strength_score(
            "strong"
        )
        == 2.0
    )

    assert (
        get_exposure_strength_score(
            "participant_only"
        )
        == 0.5
    )

    assert (
        get_exposure_strength_score(
            "none"
        )
        == 0.0
    )


def test_invalid_exposure_strength_score():
    with pytest.raises(
        ValueError,
        match=(
            "不正なexposure strength"
        ),
    ):
        get_exposure_strength_score(
            "invalid"
        )


# =========================================================
# find_result_by_combination
# =========================================================


def test_find_result_by_combination():
    results = [
        {
            "combination_name": "甲己",
            "value": 1,
        },
        {
            "combination_name": "乙庚",
            "value": 2,
        },
    ]

    result = find_result_by_combination(
        results,
        "乙庚",
    )

    assert result == {
        "combination_name": "乙庚",
        "value": 2,
    }


def test_find_result_by_combination_none():
    results = [
        {
            "combination_name": "甲己",
        },
    ]

    result = find_result_by_combination(
        results,
        "丙辛",
    )

    assert result is None


# =========================================================
# classify_judgment
# =========================================================


def test_classify_strong_candidate():
    result = classify_judgment(
        total_score=9.0,
        month_support_level="strong",
        has_root=True,
        has_external_exposure=True,
    )

    assert result == "strong_candidate"


def test_classify_possible_with_strong_month():
    result = classify_judgment(
        total_score=7.5,
        month_support_level="strong",
        has_root=True,
        has_external_exposure=False,
    )

    assert result == "possible"


def test_classify_possible_with_supportive_month():
    result = classify_judgment(
        total_score=5.5,
        month_support_level="supportive",
        has_root=True,
        has_external_exposure=True,
    )

    assert result == "possible"


def test_classify_weak():
    result = classify_judgment(
        total_score=4.0,
        month_support_level="strong",
        has_root=False,
        has_external_exposure=False,
    )

    assert result == "weak"


def test_classify_unsupported():
    result = classify_judgment(
        total_score=4.5,
        month_support_level="weak",
        has_root=True,
        has_external_exposure=False,
    )

    assert result == "unsupported"


# =========================================================
# Single judgment
# =========================================================


def test_single_strong_candidate():
    transformation = (
        make_transformation(
            support_level="strong"
        )
    )

    root_result = make_root_result(
        root_strength="strong",
        has_root=True,
        has_month_root=True,
    )

    exposure_result = (
        make_exposure_result(
            exposure_strength="strong",
            has_exposure=True,
            has_external_exposure=True,
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            root_result,
            exposure_result,
        )
    )

    assert (
        result["combination_name"]
        == "甲己"
    )

    assert (
        result["result_element"]
        == "土"
    )

    assert (
        result["position_a"]
        == "year"
    )

    assert (
        result["position_b"]
        == "month"
    )

    assert (
        result["month_support_level"]
        == "strong"
    )

    assert (
        result["month_support_score"]
        == 4.0
    )

    assert (
        result["root_strength"]
        == "strong"
    )

    assert (
        result["root_score"]
        == 3.0
    )

    assert result["has_root"] is True

    assert (
        result["has_month_root"]
        is True
    )

    assert (
        result["exposure_strength"]
        == "strong"
    )

    assert (
        result["exposure_score"]
        == 2.0
    )

    assert (
        result["has_exposure"]
        is True
    )

    assert (
        result[
            "has_external_exposure"
        ]
        is True
    )

    assert (
        result["total_score"]
        == 9.0
    )

    assert (
        result["judgment"]
        == "strong_candidate"
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        "strong_month_support"
        in result["supporting_factors"]
    )

    assert (
        "has_transformation_root"
        in result["supporting_factors"]
    )

    assert (
        "has_month_root"
        in result["supporting_factors"]
    )

    assert (
        "has_external_exposure"
        in result["supporting_factors"]
    )

    assert (
        result["limiting_factors"]
        == []
    )


def test_single_possible():
    transformation = (
        make_transformation(
            support_level="supportive"
        )
    )

    root_result = make_root_result(
        root_strength="strong",
        has_root=True,
        has_month_root=False,
    )

    exposure_result = (
        make_exposure_result(
            exposure_strength="participant_only",
            has_exposure=True,
            has_external_exposure=False,
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            root_result,
            exposure_result,
        )
    )

    assert (
        result["month_support_score"]
        == 2.0
    )

    assert (
        result["root_score"]
        == 3.0
    )

    assert (
        result["exposure_score"]
        == 0.5
    )

    assert (
        result["total_score"]
        == 5.5
    )

    assert (
        result["judgment"]
        == "possible"
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        "supportive_month"
        in result["supporting_factors"]
    )

    assert (
        "has_transformation_root"
        in result["supporting_factors"]
    )

    assert (
        "participant_exposure_only"
        in result["supporting_factors"]
    )

    assert (
        "no_external_exposure"
        in result["limiting_factors"]
    )


def test_single_weak():
    transformation = (
        make_transformation(
            support_level="strong"
        )
    )

    root_result = make_root_result(
        root_strength="none",
        has_root=False,
        has_month_root=False,
    )

    exposure_result = (
        make_exposure_result(
            exposure_strength="none",
            has_exposure=False,
            has_external_exposure=False,
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            root_result,
            exposure_result,
        )
    )

    assert (
        result["total_score"]
        == 4.0
    )

    assert (
        result["judgment"]
        == "weak"
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        "no_transformation_root"
        in result["limiting_factors"]
    )

    assert (
        "no_transformation_exposure"
        in result["limiting_factors"]
    )


def test_single_unsupported():
    transformation = (
        make_transformation(
            support_level="weak"
        )
    )

    root_result = make_root_result(
        root_strength="none",
        has_root=False,
        has_month_root=False,
    )

    exposure_result = (
        make_exposure_result(
            exposure_strength="none",
            has_exposure=False,
            has_external_exposure=False,
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            root_result,
            exposure_result,
        )
    )

    assert (
        result["total_score"]
        == 0.0
    )

    assert (
        result["judgment"]
        == "unsupported"
    )

    assert (
        result["confidence"]
        == "very_low"
    )

    assert (
        "weak_month_support"
        in result["limiting_factors"]
    )


# =========================================================
# Invalid single inputs
# =========================================================


def test_invalid_transformation_type():
    with pytest.raises(
        TypeError,
        match="transformationはdict型",
    ):
        evaluate_single_transformation_judgment(
            [],
            {},
            {},
        )


def test_invalid_root_result_type():
    with pytest.raises(
        TypeError,
        match="root_resultはdict型",
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            [],
            {},
        )


def test_invalid_exposure_result_type():
    with pytest.raises(
        TypeError,
        match="exposure_resultはdict型",
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            [],
        )


def test_missing_combination_name():
    transformation = (
        make_transformation()
    )

    del transformation[
        "combination_name"
    ]

    with pytest.raises(
        ValueError,
        match=(
            "combination_nameが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_result_element():
    transformation = (
        make_transformation()
    )

    del transformation[
        "result_element"
    ]

    with pytest.raises(
        ValueError,
        match=(
            "result_elementが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_month_support():
    transformation = (
        make_transformation()
    )

    del transformation[
        "month_support"
    ]

    with pytest.raises(
        ValueError,
        match="month_supportが必要です",
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_month_support_level():
    transformation = (
        make_transformation()
    )

    transformation[
        "month_support"
    ] = {}

    with pytest.raises(
        ValueError,
        match=(
            "support_levelが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_root_evaluation():
    with pytest.raises(
        ValueError,
        match=(
            "root_evaluationが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            {},
            make_exposure_result(),
        )


def test_missing_root_strength():
    root_result = make_root_result()

    root_result[
        "root_evaluation"
    ].pop(
        "root_strength"
    )

    with pytest.raises(
        ValueError,
        match="root_strengthが必要です",
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            root_result,
            make_exposure_result(),
        )


def test_missing_exposure_evaluation():
    with pytest.raises(
        ValueError,
        match=(
            "exposure_evaluationが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            {},
        )


def test_missing_exposure_strength():
    exposure_result = (
        make_exposure_result()
    )

    exposure_result[
        "exposure_evaluation"
    ].pop(
        "exposure_strength"
    )

    with pytest.raises(
        ValueError,
        match=(
            "exposure_strengthが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            exposure_result,
        )


# =========================================================
# Collection judgment
# =========================================================


def test_judgment_not_applicable():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
        )
    )

    assert (
        result[
            "has_transformation_candidate"
        ]
        is False
    )

    assert (
        result["judgment_count"]
        == 0
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 0
    )

    assert (
        result["possible_count"]
        == 0
    )

    assert (
        result["weak_count"]
        == 0
    )

    assert (
        result["unsupported_count"]
        == 0
    )

    assert (
        result["overall_judgment"]
        == "not_applicable"
    )

    assert (
        result["judgments"]
        == []
    )

    assert (
        result["method"]
        == (
            "stem_transformation_"
            "judgment_v2"
        )
    )

    assert (
        result["status"]
        == (
            "provisional_stem_"
            "transformation_judgment"
        )
    )


def test_all_strong_candidates():
    transformations = {
        "transformations": [
            make_transformation(
                combination_name="甲己",
                result_element="土",
                support_level="strong",
            ),
        ],
    }

    roots = {
        "results": [
            make_root_result(
                combination_name="甲己",
                result_element="土",
                root_strength="strong",
                has_root=True,
                has_month_root=True,
            ),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(
                combination_name="甲己",
                result_element="土",
                exposure_strength="strong",
                has_exposure=True,
                has_external_exposure=True,
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            roots,
            exposures,
        )
    )

    assert (
        result[
            "has_transformation_candidate"
        ]
        is True
    )

    assert (
        result["judgment_count"]
        == 1
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result["possible_count"]
        == 0
    )

    assert (
        result["weak_count"]
        == 0
    )

    assert (
        result["unsupported_count"]
        == 0
    )

    assert (
        result["overall_judgment"]
        == "strong_candidate"
    )


def test_all_possible():
    transformations = {
        "transformations": [
            make_transformation(
                support_level="supportive"
            ),
        ],
    }

    roots = {
        "results": [
            make_root_result(
                root_strength="strong",
                has_root=True,
                has_month_root=False,
            ),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(
                exposure_strength="participant_only",
                has_exposure=True,
                has_external_exposure=False,
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            roots,
            exposures,
        )
    )

    assert (
        result["possible_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "possible"
    )


def test_all_weak():
    transformations = {
        "transformations": [
            make_transformation(
                support_level="strong"
            ),
        ],
    }

    roots = {
        "results": [
            make_root_result(
                root_strength="none",
                has_root=False,
                has_month_root=False,
            ),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(
                exposure_strength="none",
                has_exposure=False,
                has_external_exposure=False,
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            roots,
            exposures,
        )
    )

    assert (
        result["weak_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "weak"
    )


def test_all_unsupported():
    transformations = {
        "transformations": [
            make_transformation(
                support_level="weak"
            ),
        ],
    }

    roots = {
        "results": [
            make_root_result(
                root_strength="none",
                has_root=False,
                has_month_root=False,
            ),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(
                exposure_strength="none",
                has_exposure=False,
                has_external_exposure=False,
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            roots,
            exposures,
        )
    )

    assert (
        result["unsupported_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "unsupported"
    )


def test_mixed_judgments():
    transformation_a = (
        make_transformation(
            combination_name="甲己",
            result_element="土",
            support_level="strong",
        )
    )

    transformation_b = (
        make_transformation(
            combination_name="丙辛",
            result_element="水",
            support_level="weak",
        )
    )

    transformation_b[
        "position_a"
    ] = "day"

    transformation_b[
        "position_b"
    ] = "hour"

    transformations = {
        "transformations": [
            transformation_a,
            transformation_b,
        ],
    }

    roots = {
        "results": [
            make_root_result(
                combination_name="甲己",
                result_element="土",
                root_strength="strong",
                has_root=True,
                has_month_root=True,
            ),
            make_root_result(
                combination_name="丙辛",
                result_element="水",
                root_strength="none",
                has_root=False,
                has_month_root=False,
            ),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(
                combination_name="甲己",
                result_element="土",
                exposure_strength="strong",
                has_exposure=True,
                has_external_exposure=True,
            ),
            make_exposure_result(
                combination_name="丙辛",
                result_element="水",
                exposure_strength="none",
                has_exposure=False,
                has_external_exposure=False,
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            roots,
            exposures,
        )
    )

    assert (
        result["judgment_count"]
        == 2
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result["unsupported_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "mixed"
    )


# =========================================================
# Collection validation
# =========================================================


def test_invalid_stem_transformations_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_transformationsはdict型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            [],
            {},
            {},
        )


def test_invalid_transformation_roots_type():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_rootsはdict型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            [],
            {},
        )


def test_invalid_transformation_exposures_type():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_exposuresはdict型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            [],
        )


def test_invalid_transformations_list():
    with pytest.raises(
        TypeError,
        match="transformationsはlist型",
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": {},
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
        )


def test_invalid_root_results_list():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_rootsの"
            "resultsはlist型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": {},
            },
            {
                "results": [],
            },
        )


def test_invalid_exposure_results_list():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_exposuresの"
            "resultsはlist型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": {},
            },
        )


def test_missing_root_result():
    transformations = {
        "transformations": [
            make_transformation(),
        ],
    }

    with pytest.raises(
        ValueError,
        match=(
            "対応する通根評価が"
            "見つかりません"
        ),
    ):
        evaluate_stem_transformation_judgment(
            transformations,
            {
                "results": [],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
        )


def test_missing_exposure_result():
    transformations = {
        "transformations": [
            make_transformation(),
        ],
    }

    with pytest.raises(
        ValueError,
        match=(
            "対応する透干評価が"
            "見つかりません"
        ),
    ):
        evaluate_stem_transformation_judgment(
            transformations,
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [],
            },
        )


def test_result_contains_notes():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert len(
        result["notes"]
    ) >= 1
