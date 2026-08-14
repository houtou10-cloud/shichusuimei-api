"""
tests/test_generate_customer_reading.py

scripts/generate_customer_reading.py の非LIVE統合テスト。

目的
----
本番顧客生成フローのうち、外部API・実PDF生成をfake化しながら、

顧客入力
    ↓
intake.json
    ↓
命式計算
    ↓
reading_context.json
    ↓
consultation_context.json
    ↓
AI鑑定生成
    ↓
ai_reading.json
    ↓
product.json
    ↓
四柱推命鑑定書.pdf
    ↓
summary.json

までの接続契約を固定する。

検証内容
--------
1. 入力正規化
2. customer_id生成
3. 顧客フォルダ生成
4. intake保存
5. reading_context保存
6. consultation_context保存
7. consultation_contextがgenerate_readingへ渡る
8. primary_focus=career
9. ReadingProduct生成
10. PDF生成
11. summary生成
12. APIキーやpromptを保存物へ漏らさない
13. 相談内容で命式事実を書き換えない
14. 例外処理
15. main()の終了コード
16. 最終品質ゲート

このテストはOpenAI APIを呼ばない。
Playwrightも起動しない。
"""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.consultation_context import (
    build_consultation_context,
)
from engine.reading_generator import (
    ReadingGenerationResult,
)


# ============================================================
# Load script module
# ============================================================


SCRIPT_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "scripts"
    / "generate_customer_reading.py"
)


