"""
api/reading_routes.py

四柱推命 AI鑑定 API v2

POST /reading
GET  /reading/status

処理フロー
----------
request
    ↓
calculate_chart()
    ↓
build_reading_context()
    ↓
generate_reading()
    ↓
OpenAI Responses API
    ↓
AI鑑定結果
    ↓
JSON response

設計方針
--------
・四柱推命の計算はAIに行わせない
・命式計算は engine.chart が担当する
・AI用データ整形は engine.reading_context が担当する
・プロンプト生成は engine.reading_prompt が担当する
・OpenAI呼び出しは engine.reading_generator が担当する
・API層では各エンジンを接続するだけにする
・OPENAI_API_KEYそのものはレスポンスへ出さない
・section名は reading_prompt / reading_generator の正式契約へ統一する
・AI生成結果のtext属性は ReadingGenerationResult.text を使用する

Version
-------
reading_api_v2
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import (
    BaseModel,
    Field,
)

from engine.chart import (
    calculate_chart,
)
from engine.reading_context import (
    build_reading_context,
)
from engine.reading_generator import (
    ReadingGenerationResult,
    ReadingGeneratorConfigurationError,
    ReadingGeneratorError,
    ReadingGeneratorJSONError,
    ReadingGeneratorRequestError,
    ReadingGeneratorResponseError,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)
from engine.reading_prompt import (
    DEFAULT_READING_SECTIONS,
    SUPPORTED_OUTPUT_FORMATS,
    SUPPORTED_TONES,
)


# ============================================================
# Router
# ============================================================


router = APIRouter(
    tags=[
        "reading",
    ],
)


# ============================================================
# Constants
# ============================================================


READING_API_VERSION = "reading_api_v1"

# reading_prompt / reading_generator と
# 同一契約を使用する。
DEFAULT_SECTIONS = tuple(
    DEFAULT_READING_SECTIONS
)

ALLOWED_SECTIONS = set(
    DEFAULT_READING_SECTIONS
)

ALLOWED_TONES = set(
    SUPPORTED_TONES
)

ALLOWED_OUTPUT_FORMATS = set(
    SUPPORTED_OUTPUT_FORMATS
)


# ============================================================
# Request models
# ============================================================


class ReadingRequest(
    BaseModel
):
    """
    AI鑑定APIへの入力。
    """

    birth_date: str = Field(
        ...,
        description=(
            "生年月日。"
            "YYYY-MM-DD形式。"
        ),
        examples=[
            "1985-07-17",
        ],
    )

    birth_time: str = Field(
        ...,
        description=(
            "出生時刻。"
            "HH:MM形式。"
        ),
        examples=[
            "21:50",
        ],
    )

    birth_place: str = Field(
        ...,
        description=(
            "出生地。"
        ),
        examples=[
            "石川県",
        ],
    )

    gender: str = Field(
        ...,
        description=(
            "性別。"
            "既存chartエンジンへそのまま渡す。"
        ),
        examples=[
            "female",
        ],
    )

    target_datetime: datetime | None = Field(
        default=None,
        description=(
            "現在運・歳運等の基準日時。"
            "省略時はchart側の"
            "デフォルト動作を使用する。"
        ),
    )

    sections: list[str] | None = Field(
        default=None,
        description=(
            "生成する鑑定セクション。"
            "指定可能: "
            "core_personality, career, wealth, "
            "relationships, health, current_luck, "
            "future_flow, advice"
        ),
        examples=[
            [
                "core_personality",
                "career",
                "wealth",
            ]
        ],
    )

    tone: str = Field(
        default="professional_warm",
        description=(
            "鑑定文のトーン。"
        ),
    )

    output_format: Literal[
        "text",
        "json",
    ] = Field(
        default="json",
        description=(
            "AI鑑定結果の出力形式。"
        ),
    )

    model: str | None = Field(
        default=None,
        description=(
            "OpenAIモデル。"
            "省略時はreading_generatorの"
            "デフォルトモデルを使用する。"
        ),
    )

    max_output_tokens: int = Field(
        default=4000,
        ge=256,
        le=16000,
        description=(
            "OpenAI出力トークン上限。"
        ),
    )

    store: bool = Field(
        default=False,
        description=(
            "OpenAI Responses APIの"
            "store設定。"
            "デフォルトFalse。"
        ),
    )


# ============================================================
# Response models
# ============================================================


class ReadingErrorResponse(
    BaseModel
):
    """
    エラーレスポンス。
    """

    status: str

    error: str

    detail: str | None = None


class ReadingResponse(
    BaseModel
):
    """
    AI鑑定APIレスポンス。
    """

    api_version: str

    status: str

    model: str

    response_id: str | None = None

    response_status: str | None = None

    output_format: str

    sections: list[str]

    reading: Any

    usage: dict[str, Any]

    calculation: dict[str, Any] | None = None


# ============================================================
# Validation helpers
# ============================================================


def _normalize_sections(
    sections: list[str] | None,
) -> tuple[str, ...]:
    """
    sectionsを検証・正規化する。

    Noneの場合はreading_promptと同じ
    8セクションを使用する。
    """

    if sections is None:
        return DEFAULT_SECTIONS

    if not isinstance(
        sections,
        list,
    ):
        raise ValueError(
            "sectionsはlistで指定してください。"
        )

    if not sections:
        raise ValueError(
            "sectionsを1件以上指定してください。"
        )

    normalized: list[str] = []

    for section in sections:

        if not isinstance(
            section,
            str,
        ):
            raise ValueError(
                "sectionsの各要素は"
                "文字列で指定してください。"
            )

        value = section.strip()

        if not value:
            raise ValueError(
                "空のsectionは指定できません。"
            )

        if (
            value
            not in ALLOWED_SECTIONS
        ):
            raise ValueError(
                "未対応のsectionです: "
                f"{value}"
            )

        if (
            value
            not in normalized
        ):
            normalized.append(
                value
            )

    return tuple(
        normalized
    )


def _validate_tone(
    tone: str,
) -> str:
    """
    toneを検証する。
    """

    if not isinstance(
        tone,
        str,
    ):
        raise ValueError(
            "toneは文字列で指定してください。"
        )

    normalized = tone.strip()

    if not normalized:
        raise ValueError(
            "toneは空文字にできません。"
        )

    if (
        normalized
        not in ALLOWED_TONES
    ):
        raise ValueError(
            "未対応のtoneです: "
            f"{normalized}"
        )

    return normalized


def _validate_output_format(
    output_format: str,
) -> str:
    """
    output_formatを検証する。
    """

    if not isinstance(
        output_format,
        str,
    ):
        raise ValueError(
            "output_formatは文字列で指定してください。"
        )

    normalized = (
        output_format.strip()
    )

    if (
        normalized
        not in ALLOWED_OUTPUT_FORMATS
    ):
        raise ValueError(
            "未対応のoutput_formatです: "
            f"{normalized}"
        )

    return normalized


def _resolve_model(
    model: str | None,
) -> str:
    """
    requestのmodelまたは
    generatorのdefault modelを返す。
    """

    if model is None:
        return get_default_model()

    if not isinstance(
        model,
        str,
    ):
        raise ValueError(
            "modelは文字列で指定してください。"
        )

    normalized = model.strip()

    if not normalized:
        return get_default_model()

    return normalized


# ============================================================
# Chart request adapter
# ============================================================


class _ChartRequest:
    """
    calculate_chart()へ渡す
    最小リクエストオブジェクト。

    engine.chart側へ
    FastAPI/Pydantic依存を持ち込まないための
    adapter。
    """

    def __init__(
        self,
        *,
        birth_date: str,
        birth_time: str,
        birth_place: str,
        gender: str,
    ) -> None:

        self.birth_date = (
            birth_date
        )

        self.birth_time = (
            birth_time
        )

        self.birth_place = (
            birth_place
        )

        self.gender = (
            gender
        )


def _build_chart_request(
    request: ReadingRequest,
) -> _ChartRequest:
    """
    ReadingRequestから
    calculate_chart()用オブジェクトを作る。
    """

    return _ChartRequest(
        birth_date=(
            request.birth_date
        ),
        birth_time=(
            request.birth_time
        ),
        birth_place=(
            request.birth_place
        ),
        gender=(
            request.gender
        ),
    )


# ============================================================
# Chart calculation
# ============================================================


def _calculate_chart_for_reading(
    request: ReadingRequest,
) -> dict[str, Any]:
    """
    AI鑑定用の命式を計算する。
    """

    chart_request = (
        _build_chart_request(
            request
        )
    )

    if (
        request.target_datetime
        is None
    ):
        return calculate_chart(
            chart_request
        )

    return calculate_chart(
        chart_request,
        target_datetime=(
            request.target_datetime
        ),
    )


# ============================================================
# Generation result conversion
# ============================================================


def _extract_reading(
    result: ReadingGenerationResult,
) -> Any:
    """
    ReadingGenerationResultから
    クライアントへ返す鑑定本文を取得する。

    JSON:
        result.parsed

    text:
        result.text
    """

    if (
        result.output_format
        == "json"
    ):
        return result.parsed

    return result.text


def _build_response(
    *,
    chart_result: dict[str, Any],
    generation_result: ReadingGenerationResult,
) -> ReadingResponse:
    """
    APIレスポンスを構築する。
    """

    reading = _extract_reading(
        generation_result
    )

    return ReadingResponse(
        api_version=(
            READING_API_VERSION
        ),
        status=(
            generation_result.status
        ),
        model=(
            generation_result.model
        ),
        response_id=(
            generation_result.response_id
        ),
        response_status=(
            generation_result.response_status
        ),
        output_format=(
            generation_result.output_format
        ),
        sections=list(
            generation_result.sections
        ),
        reading=reading,
        usage=dict(
            generation_result.usage
        ),
        calculation=(
            chart_result
        ),
    )


# ============================================================
# Health / capability
# ============================================================


@router.get(
    "/reading/status",
    operation_id=(
        "getReadingStatus"
    ),
)
def get_reading_status() -> dict:
    """
    AI鑑定APIの利用可能状態を返す。

    APIキーそのものは返さない。
    """

    return {
        "api_version": (
            READING_API_VERSION
        ),
        "status": "ok",
        "openai_configured": (
            has_openai_api_key()
        ),
        "default_model": (
            get_default_model()
        ),
        "supported_sections": (
            sorted(
                ALLOWED_SECTIONS
            )
        ),
        "supported_tones": (
            sorted(
                ALLOWED_TONES
            )
        ),
        "supported_output_formats": (
            sorted(
                ALLOWED_OUTPUT_FORMATS
            )
        ),
    }


# ============================================================
# POST /reading
# ============================================================


@router.post(
    "/reading",
    response_model=ReadingResponse,
    operation_id=(
        "generateShichusuimeiReading"
    ),
    responses={
        400: {
            "model": (
                ReadingErrorResponse
            ),
            "description": (
                "入力値または"
                "鑑定条件が不正"
            ),
        },
        500: {
            "model": (
                ReadingErrorResponse
            ),
            "description": (
                "命式計算または"
                "AI鑑定生成エラー"
            ),
        },
        503: {
            "model": (
                ReadingErrorResponse
            ),
            "description": (
                "OpenAI APIが未設定"
            ),
        },
    },
)
def generate_shichusuimei_reading(
    request: ReadingRequest,
) -> ReadingResponse:
    """
    四柱推命の命式計算から
    AI鑑定生成までを一括実行する。

    AIには命式を再計算させず、
    engine.chartの計算結果のみを
    鑑定材料として使用する。
    """

    # --------------------------------------------------------
    # 1. OpenAI configuration
    # --------------------------------------------------------

    if not has_openai_api_key():

        raise HTTPException(
            status_code=503,
            detail=(
                "OPENAI_API_KEYが"
                "設定されていません。"
            ),
        )

    # --------------------------------------------------------
    # 2. Request validation
    # --------------------------------------------------------

    try:

        sections = (
            _normalize_sections(
                request.sections
            )
        )

        tone = (
            _validate_tone(
                request.tone
            )
        )

        output_format = (
            _validate_output_format(
                request.output_format
            )
        )

        model = (
            _resolve_model(
                request.model
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            ),
        ) from exc

    # --------------------------------------------------------
    # 3. Chart calculation
    # --------------------------------------------------------

    try:

        chart_result = (
            _calculate_chart_for_reading(
                request
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "命式計算入力が不正です: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "命式計算中に"
                "エラーが発生しました。"
            ),
        ) from exc

    # --------------------------------------------------------
    # 4. Reading context
    # --------------------------------------------------------

    try:

        reading_context = (
            build_reading_context(
                chart_result
            )
        )

    except (
        TypeError,
        ValueError,
        KeyError,
    ) as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定コンテキストの"
                "構築に失敗しました: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定コンテキストの"
                "構築中に予期しない"
                "エラーが発生しました。"
            ),
        ) from exc

    # --------------------------------------------------------
    # 5. AI generation
    # --------------------------------------------------------

    try:

        generation_result = (
            generate_reading(
                reading_context,
                model=model,
                sections=sections,
                tone=tone,
                output_format=(
                    output_format
                ),
                max_output_tokens=(
                    request.max_output_tokens
                ),
                store=(
                    request.store
                ),
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=(
                "AI鑑定生成条件が"
                "不正です: "
                f"{exc}"
            ),
        ) from exc

    except ReadingGeneratorConfigurationError as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "AI鑑定生成環境が"
                "利用できません: "
                f"{exc}"
            ),
        ) from exc

    except (
        ReadingGeneratorRequestError,
        ReadingGeneratorResponseError,
        ReadingGeneratorJSONError,
        ReadingGeneratorError,
    ) as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定生成中に"
                "エラーが発生しました: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定生成中に"
                "エラーが発生しました。"
            ),
        ) from exc

    # --------------------------------------------------------
    # 6. Generation status
    # --------------------------------------------------------

    if (
        generation_result.status
        != "completed"
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定が正常完了"
                "しませんでした。"
                " status="
                f"{generation_result.status}"
            ),
        )

    # --------------------------------------------------------
    # 7. Validate generated reading
    # --------------------------------------------------------

    reading = _extract_reading(
        generation_result
    )

    if reading is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定結果が"
                "空でした。"
            ),
        )

    if (
        isinstance(
            reading,
            str,
        )
        and not reading.strip()
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定結果が"
                "空文字でした。"
            ),
        )

    if (
        output_format
        == "json"
        and not isinstance(
            reading,
            dict,
        )
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "AI鑑定JSONが"
                "取得できませんでした。"
            ),
        )

    # --------------------------------------------------------
    # 8. Response
    # --------------------------------------------------------

    return _build_response(
        chart_result=(
            chart_result
        ),
        generation_result=(
            generation_result
        ),
    )


# ============================================================
# Public API
# ============================================================


__all__ = [
    "READING_API_VERSION",
    "DEFAULT_SECTIONS",
    "ALLOWED_SECTIONS",
    "ALLOWED_TONES",
    "ALLOWED_OUTPUT_FORMATS",
    "ReadingRequest",
    "ReadingResponse",
    "ReadingErrorResponse",
    "get_reading_status",
    "generate_shichusuimei_reading",
    "router",
]
