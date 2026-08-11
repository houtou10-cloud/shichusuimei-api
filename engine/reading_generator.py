"""
engine/reading_generator.py

四柱推命 AI鑑定文生成エンジン v1

目的
----
reading_context_v1
    ↓
reading_prompt_v1
    ↓
OpenAI Responses API
    ↓
鑑定文 / 構造化JSON

というAI生成パイプラインを担当する。

このモジュールは占術計算を行わない。
四柱・日主・身強身弱・格局・用神・大運・歳運・統合運は、
engine.reading_context / engine.reading_prompt が渡した
既存の計算済みデータを事実として扱う。

重要な設計方針
--------------
1. 占術計算を再実行しない。
2. AIへ渡すpromptは reading_prompt.py だけで生成する。
3. OpenAI API呼び出し部分をこのモジュールへ隔離する。
4. APIキーをコードへ埋め込まない。
5. OPENAI_API_KEY は環境変数または注入clientから利用する。
6. model名も環境変数で差し替え可能にする。
7. Responses APIを使用する。
8. デフォルトで store=False とし、不要な保存を避ける。
9. text / json の両出力に対応する。
10. JSON出力時はJSON SchemaをResponses APIへ渡す。
11. API responseの生オブジェクトを外部へそのまま公開しない。
12. AIが返したJSONは必ずparseして検証可能な形にする。
13. テストではclientを注入できるようにする。
14. OpenAI SDKが未インストールでもimport時には落とさない。
15. API通信エラーを本モジュール固有の例外へ変換する。

主な公開API
------------
- get_default_model()
- create_openai_client()
- build_generation_payload()
- generate_reading()
- generate_reading_text()
- generate_reading_json()
- generate_reading_from_context()
- calculate_ai_reading()
- get_reading_generator_metadata()

注意
----
このファイルをimportしただけではOpenAI APIへ接続しない。
API通信は generate_reading() 系関数を明示的に呼んだ場合のみ行う。

Version
-------
reading_generator_v1
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


from engine.reading_prompt import (
    DEFAULT_LANGUAGE,
    DEFAULT_READING_SECTIONS,
    DEFAULT_TONE,
    SUPPORTED_OUTPUT_FORMATS,
    build_reading_request,
)


# ============================================================
# Constants
# ============================================================


READING_GENERATOR_VERSION = "reading_generator_v1"
READING_GENERATOR_METHOD = "openai_responses_api_v1"
READING_GENERATOR_STATUS = "ai_generation_ready"

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_READING_MODEL_ENV = "OPENAI_READING_MODEL"

# 公式QuickstartでResponses APIの例として利用されているモデル名。
# 実運用では OPENAI_READING_MODEL で差し替えることを推奨する。
DEFAULT_OPENAI_MODEL = "gpt-5"

DEFAULT_MAX_OUTPUT_TOKENS = 6000

DEFAULT_STORE = False

JSON_SCHEMA_NAME = "shichusuimei_reading"

SUPPORTED_GENERATION_OUTPUT_FORMATS = (
    "text",
    "json",
)


# ============================================================
# Exceptions
# ============================================================


class ReadingGeneratorError(Exception):
    """
    reading_generator.py の基底例外。
    """


class ReadingGeneratorConfigurationError(
    ReadingGeneratorError
):
    """
    APIキー・model・SDKなど設定系の例外。
    """


class ReadingGeneratorRequestError(
    ReadingGeneratorError
):
    """
    OpenAI APIへのrequest失敗。
    """


class ReadingGeneratorResponseError(
    ReadingGeneratorError
):
    """
    OpenAI APIからのresponseが不正。
    """


class ReadingGeneratorJSONError(
    ReadingGeneratorResponseError
):
    """
    JSON鑑定結果のparse失敗。
    """


# ============================================================
# Result model
# ============================================================


@dataclass(frozen=True)
class ReadingGenerationResult:
    """
    AI鑑定生成結果。

    外部SDKのresponse objectをそのまま返さず、
    アプリ側で利用する情報だけへ正規化する。
    """

    output_format: str
    model: str
    text: str
    parsed: Optional[Dict[str, Any]]
    response_id: Optional[str]
    response_status: Optional[str]
    usage: Dict[str, Any]
    sections: Tuple[str, ...]
    method: str = READING_GENERATOR_METHOD
    status: str = "completed"

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        """
        JSON化しやすいdictへ変換する。
        """

        return {
            "output_format": (
                self.output_format
            ),
            "model": self.model,
            "text": self.text,
            "parsed": deepcopy(
                self.parsed
            ),
            "response_id": (
                self.response_id
            ),
            "response_status": (
                self.response_status
            ),
            "usage": deepcopy(
                self.usage
            ),
            "sections": list(
                self.sections
            ),
            "method": self.method,
            "status": self.status,
        }


# ============================================================
# Generic validation
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    """
    Mapping型を検証する。
    """

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はdict型で指定してください。"
        )

    return value


def _require_bool(
    value: Any,
    name: str,
) -> bool:
    """
    bool型を検証する。
    """

    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(
            f"{name}はbool型で指定してください。"
        )

    return value


def _require_positive_int(
    value: Any,
    name: str,
) -> int:
    """
    正の整数を検証する。
    """

    if (
        not isinstance(
            value,
            int,
        )
        or isinstance(
            value,
            bool,
        )
    ):
        raise TypeError(
            f"{name}は整数で指定してください。"
        )

    if value <= 0:
        raise ValueError(
            f"{name}は1以上で指定してください。"
        )

    return value


def _non_empty_string(
    value: Any,
    name: str,
) -> str:
    """
    空でない文字列を検証する。
    """

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列で指定してください。"
        )

    stripped = value.strip()

    if not stripped:
        raise ValueError(
            f"{name}は空文字にできません。"
        )

    return stripped


def _normalize_output_format(
    output_format: str,
) -> str:
    """
    出力形式を検証する。
    """

    output_format = (
        _non_empty_string(
            output_format,
            "output_format",
        )
    )

    if output_format not in (
        SUPPORTED_GENERATION_OUTPUT_FORMATS
    ):
        raise ValueError(
            "output_formatはtextまたはjsonで指定してください。"
        )

    return output_format


def _normalize_sections(
    sections: Optional[
        Sequence[str]
    ],
) -> Tuple[str, ...]:
    """
    reading_prompt側と同じセクション契約を検証する。
    """

    if sections is None:
        return tuple(
            DEFAULT_READING_SECTIONS
        )

    if isinstance(
        sections,
        str,
    ):
        raise TypeError(
            "sectionsは文字列ではなく"
            "文字列の配列で指定してください。"
        )

    if not isinstance(
        sections,
        Sequence,
    ):
        raise TypeError(
            "sectionsは配列で指定してください。"
        )

    normalized: List[str] = []

    for section in sections:
        if not isinstance(
            section,
            str,
        ):
            raise TypeError(
                "sectionsの各要素は文字列で指定してください。"
            )

        section = section.strip()

        if not section:
            raise ValueError(
                "sectionsに空文字は指定できません。"
            )

        if section not in (
            DEFAULT_READING_SECTIONS
        ):
            raise ValueError(
                f"未対応の鑑定セクションです: {section}"
            )

        if section not in normalized:
            normalized.append(
                section
            )

    if not normalized:
        raise ValueError(
            "sectionsには1件以上指定してください。"
        )

    return tuple(
        normalized
    )


# ============================================================
# Environment / model
# ============================================================


def get_default_model() -> str:
    """
    AI鑑定に使用するmodel名を返す。

    優先順位
    ----------
    1. OPENAI_READING_MODEL
    2. DEFAULT_OPENAI_MODEL
    """

    env_model = os.getenv(
        OPENAI_READING_MODEL_ENV
    )

    if isinstance(
        env_model,
        str,
    ):
        env_model = (
            env_model.strip()
        )

        if env_model:
            return env_model

    return DEFAULT_OPENAI_MODEL


def resolve_model(
    model: Optional[str] = None,
) -> str:
    """
    明示modelまたは環境変数からmodelを決定する。
    """

    if model is None:
        return get_default_model()

    return _non_empty_string(
        model,
        "model",
    )


def has_openai_api_key() -> bool:
    """
    OPENAI_API_KEY が存在するか確認する。

    APIキーそのものは返さない。
    """

    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    return bool(
        isinstance(
            api_key,
            str,
        )
        and api_key.strip()
    )


# ============================================================
# OpenAI client
# ============================================================


def create_openai_client(
    *,
    api_key: Optional[str] = None,
) -> Any:
    """
    OpenAI Python SDK clientを生成する。

    Parameters
    ----------
    api_key:
        明示的に指定するAPIキー。
        NoneならOPENAI_API_KEYをSDKへ任せる。

    Notes
    -----
    importを関数内で行うことで、
    テスト・計算エンジン利用時に
    OpenAI SDKを必須にしない。
    """

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise (
            ReadingGeneratorConfigurationError(
                "OpenAI Python SDKが"
                "インストールされていません。"
                "requirements.txtにopenaiを追加してください。"
            )
        ) from exc

    if api_key is not None:
        api_key = _non_empty_string(
            api_key,
            "api_key",
        )

        return OpenAI(
            api_key=api_key
        )

    # SDKはOPENAI_API_KEYを
    # 環境変数から自動取得する。
    try:
        return OpenAI()
    except Exception as exc:
        raise (
            ReadingGeneratorConfigurationError(
                "OpenAI clientを初期化できません。"
                "OPENAI_API_KEYを確認してください。"
            )
        ) from exc


# ============================================================
# JSON Schema normalization
# ============================================================


def _prepare_strict_json_schema(
    schema: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Structured Outputs用に
    object schemaへadditionalProperties=Falseを再帰付与する。

    reading_prompt.py が生成するschemaを変更せず、
    API送信時だけstrict向けに整形する。
    """

    schema = _require_mapping(
        schema,
        "schema",
    )

    def normalize(
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            Mapping,
        ):
            result = {
                str(key): normalize(
                    item
                )
                for key, item
                in value.items()
            }

            if (
                result.get(
                    "type"
                )
                == "object"
            ):
                result[
                    "additionalProperties"
                ] = False

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                normalize(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                normalize(
                    item
                )
                for item in value
            ]

        return deepcopy(value)

    return normalize(
        schema
    )