def load_script_module():
    spec = importlib.util.spec_from_file_location(
        "generate_customer_reading_test_target",
        SCRIPT_PATH,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "generate_customer_reading.pyを"
            "読み込めませんでした。"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


@pytest.fixture
def script_module():
    return load_script_module()


# ============================================================
# Canonical fixtures
# ============================================================


@pytest.fixture
def sample_intake():
    return {
        "name": "山田太郎",
        "birth_date": "1990-05-15",
        "birth_time": "14:30",
        "birth_place": "愛知県名古屋市",
        "gender": "男性",
        "concern": (
            "現在の仕事をこのまま続けるべきか"
            "悩んでいます。収入面にも不安があり、"
            "副業や独立にも興味があります。"
        ),
        "desired_future": (
            "自分の強みを活かせる仕事を見つけ、"
            "安定した収入を得たいです。"
        ),
    }


@pytest.fixture
def fake_chart_result():
    return {
        "chart": {
            "year": {
                "pillar": "庚午",
            },
            "month": {
                "pillar": "辛巳",
            },
            "day": {
                "pillar": "乙亥",
            },
            "hour": {
                "pillar": "癸未",
            },
        }
    }


@pytest.fixture
def fake_reading_context():
    return {
        "schema_version": (
            "reading_context_v1"
        ),
        "subject": {
            "birth_date": (
                "1990-05-15"
            ),
            "birth_time": (
                "14:30"
            ),
            "birth_place": (
                "愛知県名古屋市"
            ),
            "gender": "male",
        },
        "natal_chart": {
            "pillar_sequence": [
                "庚午",
                "辛巳",
                "乙亥",
                "癸未",
            ],
            "pillars": {
                "year": {
                    "pillar": "庚午",
                },
                "month": {
                    "pillar": "辛巳",
                },
                "day": {
                    "pillar": "乙亥",
                },
                "hour": {
                    "pillar": "癸未",
                },
            },
        },
        "day_master": {
            "stem": "乙",
            "element": "木",
            "yin_yang": "陰",
            "day_pillar": "乙亥",
        },
        "five_elements": {},
        "strength": {
            "label": "中和",
        },
        "pattern": {
            "primary_pattern": "dummy",
        },
        "useful_gods": {
            "primary_useful_element": "火",
        },
        "luck": {
            "current_major_luck": {
                "ganzhi": "甲申",
            },
            "annual_luck": {
                "year": 2026,
                "ganzhi": "丙午",
            },
        },
        "reading_sections": {},
        "source_metadata": {},
        "method": "reading_context_v1",
        "status": "ready_for_ai_reading",
    }


@pytest.fixture
def fake_generation_result():
    parsed = {
        "summary": (
            "相談内容を踏まえた"
            "テスト用の全体要約です。"
        ),
        "sections": {
            "core_personality": {
                "title": "本質・性格",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "career": {
                "title": "仕事・適職",
                "summary": "summary",
                "detail": (
                    "現在の仕事と転職について"
                    "相談内容を踏まえて説明します。"
                ),
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "wealth": {
                "title": "金運",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "relationships": {
                "title": "恋愛・人間関係",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "health": {
                "title": "健康傾向",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "current_luck": {
                "title": "現在の運勢",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "future_flow": {
                "title": "今後の流れ",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
            "advice": {
                "title": "開運アドバイス",
                "summary": "summary",
                "detail": "detail",
                "evidence": ["evidence"],
                "advice": ["advice"],
            },
        },
        "disclaimer": (
            "本鑑定は傾向を示すものであり、"
            "将来を確定的に保証するものではありません。"
        ),
    }

    return ReadingGenerationResult(
        output_format="json",
        model="gpt-5",
        text=json.dumps(
            parsed,
            ensure_ascii=False,
        ),
        parsed=parsed,
        response_id=(
            "resp_test_customer_001"
        ),
        response_status="completed",
        usage={
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
        },
        sections=(
            "core_personality",
            "career",
            "wealth",
            "relationships",
            "health",
            "current_luck",
            "future_flow",
            "advice",
        ),
        method=(
            "openai_responses_api_v1"
        ),
        status="completed",
    )


class FakeProduct:
    def __init__(
        self,
        *,
        title,
        context,
        generation_result,
        sections,
    ):
        self.title = title

        self.sections = [
            {
                "key": section,
            }
            for section
            in sections
        ]

        self._data = {
            "title": title,
            "subject": deepcopy(
                context.get(
                    "subject",
                    {},
                )
            ),
            "chart_summary": {
                "pillar_sequence": deepcopy(
                    context[
                        "natal_chart"
                    ][
                        "pillar_sequence"
                    ]
                ),
                "day_master": deepcopy(
                    context[
                        "day_master"
                    ]
                ),
            },
            "sections": deepcopy(
                generation_result.parsed[
                    "sections"
                ]
            ),
            "summary": (
                generation_result.parsed[
                    "summary"
                ]
            ),
            "disclaimer": (
                generation_result.parsed[
                    "disclaimer"
                ]
            ),
            "generation": {
                "model": (
                    generation_result.model
                ),
                "response_id": (
                    generation_result.response_id
                ),
                "response_status": (
                    generation_result.response_status
                ),
                "usage": deepcopy(
                    generation_result.usage
                ),
                "method": (
                    generation_result.method
                ),
                "status": (
                    generation_result.status
                ),
            },
            "metadata": {
                "recalculates_astrology": (
                    False
                ),
                "rewrites_ai_reading": (
                    False
                ),
            },
        }

    def to_dict(
        self,
    ):
        return deepcopy(
            self._data
        )


# ============================================================
# Basic normalization
# ============================================================


def test_normalize_birth_date(
    script_module,
):
    assert (
        script_module.normalize_birth_date(
            "1990-05-15"
        )
        == "1990-05-15"
    )


@pytest.mark.parametrize(
    "value",
    (
        "1990/05/15",
        "1990-5-15",
        "",
        "abc",
    ),
)
def test_normalize_birth_date_rejects_bad_value(
    script_module,
    value,
):
    with pytest.raises(
        (TypeError, ValueError)
    ):
        script_module.normalize_birth_date(
            value
        )


def test_normalize_birth_time(
    script_module,
):
    assert (
        script_module.normalize_birth_time(
            "14:30"
        )
        == "14:30"
    )


@pytest.mark.parametrize(
    "value",
    (
        "25:00",
        "14時30分",
        "",
        "abc",
    ),
)
def test_normalize_birth_time_rejects_bad_value(
    script_module,
    value,
):
    with pytest.raises(
        (TypeError, ValueError)
    ):
        script_module.normalize_birth_time(
            value
        )


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("男性", "male"),
        ("男", "male"),
        ("male", "male"),
        ("m", "male"),
        ("女性", "female"),
        ("女", "female"),
        ("female", "female"),
        ("f", "female"),
    ),
)
def test_normalize_gender(
    script_module,
    raw,
    expected,
):
    assert (
        script_module.normalize_gender(
            raw
        )
        == expected
    )


def test_normalize_gender_rejects_unknown(
    script_module,
):
    with pytest.raises(
        ValueError
    ):
        script_module.normalize_gender(
            "unknown"
        )


# ============================================================
# Customer id / directory
# ============================================================


def test_create_customer_id(
    script_module,
):
    from datetime import datetime

    assert (
        script_module.create_customer_id(
            datetime(
                2026,
                8,
                13,
                16,
                13,
                44,
            )
        )
        == "20260813_161344"
    )


def test_create_customer_dir(
    script_module,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        script_module,
        "OUTPUT_ROOT",
        tmp_path,
    )

    result = (
        script_module.create_customer_dir(
            "20260813_161344"
        )
    )

    assert (
        result
        == (
            tmp_path
            / "20260813_161344"
        )
    )

    assert result.exists()


@pytest.mark.parametrize(
    "bad_id",
    (
        "",
        "abc",
        "20260813",
        "20260813-161344",
        "../20260813_161344",
    ),
)
def test_create_customer_dir_rejects_bad_id(
    script_module,
    tmp_path,
    monkeypatch,
    bad_id,
):
    monkeypatch.setattr(
        script_module,
        "OUTPUT_ROOT",
        tmp_path,
    )

    with pytest.raises(
        (TypeError, ValueError)
    ):
        script_module.create_customer_dir(
            bad_id
        )


# ============================================================
# Chart helpers
# ============================================================


def test_build_chart_request(
    script_module,
):
    intake = {
        "birth_date": (
            "1990-05-15"
        ),
        "birth_time": (
            "14:30"
        ),
        "birth_place": (
            "愛知県名古屋市"
        ),
        "gender": "male",
    }

    request = (
        script_module.build_chart_request(
            intake
        )
    )

    assert (
        request.birth_date
        == "1990-05-15"
    )

    assert (
        request.birth_time
        == "14:30"
    )

    assert (
        request.birth_place
        == "愛知県名古屋市"
    )

    assert (
        request.gender
        == "male"
    )


def test_extract_pillars(
    script_module,
    fake_chart_result,
):
    assert (
        script_module.extract_pillars(
            fake_chart_result
        )
        == {
            "year": "庚午",
            "month": "辛巳",
            "day": "乙亥",
            "hour": "癸未",
        }
    )


def test_extract_day_master(
    script_module,
    fake_reading_context,
):
    assert (
        script_module.extract_day_master(
            fake_reading_context
        )
        == "乙"
    )


# ============================================================
# Security
# ============================================================


def test_output_security_accepts_clean_data(
    script_module,
    fake_reading_context,
):
    consultation = (
        build_consultation_context(
            concern=(
                "仕事について悩んでいます。"
            ),
            desired_future=(
                "安定した収入を得たいです。"
            ),
        )
    )

    script_module.validate_output_security(
        product_data={
            "title": (
                "四柱推命鑑定書"
            )
        },
        consultation_context=(
            consultation
        ),
        reading_context=(
            fake_reading_context
        ),
    )


def test_output_security_rejects_api_key(
    script_module,
    fake_reading_context,
    monkeypatch,
):
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "sk-test-secret",
    )

    consultation = (
        build_consultation_context()
    )

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_output_security(
            product_data={
                "leak": (
                    "sk-test-secret"
                )
            },
            consultation_context=(
                consultation
            ),
            reading_context=(
                fake_reading_context
            ),
        )


@pytest.mark.parametrize(
    "marker",
    (
        "api_key",
        "system_prompt",
        "user_prompt",
    ),
)
def test_output_security_rejects_private_markers(
    script_module,
    fake_reading_context,
    marker,
):
    consultation = (
        build_consultation_context()
    )

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_output_security(
            product_data={
                marker: "secret"
            },
            consultation_context=(
                consultation
            ),
            reading_context=(
                fake_reading_context
            ),
        )


# ============================================================
# Full fake E2E
# ============================================================


def configure_full_fake_pipeline(
    *,
    script_module,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    monkeypatch.setattr(
        script_module,
        "OUTPUT_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        script_module,
        "validate_environment",
        lambda: "gpt-5",
    )

    monkeypatch.setattr(
        script_module,
        "calculate_chart",
        lambda request,
        target_datetime=None: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        script_module,
        "build_reading_context",
        lambda chart_result: deepcopy(
            fake_reading_context
        ),
    )

    captured = {
        "generate_reading": None,
        "product": None,
    }

    def fake_generate_reading(
        reading_context,
        *,
        consultation_context=None,
        **kwargs,
    ):
        captured[
            "generate_reading"
        ] = {
            "reading_context": deepcopy(
                reading_context
            ),
            "consultation_context": deepcopy(
                consultation_context
            ),
            "kwargs": deepcopy(
                kwargs
            ),
        }

        return deepcopy(
            fake_generation_result
        )

    monkeypatch.setattr(
        script_module,
        "generate_reading",
        fake_generate_reading,
    )

    def fake_build_reading_product(
        reading_context,
        generation_result,
        *,
        title,
        sections,
    ):
        product = FakeProduct(
            title=title,
            context=reading_context,
            generation_result=(
                generation_result
            ),
            sections=sections,
        )

        captured[
            "product"
        ] = product

        return product

    monkeypatch.setattr(
        script_module,
        "build_reading_product",
        fake_build_reading_product,
    )

    # validate_product() は isinstance(ReadingProduct) を要求するので
    # fake productを使うこのE2Eでは関数自体を置換する。
    monkeypatch.setattr(
        script_module,
        "validate_product",
        lambda product: None,
    )

    def fake_write_pdf(
        product,
        output_path,
        *,
        document_title=None,
        **kwargs,
    ):
        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_bytes(
            b"%PDF-1.7\n"
            b"fake customer reading pdf"
        )

        return output_path

    monkeypatch.setattr(
        script_module,
        "write_reading_product_pdf",
        fake_write_pdf,
    )

    monkeypatch.setattr(
        script_module,
        "get_reading_pdf_metadata",
        lambda: {
            "version": (
                "reading_pdf_v1"
            ),
            "method": (
                "html_to_pdf_"
                "playwright_chromium_v1"
            ),
            "status": "ready",
            "recalculates_astrology": (
                False
            ),
        },
    )

    return captured


def test_generate_customer_reading_full_fake_e2e(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    captured = (
        configure_full_fake_pipeline(
            script_module=(
                script_module
            ),
            tmp_path=tmp_path,
            monkeypatch=(
                monkeypatch
            ),
            fake_chart_result=(
                fake_chart_result
            ),
            fake_reading_context=(
                fake_reading_context
            ),
            fake_generation_result=(
                fake_generation_result
            ),
        )
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    assert (
        result[
            "pillars"
        ]
        == {
            "year": "庚午",
            "month": "辛巳",
            "day": "乙亥",
            "hour": "癸未",
        }
    )

    assert (
        result[
            "day_master"
        ]
        == "乙"
    )

    assert (
        result[
            "primary_focus"
        ]
        == "career"
    )

    assert (
        result[
            "response_status"
        ]
        == "completed"
    )

    assert (
        result[
            "response_id"
        ]
        == "resp_test_customer_001"
    )

    assert (
        result[
            "model"
        ]
        == "gpt-5"
    )

    assert (
        result[
            "pdf_size"
        ]
        > 0
    )

    assert (
        captured[
            "generate_reading"
        ]
        is not None
    )


def test_generate_customer_reading_passes_consultation_to_generator(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    captured = (
        configure_full_fake_pipeline(
            script_module=(
                script_module
            ),
            tmp_path=tmp_path,
            monkeypatch=(
                monkeypatch
            ),
            fake_chart_result=(
                fake_chart_result
            ),
            fake_reading_context=(
                fake_reading_context
            ),
            fake_generation_result=(
                fake_generation_result
            ),
        )
    )

    script_module.generate_customer_reading(
        sample_intake
    )

    call = captured[
        "generate_reading"
    ]

    assert (
        call[
            "consultation_context"
        ][
            "focus"
        ][
            "primary"
        ]
        == "career"
    )

    assert (
        call[
            "consultation_context"
        ][
            "input"
        ][
            "concern"
        ]
        == sample_intake[
            "concern"
        ]
    )

    assert (
        call[
            "consultation_context"
        ][
            "input"
        ][
            "desired_future"
        ]
        == sample_intake[
            "desired_future"
        ]
    )


def test_generate_customer_reading_generator_configuration(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    captured = (
        configure_full_fake_pipeline(
            script_module=(
                script_module
            ),
            tmp_path=tmp_path,
            monkeypatch=(
                monkeypatch
            ),
            fake_chart_result=(
                fake_chart_result
            ),
            fake_reading_context=(
                fake_reading_context
            ),
            fake_generation_result=(
                fake_generation_result
            ),
        )
    )

    script_module.generate_customer_reading(
        sample_intake
    )

    kwargs = captured[
        "generate_reading"
    ][
        "kwargs"
    ]

    assert (
        kwargs[
            "model"
        ]
        == "gpt-5"
    )

    assert (
        tuple(
            kwargs[
                "sections"
            ]
        )
        == script_module.SECTIONS
    )

    assert (
        kwargs[
            "language"
        ]
        == "ja"
    )

    assert (
        kwargs[
            "tone"
        ]
        == "professional_warm"
    )

    assert (
        kwargs[
            "output_format"
        ]
        == "json"
    )

    assert (
        kwargs[
            "store"
        ]
        is False
    )


# ============================================================
# Saved files
# ============================================================


def test_full_e2e_saves_all_expected_files(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    expected = (
        "intake_path",
        "reading_context_path",
        "consultation_context_path",
        "ai_reading_path",
        "product_path",
        "pdf_path",
        "summary_path",
    )

    for key in expected:
        assert (
            result[
                key
            ].exists()
        )


def test_intake_json_contents(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    data = json.loads(
        result[
            "intake_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        data[
            "name"
        ]
        == "山田太郎"
    )

    assert (
        data[
            "gender"
        ]
        == "male"
    )

    assert (
        data[
            "concern"
        ]
        == sample_intake[
            "concern"
        ]
    )

    assert (
        data[
            "desired_future"
        ]
        == sample_intake[
            "desired_future"
        ]
    )

    assert (
        data[
            "schema_version"
        ]
        == "customer_intake_v1"
    )


def test_consultation_context_json_contents(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    data = json.loads(
        result[
            "consultation_context_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        data[
            "version"
        ]
        == "consultation_context_v1"
    )

    assert (
        data[
            "focus"
        ][
            "primary"
        ]
        == "career"
    )

    assert (
        data[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        data[
            "rewrites_chart_facts"
        ]
        is False
    )


def test_reading_context_json_preserves_chart(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    data = json.loads(
        result[
            "reading_context_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        data[
            "natal_chart"
        ][
            "pillar_sequence"
        ]
        == [
            "庚午",
            "辛巳",
            "乙亥",
            "癸未",
        ]
    )

    assert (
        data[
            "day_master"
        ][
            "stem"
        ]
        == "乙"
    )


def test_ai_reading_json_contents(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    data = json.loads(
        result[
            "ai_reading_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        "career"
        in data[
            "sections"
        ]
    )

    assert (
        "転職"
        in data[
            "sections"
        ][
            "career"
        ][
            "detail"
        ]
    )


def test_product_json_has_no_private_prompt_fields(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    raw = (
        result[
            "product_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        "system_prompt"
        not in raw
    )

    assert (
        "user_prompt"
        not in raw
    )

    assert (
        '"api_key"'
        not in raw
    )


def test_summary_json_contents(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    configure_full_fake_pipeline(
        script_module=(
            script_module
        ),
        tmp_path=tmp_path,
        monkeypatch=(
            monkeypatch
        ),
        fake_chart_result=(
            fake_chart_result
        ),
        fake_reading_context=(
            fake_reading_context
        ),
        fake_generation_result=(
            fake_generation_result
        ),
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    data = json.loads(
        result[
            "summary_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        data[
            "status"
        ]
        == "completed"
    )

    assert (
        data[
            "customer_name"
        ]
        == "山田太郎"
    )

    assert (
        data[
            "day_master"
        ]
        == "乙"
    )

    assert (
        data[
            "consultation"
        ][
            "primary_focus"
        ]
        == "career"
    )

    assert (
        data[
            "generation"
        ][
            "response_id"
        ]
        == "resp_test_customer_001"
    )

    assert (
        data[
            "pdf"
        ][
            "size_bytes"
        ]
        > 0
    )

    assert (
        data[
            "pdf_metadata"
        ][
            "recalculates_astrology"
        ]
        is False
    )


# ============================================================
# No astrology mutation
# ============================================================


def test_consultation_does_not_mutate_reading_context(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    original = deepcopy(
        fake_reading_context
    )

    captured = (
        configure_full_fake_pipeline(
            script_module=(
                script_module
            ),
            tmp_path=tmp_path,
            monkeypatch=(
                monkeypatch
            ),
            fake_chart_result=(
                fake_chart_result
            ),
            fake_reading_context=(
                fake_reading_context
            ),
            fake_generation_result=(
                fake_generation_result
            ),
        )
    )

    script_module.generate_customer_reading(
        sample_intake
    )

    passed_context = (
        captured[
            "generate_reading"
        ][
            "reading_context"
        ]
    )

    assert (
        passed_context[
            "natal_chart"
        ][
            "pillar_sequence"
        ]
        == original[
            "natal_chart"
        ][
            "pillar_sequence"
        ]
    )

    assert (
        passed_context[
            "day_master"
        ]
        == original[
            "day_master"
        ]
    )

    assert (
        passed_context[
            "strength"
        ]
        == original[
            "strength"
        ]
    )

    assert (
        passed_context[
            "pattern"
        ]
        == original[
            "pattern"
        ]
    )

    assert (
        passed_context[
            "useful_gods"
        ]
        == original[
            "useful_gods"
        ]
    )


def test_wrong_customer_assumption_does_not_rewrite_chart(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    intake = deepcopy(
        sample_intake
    )

    intake[
        "concern"
    ] = (
        "私は日主が甲だと思っています。"
        "甲として鑑定してください。"
    )

    captured = (
        configure_full_fake_pipeline(
            script_module=(
                script_module
            ),
            tmp_path=tmp_path,
            monkeypatch=(
                monkeypatch
            ),
            fake_chart_result=(
                fake_chart_result
            ),
            fake_reading_context=(
                fake_reading_context
            ),
            fake_generation_result=(
                fake_generation_result
            ),
        )
    )

    result = (
        script_module.generate_customer_reading(
            intake
        )
    )

    passed_context = (
        captured[
            "generate_reading"
        ][
            "reading_context"
        ]
    )

    assert (
        passed_context[
            "day_master"
        ][
            "stem"
        ]
        == "乙"
    )

    assert (
        result[
            "day_master"
        ]
        == "乙"
    )

    assert (
        result[
            "pillars"
        ][
            "day"
        ]
        == "乙亥"
    )


# ============================================================
# Generation result validation
# ============================================================


def test_validate_generation_result_success(
    script_module,
    fake_generation_result,
):
    script_module.validate_generation_result(
        fake_generation_result
    )


def test_validate_generation_result_rejects_non_json(
    script_module,
    fake_generation_result,
):
    broken = deepcopy(
        fake_generation_result
    )

    broken.output_format = (
        "text"
    )

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_generation_result(
            broken
        )


def test_validate_generation_result_rejects_missing_parsed(
    script_module,
    fake_generation_result,
):
    broken = deepcopy(
        fake_generation_result
    )

    broken.parsed = None

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_generation_result(
            broken
        )


def test_validate_generation_result_rejects_incomplete_status(
    script_module,
    fake_generation_result,
):
    broken = deepcopy(
        fake_generation_result
    )

    broken.status = (
        "incomplete"
    )

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_generation_result(
            broken
        )


# ============================================================
# PDF validation
# ============================================================


def test_validate_pdf_success(
    script_module,
    tmp_path,
):
    path = (
        tmp_path
        / "reading.pdf"
    )

    path.write_bytes(
        b"%PDF-1.7\nabc"
    )

    assert (
        script_module.validate_pdf(
            path
        )
        == len(
            b"%PDF-1.7\nabc"
        )
    )


def test_validate_pdf_rejects_missing(
    script_module,
    tmp_path,
):
    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_pdf(
            tmp_path
            / "missing.pdf"
        )


def test_validate_pdf_rejects_empty(
    script_module,
    tmp_path,
):
    path = (
        tmp_path
        / "empty.pdf"
    )

    path.write_bytes(
        b""
    )

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_pdf(
            path
        )


def test_validate_pdf_rejects_non_pdf(
    script_module,
    tmp_path,
):
    path = (
        tmp_path
        / "bad.pdf"
    )

    path.write_bytes(
        b"not pdf"
    )

    with pytest.raises(
        RuntimeError
    ):
        script_module.validate_pdf(
            path
        )


# ============================================================
# main()
# ============================================================


def test_main_missing_api_key_returns_1(
    script_module,
    monkeypatch,
):
    monkeypatch.setattr(
        script_module,
        "has_openai_api_key",
        lambda: False,
    )

    assert (
        script_module.main()
        == 1
    )


def test_main_success_returns_0(
    script_module,
    monkeypatch,
):
    monkeypatch.setattr(
        script_module,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        script_module,
        "get_default_model",
        lambda: "gpt-5",
    )

    fake_intake = {
        "name": "山田太郎",
    }

    monkeypatch.setattr(
        script_module,
        "prompt_customer_input",
        lambda: fake_intake,
    )

    fake_result = {
        "customer_id": (
            "20260813_161344"
        ),
        "primary_focus": "career",
        "pillars": {
            "year": "庚午",
            "month": "辛巳",
            "day": "乙亥",
            "hour": "癸未",
        },
        "day_master": "乙",
        "pdf_path": Path(
            "dummy.pdf"
        ),
        "product_path": Path(
            "product.json"
        ),
        "ai_reading_path": Path(
            "ai_reading.json"
        ),
        "reading_context_path": Path(
            "reading_context.json"
        ),
        "consultation_context_path": Path(
            "consultation_context.json"
        ),
        "intake_path": Path(
            "intake.json"
        ),
        "summary_path": Path(
            "summary.json"
        ),
        "response_status": "completed",
        "response_id": (
            "resp_test"
        ),
        "model": "gpt-5",
        "pdf_size": 1234,
        "usage": {},
    }

    monkeypatch.setattr(
        script_module,
        "generate_customer_reading",
        lambda intake: deepcopy(
            fake_result
        ),
    )

    monkeypatch.setattr(
        script_module,
        "print_completion",
        lambda **kwargs: None,
    )

    assert (
        script_module.main()
        == 0
    )


def test_main_generation_error_returns_1(
    script_module,
    monkeypatch,
):
    monkeypatch.setattr(
        script_module,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        script_module,
        "get_default_model",
        lambda: "gpt-5",
    )

    monkeypatch.setattr(
        script_module,
        "prompt_customer_input",
        lambda: {
            "name": "山田太郎"
        },
    )

    def raise_error(
        intake,
    ):
        raise RuntimeError(
            "test failure"
        )

    monkeypatch.setattr(
        script_module,
        "generate_customer_reading",
        raise_error,
    )

    assert (
        script_module.main()
        == 1
    )


# ============================================================
# Final gate
# ============================================================


def test_generate_customer_reading_v1_1_final_gate(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    """
    顧客入力
        ↓
    命式
        ↓
    reading_context
        ↓
    consultation_context
        ↓
    AI鑑定
        ↓
    product
        ↓
    PDF
        ↓
    保存物

    の最終非LIVE品質ゲート。
    """

    captured = (
        configure_full_fake_pipeline(
            script_module=(
                script_module
            ),
            tmp_path=tmp_path,
            monkeypatch=(
                monkeypatch
            ),
            fake_chart_result=(
                fake_chart_result
            ),
            fake_reading_context=(
                fake_reading_context
            ),
            fake_generation_result=(
                fake_generation_result
            ),
        )
    )

    result = (
        script_module.generate_customer_reading(
            sample_intake
        )
    )

    assert (
        result[
            "primary_focus"
        ]
        == "career"
    )

    assert (
        result[
            "pillars"
        ]
        == {
            "year": "庚午",
            "month": "辛巳",
            "day": "乙亥",
            "hour": "癸未",
        }
    )

    assert (
        result[
            "day_master"
        ]
        == "乙"
    )

    assert (
        captured[
            "generate_reading"
        ][
            "consultation_context"
        ][
            "focus"
        ][
            "primary"
        ]
        == "career"
    )

    assert (
        captured[
            "generate_reading"
        ][
            "reading_context"
        ][
            "day_master"
        ][
            "stem"
        ]
        == "乙"
    )

    for key in (
        "intake_path",
        "reading_context_path",
        "consultation_context_path",
        "ai_reading_path",
        "product_path",
        "pdf_path",
        "summary_path",
    ):
        assert (
            result[
                key
            ].exists()
        )

    assert (
        result[
            "pdf_path"
        ].read_bytes().startswith(
            b"%PDF"
        )
    )

    product_text = (
        result[
            "product_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        "system_prompt"
        not in product_text
    )

    assert (
        "user_prompt"
        not in product_text
    )

    assert (
        '"api_key"'
        not in product_text
    )

    summary = json.loads(
        result[
            "summary_path"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        summary[
            "status"
        ]
        == "completed"
    )

    assert (
        summary[
            "consultation"
        ][
            "primary_focus"
        ]
        == "career"
    )

    assert (
        summary[
            "generation"
        ][
            "response_status"
        ]
        == "completed"
    )

    assert (
        summary[
            "pdf_metadata"
        ][
            "recalculates_astrology"
        ]
        is False
    )


# ============================================================
# Auto-Repair integration
# ============================================================


def test_generate_customer_reading_auto_repair_then_passes(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    """
    初回品質ゲートNG
      -> Auto-Repair 1回
      -> 再検査OK
      -> Product / PDF生成

    をLIVE APIなしで確認する統合テスト。
    """

    from copy import deepcopy

    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityReport,
    )
    from engine.reading_repair import (
        ReadingRepairResult,
    )

    captured = configure_full_fake_pipeline(
        script_module=script_module,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        fake_chart_result=fake_chart_result,
        fake_reading_context=fake_reading_context,
        fake_generation_result=fake_generation_result,
    )

    original = deepcopy(
        fake_generation_result.parsed
    )
    repaired = deepcopy(original)

    repaired["sections"]["career"]["detail"] = (
        "仕事内容、収入、働き方の条件を分けて比較し、"
        "現職継続と転職の両方を現実的に検討するとよいでしょう。"
    )

    invalid_report = ReadingQualityReport(
        valid=False,
        issues=(
            QualityIssue(
                code="cross_section_advice_repetition",
                path="sections",
                message=(
                    "同じ助言概念が多くの"
                    "セクションで繰り返されています。"
                ),
                value="career, future_flow, advice",
                matched="再現性",
            ),
        ),
    )

    valid_report = ReadingQualityReport(
        valid=True,
        issues=(),
    )

    quality_calls = []

    def fake_quality(
        ai_reading,
        *,
        reading_context,
        consultation_context=None,
    ):
        quality_calls.append(
            deepcopy(ai_reading)
        )
        if len(quality_calls) == 1:
            return invalid_report
        return valid_report

    repair_calls = []

    def fake_repair(
        ai_reading,
        quality_report,
        *,
        reading_context,
        consultation_context=None,
        client=None,
        model=None,
        max_output_tokens=None,
        reasoning_effort=None,
        store=None,
    ):
        repair_calls.append(
            {
                "ai_reading": deepcopy(ai_reading),
                "quality_report": quality_report,
                "reading_context": deepcopy(
                    reading_context
                ),
                "consultation_context": deepcopy(
                    consultation_context
                ),
                "model": model,
                "max_output_tokens": max_output_tokens,
                "reasoning_effort": reasoning_effort,
                "store": store,
            }
        )

        return ReadingRepairResult(
            original=deepcopy(ai_reading),
            repaired=deepcopy(repaired),
            issue_count=1,
            error_count=0,
            warning_count=1,
            repaired_issue_codes=(
                "cross_section_advice_repetition",
            ),
            response_id="resp_repair_fake_001",
            response_status="completed",
            model=model or "gpt-5",
            usage={
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
            },
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

    result = script_module.generate_customer_reading(
        sample_intake
    )

    assert len(quality_calls) == 2
    assert len(repair_calls) == 1

    call = repair_calls[0]

    assert call["ai_reading"] == original
    assert call["quality_report"] is invalid_report
    assert call["reading_context"] == fake_reading_context
    assert (
        call["consultation_context"]["focus"]["primary"]
        == "career"
    )
    assert call["model"] == "gpt-5"
    assert (
        call["max_output_tokens"]
        == script_module.REPAIR_MAX_OUTPUT_TOKENS
    )
    assert (
        call["reasoning_effort"]
        == script_module.REPAIR_REASONING_EFFORT
    )
    assert call["store"] is script_module.REPAIR_STORE

    # Repair後JSONが再検査されている。
    assert quality_calls[1] == repaired

    # 最終品質は合格。
    assert result["quality_report"]["valid"] is True
    assert result["quality_report"]["issue_count"] == 0

    # Repair履歴が1回分保存される。
    history = result["repair_history"]

    assert history["repaired"] is True
    assert history["attempt_count"] == 1
    assert history["initial_quality"]["valid"] is False
    assert history["final_quality"]["valid"] is True
    assert history["final_valid"] is True

    attempt = history["attempts"][0]

    assert attempt["attempt"] == 1
    assert (
        attempt["repair"]["response_id"]
        == "resp_repair_fake_001"
    )
    assert attempt["quality_before"]["valid"] is False
    assert attempt["quality_after"]["valid"] is True

    # ai_reading.json はRepair後の最終採用版。
    saved_ai_reading = json.loads(
        result[
            "ai_reading_path"
        ].read_text(
            encoding="utf-8"
        )
    )
    assert saved_ai_reading == repaired

    # repair_history.json が存在し、内容も一致。
    assert result["repair_history_path"].exists()

    saved_history = json.loads(
        result[
            "repair_history_path"
        ].read_text(
            encoding="utf-8"
        )
    )
    assert saved_history["attempt_count"] == 1
    assert saved_history["repaired"] is True
    assert saved_history["final_valid"] is True

    # Product工程にもRepair後の結果を渡す。
    product_data = (
        captured[
            "product"
        ].to_dict()
    )

    assert (
        product_data[
            "sections"
        ]
        == repaired[
            "sections"
        ]
    )

    assert (
        product_data[
            "summary"
        ]
        == repaired[
            "summary"
        ]
    )

    assert (
        product_data[
            "disclaimer"
        ]
        == repaired[
            "disclaimer"
        ]
    )

    # 初回生成結果を破壊しない。
    assert fake_generation_result.parsed == original


def test_generate_customer_reading_skips_repair_when_quality_passes(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    """
    初回valid=TrueならRepair APIを呼ばない。
    """

    configure_full_fake_pipeline(
        script_module=script_module,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        fake_chart_result=fake_chart_result,
        fake_reading_context=fake_reading_context,
        fake_generation_result=fake_generation_result,
    )

    def forbidden_repair(*args, **kwargs):
        raise AssertionError(
            "valid=Trueなのにrepair_readingが呼ばれました。"
        )

    monkeypatch.setattr(
        script_module,
        "repair_reading",
        forbidden_repair,
    )

    result = script_module.generate_customer_reading(
        sample_intake
    )

    assert result["quality_report"]["valid"] is True
    assert result["repair_history"]["attempt_count"] == 0
    assert result["repair_history"]["repaired"] is False


def test_generate_customer_reading_auto_repair_second_attempt_passes(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    """
    1回目Repair後もNG、
    2回目Repair後にOKなら2回で停止する。
    """

    from copy import deepcopy

    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityReport,
    )
    from engine.reading_repair import (
        ReadingRepairResult,
    )

    configure_full_fake_pipeline(
        script_module=script_module,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        fake_chart_result=fake_chart_result,
        fake_reading_context=fake_reading_context,
        fake_generation_result=fake_generation_result,
    )

    invalid = ReadingQualityReport(
        valid=False,
        issues=(
            QualityIssue(
                code="cross_section_advice_repetition",
                path="sections",
                message="同じ助言概念が繰り返されています。",
                value="career, advice",
                matched="再現性",
            ),
        ),
    )
    valid = ReadingQualityReport(
        valid=True,
        issues=(),
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
        return (
            valid
            if quality_count >= 3
            else invalid
        )

    def fake_repair(
        ai_reading,
        quality_report,
        *,
        reading_context,
        consultation_context=None,
        client=None,
        model=None,
        max_output_tokens=None,
        reasoning_effort=None,
        store=None,
    ):
        nonlocal repair_count
        repair_count += 1

        repaired = deepcopy(ai_reading)
        repaired["sections"]["career"]["detail"] = (
            f"Repair attempt {repair_count}"
        )

        return ReadingRepairResult(
            original=deepcopy(ai_reading),
            repaired=repaired,
            issue_count=1,
            error_count=0,
            warning_count=1,
            repaired_issue_codes=(
                "cross_section_advice_repetition",
            ),
            response_id=(
                f"resp_repair_fake_{repair_count:03d}"
            ),
            response_status="completed",
            model=model or "gpt-5",
            usage={},
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

    result = script_module.generate_customer_reading(
        sample_intake
    )

    assert quality_count == 3
    assert repair_count == 2
    assert result["repair_history"]["attempt_count"] == 2
    assert result["repair_history"]["final_valid"] is True
    assert result["quality_report"]["valid"] is True


def test_generate_customer_reading_auto_repair_exhaustion_raises(
    script_module,
    sample_intake,
    tmp_path,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_result,
):
    """
    最大回数RepairしてもNGならReadingQualityError。
    無限ループしない。
    """

    from copy import deepcopy

    from engine.reading_quality import (
        QualityIssue,
        ReadingQualityError,
        ReadingQualityReport,
    )
    from engine.reading_repair import (
        ReadingRepairResult,
    )

    configure_full_fake_pipeline(
        script_module=script_module,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        fake_chart_result=fake_chart_result,
        fake_reading_context=fake_reading_context,
        fake_generation_result=fake_generation_result,
    )

    invalid = ReadingQualityReport(
        valid=False,
        issues=(
            QualityIssue(
                code="health_astrology_specific_overreach",
                path="sections.health.detail",
                message=(
                    "健康章で具体的な身体状態を"
                    "直接推測しています。"
                ),
                value="姿勢",
                matched="姿勢",
            ),
        ),
    )

    quality_count = 0
    repair_count = 0

    def always_invalid(
        ai_reading,
        *,
        reading_context,
        consultation_context=None,
    ):
        nonlocal quality_count
        quality_count += 1
        return invalid

    def fake_repair(
        ai_reading,
        quality_report,
        *,
        reading_context,
        consultation_context=None,
        client=None,
        model=None,
        max_output_tokens=None,
        reasoning_effort=None,
        store=None,
    ):
        nonlocal repair_count
        repair_count += 1

        return ReadingRepairResult(
            original=deepcopy(ai_reading),
            repaired=deepcopy(ai_reading),
            issue_count=1,
            error_count=1,
            warning_count=0,
            repaired_issue_codes=(
                "health_astrology_specific_overreach",
            ),
            response_id=(
                f"resp_repair_exhaust_{repair_count:03d}"
            ),
            response_status="completed",
            model=model or "gpt-5",
            usage={},
        )

    monkeypatch.setattr(
        script_module,
        "validate_customer_facing_reading",
        always_invalid,
    )
    monkeypatch.setattr(
        script_module,
        "repair_reading",
        fake_repair,
    )

    with pytest.raises(
        ReadingQualityError
    ):
        script_module.generate_customer_reading(
            sample_intake
        )

    # 初回 + Repair#1後 + Repair#2後。
    assert quality_count == 3

    # 最大2回で停止。
    assert (
        repair_count
        == script_module.MAX_REPAIR_ATTEMPTS
    )
