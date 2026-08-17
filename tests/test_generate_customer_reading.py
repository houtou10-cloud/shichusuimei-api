# ============================================================
# Warning handling
# ============================================================
#
# v1.1 policy:
#
# - valid=False
#     -> Auto-Repair対象
#
# - valid=True + warning
#     -> quality_reportへ記録
#     -> Auto-Repairしない
#     -> Product / PDF生成を継続
#
# useful_gods_role_confusion もv1.1では
# 通常warningとして扱う。
#
# より厳密な用神役割整合性の自動修復は
# v1.2で扱う。
# ============================================================


def test_should_not_auto_repair_valid_report_with_useful_gods_warning(
    script_module,
):
    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityReport,
    )

    report = ReadingQualityReport(
        valid=True,
        issues=(
            QualityIssue(
                code="useful_gods_role_confusion",
                path="sections.wealth.detail",
                message=(
                    "主用神と補助用神が"
                    "同格の用神として"
                    "表現されています。"
                ),
                value="用神は金・水・土です。",
                matched="用神は金・水・土です。",
            ),
        ),
    )

    assert (
        script_module.should_auto_repair(
            report
        )
        is False
    )

    assert (
        script_module.get_auto_repair_issue_codes(
            report
        )
        == ()
    )


def test_should_not_auto_repair_style_warning_only(
    script_module,
):
    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityReport,
    )

    report = ReadingQualityReport(
        valid=True,
        issues=(
            QualityIssue(
                code="sentence_ending_overuse",
                path="sections",
                message=(
                    "同じ説明語尾が"
                    "多数章で続いています。"
                ),
                value="career, wealth",
                matched="でしょう",
            ),
        ),
    )

    assert (
        script_module.should_auto_repair(
            report
        )
        is False
    )

    assert (
        script_module.get_auto_repair_issue_codes(
            report
        )
        == ()
    )


def test_generate_customer_reading_does_not_repair_warning_when_valid(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityReport,
    )

    configure_full_fake_pipeline(
        script_module=script_module,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        fake_chart_result=fake_chart_result,
        fake_reading_context=fake_reading_context,
        fake_generation_result=fake_generation_result,
    )

    warning_report = (
        ReadingQualityReport(
            valid=True,
            issues=(
                QualityIssue(
                    code="useful_gods_role_confusion",
                    path="sections.wealth.detail",
                    message=(
                        "主用神と補助用神が"
                        "同格の用神として"
                        "表現されています。"
                    ),
                    value="用神は火・土です。",
                    matched="用神は火・土です。",
                ),
            ),
        )
    )

    quality_count = 0
    repair_count = 0

    def fake_quality(
        ai_reading,
        *,
        reading_context,
        consultation_context=None,
    ):
        nonlocal quality_count

        quality_count += 1

        return warning_report

    def fake_repair(
        *args,
        **kwargs,
    ):
        nonlocal repair_count

        repair_count += 1

        raise AssertionError(
            "valid=Trueのwarningでは"
            "Auto-Repairを呼んではいけません。"
        )

    monkeypatch.setattr(
        script_module,
        "validate_customer_facing_reading",
        fake_quality,
    )

    monkeypatch.setattr(
        script_module,
        "repair_reading",
        fake_repair,
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    # 初回品質判定だけ。
    assert quality_count == 1

    # warningだけなのでRepairしない。
    assert repair_count == 0

    assert (
        result[
            "repair_history"
        ][
            "attempt_count"
        ]
        == 0
    )

    assert (
        result[
            "repair_history"
        ][
            "repaired"
        ]
        is False
    )

    # warning自体は削除せず、
    # 最終quality_reportへ記録する。
    final_codes = {
        issue[
            "code"
        ]
        for issue
        in result[
            "quality_report"
        ][
            "issues"
        ]
    }

    assert (
        "useful_gods_role_confusion"
        in final_codes
    )

    assert (
        result[
            "quality_report"
        ][
            "valid"
        ]
        is True
    )


def test_generate_customer_reading_warning_does_not_block_completion(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityReport,
    )

    configure_full_fake_pipeline(
        script_module=script_module,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        fake_chart_result=fake_chart_result,
        fake_reading_context=fake_reading_context,
        fake_generation_result=fake_generation_result,
    )

    warning_report = (
        ReadingQualityReport(
            valid=True,
            issues=(
                QualityIssue(
                    code="useful_gods_role_confusion",
                    path="sections.current_luck.detail",
                    message=(
                        "主用神と補助用神が"
                        "同格の用神として"
                        "表現されています。"
                    ),
                    value=(
                        "水と火の影響を見ながら、"
                        "主用神である土を活かします。"
                    ),
                    matched=(
                        "水と火の影響を見ながら、"
                        "主用神である土を活かします。"
                    ),
                ),
            ),
        )
    )

    quality_count = 0
    repair_count = 0

    def always_warning(
        ai_reading,
        *,
        reading_context,
        consultation_context=None,
    ):
        nonlocal quality_count

        quality_count += 1

        return warning_report

    def fake_repair(
        *args,
        **kwargs,
    ):
        nonlocal repair_count

        repair_count += 1

        raise AssertionError(
            "valid=Trueのwarningでは"
            "Auto-Repairを呼んではいけません。"
        )

    monkeypatch.setattr(
        script_module,
        "validate_customer_facing_reading",
        always_warning,
    )

    monkeypatch.setattr(
        script_module,
        "repair_reading",
        fake_repair,
    )

    # ReadingQualityErrorを出さず、
    # 正常に最後まで完了すること。
    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    assert quality_count == 1

    assert repair_count == 0

    assert (
        result[
            "repair_history"
        ][
            "attempt_count"
        ]
        == 0
    )

    assert (
        result[
            "repair_history"
        ][
            "repaired"
        ]
        is False
    )

    assert (
        result[
            "quality_report"
        ][
            "valid"
        ]
        is True
    )

    final_codes = {
        issue[
            "code"
        ]
        for issue
        in result[
            "quality_report"
        ][
            "issues"
        ]
    }

    assert (
        "useful_gods_role_confusion"
        in final_codes
    )