# ============================================================
# Prompt -> Responses API payload
# ============================================================


def _messages_to_responses_input(
    messages: Sequence[
        Mapping[str, Any]
    ],
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    reading_promptのsystem/user messagesを
    Responses APIのinstructions/inputへ変換する。

    Returns
    -------
    tuple
        (instructions, input_messages)
    """

    if not isinstance(
        messages,
        Sequence,
    ) or isinstance(
        messages,
        str,
    ):
        raise TypeError(
            "messagesは配列で指定してください。"
        )

    if len(
        messages
    ) != 2:
        raise ValueError(
            "messagesはsystem/userの2件である必要があります。"
        )

    system_message = messages[
        0
    ]
    user_message = messages[
        1
    ]

    if not isinstance(
        system_message,
        Mapping,
    ):
        raise TypeError(
            "system messageはdict型である必要があります。"
        )

    if not isinstance(
        user_message,
        Mapping,
    ):
        raise TypeError(
            "user messageはdict型である必要があります。"
        )

    if (
        system_message.get(
            "role"
        )
        != "system"
    ):
        raise ValueError(
            "1件目のmessageはsystemである必要があります。"
        )

    if (
        user_message.get(
            "role"
        )
        != "user"
    ):
        raise ValueError(
            "2件目のmessageはuserである必要があります。"
        )

    instructions = _non_empty_string(
        system_message.get(
            "content"
        ),
        "system message content",
    )

    user_content = _non_empty_string(
        user_message.get(
            "content"
        ),
        "user message content",
    )

    return (
        instructions,
        [
            {
                "role": "user",
                "content": user_content,
            }
        ],
    )


def build_generation_payload(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    output_format: str = "text",
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    store: bool = DEFAULT_STORE,
) -> Dict[str, Any]:
    """
    OpenAI Responses APIへ渡すpayloadを生成する。

    API通信は行わない。
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    output_format = (
        _normalize_output_format(
            output_format
        )
    )

    normalized_sections = (
        _normalize_sections(
            sections
        )
    )

    resolved_model = resolve_model(
        model
    )

    max_output_tokens = (
        _require_positive_int(
            max_output_tokens,
            "max_output_tokens",
        )
    )

    store = _require_bool(
        store,
        "store",
    )

    reading_request = (
        build_reading_request(
            reading_context,
            sections=normalized_sections,
            language=language,
            tone=tone,
            output_format=output_format,
        )
    )

    instructions, input_messages = (
        _messages_to_responses_input(
            reading_request[
                "messages"
            ]
        )
    )

    payload: Dict[str, Any] = {
        "model": resolved_model,
        "instructions": instructions,
        "input": input_messages,
        "max_output_tokens": (
            max_output_tokens
        ),
        "store": store,
    }

    if output_format == "json":
        raw_schema = reading_request[
            "output_schema"
        ]

        if not isinstance(
            raw_schema,
            Mapping,
        ):
            raise (
                ReadingGeneratorConfigurationError(
                    "JSON出力用schemaが"
                    "reading_promptから取得できません。"
                )
            )

        strict_schema = (
            _prepare_strict_json_schema(
                raw_schema
            )
        )

        payload[
            "text"
        ] = {
            "format": {
                "type": "json_schema",
                "name": (
                    JSON_SCHEMA_NAME
                ),
                "schema": strict_schema,
                "strict": True,
            }
        }

    return {
        "payload": payload,
        "reading_request": (
            reading_request
        ),
        "sections": list(
            normalized_sections
        ),
        "output_format": (
            output_format
        ),
        "model": resolved_model,
        "method": (
            READING_GENERATOR_METHOD
        ),
        "status": (
            "request_ready"
        ),
    }


# ============================================================
# Response extraction helpers
# ============================================================


def _get_attribute_or_key(
    value: Any,
    name: str,
    default: Any = None,
) -> Any:
    """
    SDK object / dictの両方から値を取得する。
    """

    if isinstance(
        value,
        Mapping,
    ):
        return value.get(
            name,
            default,
        )

    return getattr(
        value,
        name,
        default,
    )


def _extract_output_text(
    response: Any,
) -> str:
    """
    Responses API responseからoutput_textを取得する。

    SDKのresponse.output_textを第一候補とする。
    テスト用dict responseにも対応する。
    """

    direct = _get_attribute_or_key(
        response,
        "output_text",
    )

    if isinstance(
        direct,
        str,
    ):
        direct = direct.strip()

        if direct:
            return direct

    # fallback:
    # response.output[].content[].text
    output_items = (
        _get_attribute_or_key(
            response,
            "output",
            [],
        )
    )

    if not isinstance(
        output_items,
        (list, tuple),
    ):
        output_items = []

    text_parts: List[str] = []

    for item in output_items:
        content = _get_attribute_or_key(
            item,
            "content",
            [],
        )

        if not isinstance(
            content,
            (list, tuple),
        ):
            continue

        for content_item in content:
            text = _get_attribute_or_key(
                content_item,
                "text",
            )

            if isinstance(
                text,
                str,
            ):
                text = text.strip()

                if text:
                    text_parts.append(
                        text
                    )

    combined = "\n".join(
        text_parts
    ).strip()

    if combined:
        return combined

    raise ReadingGeneratorResponseError(
        "OpenAI responseから"
        "鑑定文章を取得できませんでした。"
    )


def _normalize_usage(
    usage: Any,
) -> Dict[str, Any]:
    """
    Responses API usageを安全なdictへ変換する。
    """

    if usage is None:
        return {}

    if isinstance(
        usage,
        Mapping,
    ):
        return deepcopy(
            dict(usage)
        )

    result: Dict[str, Any] = {}

    for field in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
    ):
        value = getattr(
            usage,
            field,
            None,
        )

        if value is not None:
            result[
                field
            ] = value

    # SDK objectがmodel_dumpを持つ場合は
    # より完全なusageを取得する。
    model_dump = getattr(
        usage,
        "model_dump",
        None,
    )

    if callable(
        model_dump
    ):
        try:
            dumped = model_dump()

            if isinstance(
                dumped,
                Mapping,
            ):
                return deepcopy(
                    dict(dumped)
                )
        except Exception:
            pass

    return result


def _response_metadata(
    response: Any,
) -> Dict[str, Any]:
    """
    responseの公開可能metadataを抽出する。
    """

    return {
        "response_id": (
            _get_attribute_or_key(
                response,
                "id",
            )
        ),
        "response_status": (
            _get_attribute_or_key(
                response,
                "status",
            )
        ),
        "usage": _normalize_usage(
            _get_attribute_or_key(
                response,
                "usage",
            )
        ),
    }


# ============================================================
# JSON parsing / validation
# ============================================================


def parse_reading_json(
    text: str,
) -> Dict[str, Any]:
    """
    AIが返したJSON文字列をparseする。
    """

    text = _non_empty_string(
        text,
        "text",
    )

    try:
        parsed = json.loads(
            text
        )
    except json.JSONDecodeError as exc:
        raise ReadingGeneratorJSONError(
            "AIが返した鑑定結果を"
            "JSONとして解析できませんでした。"
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise ReadingGeneratorJSONError(
            "AI鑑定JSONの最上位は"
            "objectである必要があります。"
        )

    return parsed


def validate_generated_reading_json(
    parsed: Mapping[str, Any],
    *,
    sections: Optional[
        Sequence[str]
    ] = None,
) -> Dict[str, Any]:
    """
    生成済み鑑定JSONのアプリ側最低限validation。

    Structured Outputsでschemaを指定していても、
    アプリ境界でも重要項目を確認する。
    """

    parsed = _require_mapping(
        parsed,
        "parsed",
    )

    normalized_sections = (
        _normalize_sections(
            sections
        )
    )

    required_top_level = (
        "summary",
        "sections",
        "disclaimer",
    )

    missing_top = [
        key
        for key
        in required_top_level
        if key not in parsed
    ]

    if missing_top:
        raise ReadingGeneratorJSONError(
            "AI鑑定JSONに必要なキーがありません: "
            + ", ".join(
                missing_top
            )
        )

    summary = parsed.get(
        "summary"
    )

    if not isinstance(
        summary,
        str,
    ) or not summary.strip():
        raise ReadingGeneratorJSONError(
            "AI鑑定JSONのsummaryが不正です。"
        )

    disclaimer = parsed.get(
        "disclaimer"
    )

    if not isinstance(
        disclaimer,
        str,
    ) or not disclaimer.strip():
        raise ReadingGeneratorJSONError(
            "AI鑑定JSONのdisclaimerが不正です。"
        )

    result_sections = parsed.get(
        "sections"
    )

    if not isinstance(
        result_sections,
        Mapping,
    ):
        raise ReadingGeneratorJSONError(
            "AI鑑定JSONのsectionsが不正です。"
        )

    missing_sections = [
        section
        for section
        in normalized_sections
        if section not in result_sections
    ]

    if missing_sections:
        raise ReadingGeneratorJSONError(
            "AI鑑定JSONに必要なsectionがありません: "
            + ", ".join(
                missing_sections
            )
        )

    required_section_fields = (
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    )

    for section in normalized_sections:
        section_data = (
            result_sections[
                section
            ]
        )

        if not isinstance(
            section_data,
            Mapping,
        ):
            raise ReadingGeneratorJSONError(
                f"{section} sectionが"
                "objectではありません。"
            )

        missing_fields = [
            key
            for key
            in required_section_fields
            if key not in section_data
        ]

        if missing_fields:
            raise ReadingGeneratorJSONError(
                f"{section} sectionに"
                "必要なキーがありません: "
                + ", ".join(
                    missing_fields
                )
            )

        for text_field in (
            "title",
            "summary",
            "detail",
        ):
            value = section_data.get(
                text_field
            )

            if not isinstance(
                value,
                str,
            ):
                raise ReadingGeneratorJSONError(
                    f"{section}.{text_field}"
                    "は文字列である必要があります。"
                )

        for list_field in (
            "evidence",
            "advice",
        ):
            value = section_data.get(
                list_field
            )

            if not isinstance(
                value,
                list,
            ):
                raise ReadingGeneratorJSONError(
                    f"{section}.{list_field}"
                    "は配列である必要があります。"
                )

            if not all(
                isinstance(
                    item,
                    str,
                )
                for item in value
            ):
                raise ReadingGeneratorJSONError(
                    f"{section}.{list_field}"
                    "の各要素は文字列である必要があります。"
                )

    return {
        "valid": True,
        "sections": list(
            normalized_sections
        ),
        "section_count": len(
            normalized_sections
        ),
        "method": (
            "reading_json_validation_v1"
        ),
    }


# ============================================================
# API execution
# ============================================================


def _execute_responses_create(
    client: Any,
    payload: Mapping[
        str,
        Any,
    ],
) -> Any:
    """
    client.responses.create() を呼び出す。

    client注入によりunit testでmock可能。
    """

    if client is None:
        raise ReadingGeneratorConfigurationError(
            "clientが指定されていません。"
        )

    responses = getattr(
        client,
        "responses",
        None,
    )

    if responses is None:
        raise ReadingGeneratorConfigurationError(
            "clientにresponses APIがありません。"
        )

    create = getattr(
        responses,
        "create",
        None,
    )

    if not callable(
        create
    ):
        raise ReadingGeneratorConfigurationError(
            "client.responses.createが利用できません。"
        )

    try:
        return create(
            **dict(
                payload
            )
        )
    except Exception as exc:

        raise ReadingGeneratorRequestError(
            "OpenAI Responses APIによる"
            "鑑定文生成に失敗しました。 "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def generate_reading(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    output_format: str = "json",
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    store: bool = DEFAULT_STORE,
) -> ReadingGenerationResult:
    """
    reading_contextからAI鑑定文を生成する。

    Parameters
    ----------
    reading_context:
        reading_context_v1。

    client:
        OpenAI client。
        Noneならcreate_openai_client()で生成する。
        テスト時はfake clientを注入可能。

    api_key:
        client=None時のみ利用する明示APIキー。
        通常はOPENAI_API_KEY環境変数を推奨。

    model:
        OpenAI model名。
        NoneならOPENAI_READING_MODEL、
        未設定ならDEFAULT_OPENAI_MODEL。

    sections:
        鑑定対象セクション。

    language:
        reading_promptへ渡す言語設定。

    tone:
        reading_promptへ渡す文章トーン。

    output_format:
        "text" または "json"。
        PDF工程を考慮し、デフォルトはjson。

    max_output_tokens:
        最大出力token数。

    store:
        Responses APIのstore。
        デフォルトFalse。

    Returns
    -------
    ReadingGenerationResult
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    output_format = (
        _normalize_output_format(
            output_format
        )
    )

    normalized_sections = (
        _normalize_sections(
            sections
        )
    )

    generation = (
        build_generation_payload(
            reading_context,
            model=model,
            sections=normalized_sections,
            language=language,
            tone=tone,
            output_format=output_format,
            max_output_tokens=(
                max_output_tokens
            ),
            store=store,
        )
    )

    if client is None:
        client = create_openai_client(
            api_key=api_key
        )

    response = (
        _execute_responses_create(
            client,
            generation[
                "payload"
            ],
        )
    )

    text = _extract_output_text(
        response
    )

    parsed: Optional[
        Dict[str, Any]
    ] = None

    if output_format == "json":
        parsed = parse_reading_json(
            text
        )

        validate_generated_reading_json(
            parsed,
            sections=normalized_sections,
        )

    metadata = _response_metadata(
        response
    )

    response_status = metadata[
        "response_status"
    ]

    # Responses APIの完了状態以外でも
    # output_textが存在するケースを考慮して
    # responseのstatusを記録しつつ結果は返す。
    result_status = (
        "completed"
        if response_status in (
            None,
            "completed",
        )
        else str(
            response_status
        )
    )

    return ReadingGenerationResult(
        output_format=output_format,
        model=generation[
            "model"
        ],
        text=text,
        parsed=parsed,
        response_id=metadata[
            "response_id"
        ],
        response_status=(
            response_status
        ),
        usage=metadata[
            "usage"
        ],
        sections=tuple(
            normalized_sections
        ),
        method=(
            READING_GENERATOR_METHOD
        ),
        status=result_status,
    )


# ============================================================
# Convenience APIs
# ============================================================


def generate_reading_text(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    store: bool = DEFAULT_STORE,
) -> str:
    """
    AI鑑定を通常文章で生成し、
    textだけを返す。
    """

    result = generate_reading(
        reading_context,
        client=client,
        api_key=api_key,
        model=model,
        sections=sections,
        language=language,
        tone=tone,
        output_format="text",
        max_output_tokens=(
            max_output_tokens
        ),
        store=store,
    )

    return result.text


def generate_reading_json(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    store: bool = DEFAULT_STORE,
) -> Dict[str, Any]:
    """
    AI鑑定をJSONで生成し、
    parse済みdictだけを返す。
    """

    result = generate_reading(
        reading_context,
        client=client,
        api_key=api_key,
        model=model,
        sections=sections,
        language=language,
        tone=tone,
        output_format="json",
        max_output_tokens=(
            max_output_tokens
        ),
        store=store,
    )

    if result.parsed is None:
        raise ReadingGeneratorResponseError(
            "JSON鑑定結果が取得できませんでした。"
        )

    return deepcopy(
        result.parsed
    )


def generate_reading_from_context(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    API / service layer向けのdict返却API。
    """

    result = generate_reading(
        reading_context,
        client=client,
        api_key=api_key,
        model=model,
        sections=sections,
        output_format=output_format,
    )

    return result.to_dict()


def calculate_ai_reading(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    generate_reading_from_context() の互換alias。
    """

    return generate_reading_from_context(
        reading_context,
        client=client,
        api_key=api_key,
        model=model,
        sections=sections,
        output_format=output_format,
    )


def prepare_ai_generation_payload(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    API通信を行わずpayloadだけ生成するalias。

    CIテストやデバッグで利用する。
    """

    return build_generation_payload(
        reading_context,
        model=model,
        sections=sections,
        output_format=output_format,
    )


# ============================================================
# Metadata
# ============================================================


def get_reading_generator_metadata() -> Dict[str, Any]:
    """
    AI鑑定生成エンジンのmetadataを返す。

    APIキーは絶対に含めない。
    """

    return {
        "version": (
            READING_GENERATOR_VERSION
        ),
        "method": (
            READING_GENERATOR_METHOD
        ),
        "status": (
            READING_GENERATOR_STATUS
        ),
        "api": (
            "OpenAI Responses API"
        ),
        "default_model": (
            get_default_model()
        ),
        "model_env": (
            OPENAI_READING_MODEL_ENV
        ),
        "api_key_env": (
            OPENAI_API_KEY_ENV
        ),
        "api_key_configured": (
            has_openai_api_key()
        ),
        "default_output_format": (
            "json"
        ),
        "supported_output_formats": list(
            SUPPORTED_GENERATION_OUTPUT_FORMATS
        ),
        "default_max_output_tokens": (
            DEFAULT_MAX_OUTPUT_TOKENS
        ),
        "default_store": (
            DEFAULT_STORE
        ),
        "json_schema_name": (
            JSON_SCHEMA_NAME
        ),
        "recalculates_astrology": False,
    }


# ============================================================
# Public API
# ============================================================


__all__ = [
    "READING_GENERATOR_VERSION",
    "READING_GENERATOR_METHOD",
    "READING_GENERATOR_STATUS",
    "OPENAI_API_KEY_ENV",
    "OPENAI_READING_MODEL_ENV",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_STORE",
    "JSON_SCHEMA_NAME",
    "SUPPORTED_GENERATION_OUTPUT_FORMATS",
    "ReadingGeneratorError",
    "ReadingGeneratorConfigurationError",
    "ReadingGeneratorRequestError",
    "ReadingGeneratorResponseError",
    "ReadingGeneratorJSONError",
    "ReadingGenerationResult",
    "get_default_model",
    "resolve_model",
    "has_openai_api_key",
    "create_openai_client",
    "build_generation_payload",
    "parse_reading_json",
    "validate_generated_reading_json",
    "generate_reading",
    "generate_reading_text",
    "generate_reading_json",
    "generate_reading_from_context",
    "calculate_ai_reading",
    "prepare_ai_generation_payload",
    "get_reading_generator_metadata",
]
