"""
engine/reading_decade_luck.py

四柱推命鑑定書 v1.1
大運（10年運）AI鑑定生成レイヤー。

目的
----
既存の8セクション鑑定生成を変更せず、
現在大運＋未来4大運について、
独立したAI鑑定を生成する。

重要方針
--------
- 大運を再計算しない。
- 干支をAIに決めさせない。
- 開始年齢・終了年齢をAIに決めさせない。
- 通変星・五行をAIに決めさせない。
- AIは文章解釈だけを担当する。
- エンジン計算値を最終結果へ再結合する。
- 既存 reading_generator の Responses API helper を利用する。
"""

from __future__ import annotations

import json

from copy import deepcopy
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)


from engine.reading_generator import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
    _execute_responses_create,
    _extract_output_text,
    _prepare_strict_json_schema,
    _raise_if_unusable_response,
    _response_metadata,
    create_openai_client,
    resolve_model,
)


# ============================================================
# Metadata
# ============================================================


READING_DECADE_LUCK_VERSION = (
    "reading_decade_luck_v1"
)

READING_DECADE_LUCK_METHOD = (
    "ai_decade_luck_interpretation_v1"
)

READING_DECADE_LUCK_STATUS = (
    "ready"
)

JSON_SCHEMA_NAME = (
    "shichusuimei_decade_luck_v1"
)

DEFAULT_PERIOD_COUNT = 5

DEFAULT_DECADE_MAX_OUTPUT_TOKENS = 7000


# ============================================================
# Exceptions
# ============================================================


class ReadingDecadeLuckError(
    Exception
):
    """
    reading_decade_luck 基底例外。
    """


class ReadingDecadeLuckDataError(
    ReadingDecadeLuckError
):
    """
    入力大運データが不足・不正。
    """


class ReadingDecadeLuckResponseError(
    ReadingDecadeLuckError
):
    """
    AIレスポンスが不正。
    """


# ============================================================
# Result
# ============================================================


@dataclass(
    frozen=True
)
class ReadingDecadeLuckResult:
    """
    大運AI鑑定結果。
    """

    overview: str

    periods: Tuple[
        Dict[str, Any],
        ...
    ]

    model: str

    response_id: Optional[str]

    response_status: Optional[str]

    usage: Dict[str, Any]

    version: str = (
        READING_DECADE_LUCK_VERSION
    )

    method: str = (
        READING_DECADE_LUCK_METHOD
    )

    status: str = "completed"

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "overview": self.overview,
            "periods": [
                deepcopy(
                    item
                )
                for item
                in self.periods
            ],
            "generation": {
                "model": self.model,
                "response_id": (
                    self.response_id
                ),
                "response_status": (
                    self.response_status
                ),
                "usage": deepcopy(
                    self.usage
                ),
            },
            "version": self.version,
            "method": self.method,
            "status": self.status,
        }


# ============================================================
# Basic helpers
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はMappingで"
            "指定してください。"
        )

    return value


def _safe_dict(
    value: Any,
) -> Dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return deepcopy(
            dict(
                value
            )
        )

    return {}


def _safe_list(
    value: Any,
) -> List[Any]:
    if isinstance(
        value,
        (list, tuple),
    ):
        return list(
            value
        )

    return []


def _text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def _require_non_empty_text(
    value: Any,
    name: str,
) -> str:
    text = _text(
        value
    )

    if not text:
        raise ReadingDecadeLuckResponseError(
            f"{name}が空です。"
        )

    return text


def _pretty_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# Luck extraction
# ============================================================


def _luck_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    reading_context = (
        _require_mapping(
            reading_context,
            "reading_context",
        )
    )

    return _safe_dict(
        reading_context.get(
            "luck"
        )
    )


def _luck_pillars_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    luck = _luck_context(
        reading_context
    )

    luck_pillars = _safe_dict(
        luck.get(
            "luck_pillars"
        )
    )

    if not luck_pillars:
        raise ReadingDecadeLuckDataError(
            "reading_contextに"
            "luck_pillarsがありません。"
        )

    return luck_pillars


def _current_luck_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    luck = _luck_context(
        reading_context
    )

    return _safe_dict(
        luck.get(
            "current_luck"
        )
    )


def _current_pillar(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    current = _current_luck_context(
        reading_context
    )

    pillar = _safe_dict(
        current.get(
            "current_pillar"
        )
    )

    if not pillar:
        # compatibility
        pillar = _safe_dict(
            current.get(
                "current_luck_pillar"
            )
        )

    return pillar


def _pillar_identity(
    pillar: Mapping[
        str,
        Any,
    ],
) -> Tuple[
    Any,
    str,
]:
    return (
        pillar.get(
            "index"
        ),
        _text(
            pillar.get(
                "ganzhi"
            )
        ),
    )


def select_decade_luck_periods(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    count: int = (
        DEFAULT_PERIOD_COUNT
    ),
) -> List[
    Dict[str, Any]
]:
    """
    現在大運＋未来大運を抽出する。

    基本は5件。
    大運末尾などで未来が不足する場合は、
    利用可能な範囲だけ返す。
    """

    if not isinstance(
        count,
        int,
    ):
        raise TypeError(
            "countはintで指定してください。"
        )

    if count <= 0:
        raise ValueError(
            "countは1以上で"
            "指定してください。"
        )

    luck_pillars = (
        _luck_pillars_context(
            reading_context
        )
    )

    raw_pillars = _safe_list(
        luck_pillars.get(
            "pillars"
        )
    )

    pillars = [
        _safe_dict(
            item
        )
        for item
        in raw_pillars
        if isinstance(
            item,
            Mapping,
        )
    ]

    if not pillars:
        raise ReadingDecadeLuckDataError(
            "大運一覧が空です。"
        )

    current = _current_pillar(
        reading_context
    )

    current_index = current.get(
        "index"
    )

    current_ganzhi = _text(
        current.get(
            "ganzhi"
        )
    )

    start_position: Optional[
        int
    ] = None

    # --------------------------------------------------------
    # 1. index一致を最優先
    # --------------------------------------------------------

    if current_index is not None:
        for position, pillar in enumerate(
            pillars
        ):
            if (
                pillar.get(
                    "index"
                )
                == current_index
            ):
                start_position = (
                    position
                )
                break

    # --------------------------------------------------------
    # 2. ganzhi一致
    # --------------------------------------------------------

    if (
        start_position is None
        and current_ganzhi
    ):
        for position, pillar in enumerate(
            pillars
        ):
            if (
                _text(
                    pillar.get(
                        "ganzhi"
                    )
                )
                == current_ganzhi
            ):
                start_position = (
                    position
                )
                break

    if start_position is None:
        raise ReadingDecadeLuckDataError(
            "現在大運を大運一覧から"
            "特定できませんでした。"
        )

    selected = pillars[
        start_position:
        start_position + count
    ]

    if not selected:
        raise ReadingDecadeLuckDataError(
            "鑑定対象の大運を"
            "取得できませんでした。"
        )

    return deepcopy(
        selected
    )


# ============================================================
# Protected facts
# ============================================================


def build_decade_luck_facts(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    count: int = (
        DEFAULT_PERIOD_COUNT
    ),
) -> Dict[str, Any]:
    """
    AIへ渡す大運事実を作る。

    この値はAIに再計算させない。
    """

    luck_pillars = (
        _luck_pillars_context(
            reading_context
        )
    )

    selected = (
        select_decade_luck_periods(
            reading_context,
            count=count,
        )
    )

    periods = []

    for pillar in selected:
        periods.append(
            {
                "index": pillar.get(
                    "index"
                ),
                "ganzhi": pillar.get(
                    "ganzhi"
                ),
                "stem": pillar.get(
                    "stem"
                ),
                "branch": pillar.get(
                    "branch"
                ),
                "stem_element": (
                    pillar.get(
                        "stem_element"
                    )
                ),
                "branch_element": (
                    pillar.get(
                        "branch_element"
                    )
                ),
                "stem_ten_god": (
                    pillar.get(
                        "stem_ten_god"
                    )
                ),
                "start_age": (
                    pillar.get(
                        "start_age"
                    )
                ),
                "end_age": (
                    pillar.get(
                        "end_age"
                    )
                ),
                "stem_useful_relation": (
                    _safe_dict(
                        pillar.get(
                            "stem_useful_relation"
                        )
                    )
                ),
                "branch_useful_relation": (
                    _safe_dict(
                        pillar.get(
                            "branch_useful_relation"
                        )
                    )
                ),
            }
        )

    return {
        "direction": (
            luck_pillars.get(
                "direction"
            )
        ),
        "direction_japanese": (
            luck_pillars.get(
                "direction_japanese"
            )
        ),
        "start_age": (
            luck_pillars.get(
                "start_age"
            )
        ),
        "period_count": len(
            periods
        ),
        "periods": periods,
    }


# ============================================================
# Context for interpretation
# ============================================================


def build_decade_interpretation_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    大運解釈に必要な命式側情報だけを抽出する。
    """

    reading_context = (
        _require_mapping(
            reading_context,
            "reading_context",
        )
    )

    return {
        "subject": _safe_dict(
            reading_context.get(
                "subject"
            )
        ),
        "day_master": _safe_dict(
            reading_context.get(
                "day_master"
            )
        ),
        "five_elements": _safe_dict(
            reading_context.get(
                "five_elements"
            )
        ),
        "strength": _safe_dict(
            reading_context.get(
                "strength"
            )
        ),
        "pattern": _safe_dict(
            reading_context.get(
                "pattern"
            )
        ),
        "useful_gods": _safe_dict(
            reading_context.get(
                "useful_gods"
            )
        ),
    }


# ============================================================
# JSON schema
# ============================================================


def build_decade_luck_output_schema(
    *,
    period_count: int,
) -> Dict[str, Any]:
    """
    AIが返す文章部分だけのschema。

    干支・年齢・通変星などの
    protected factsはAIに返させない。
    """

    if not isinstance(
        period_count,
        int,
    ):
        raise TypeError(
            "period_countはintで"
            "指定してください。"
        )

    if period_count <= 0:
        raise ValueError(
            "period_countは1以上で"
            "指定してください。"
        )

    return {
        "type": "object",
        "required": [
            "overview",
            "periods",
        ],
        "properties": {
            "overview": {
                "type": "string",
            },
            "periods": {
                "type": "array",
                "minItems": (
                    period_count
                ),
                "maxItems": (
                    period_count
                ),
                "items": {
                    "type": "object",
                    "required": [
                        "index",
                        "title",
                        "theme",
                        "career",
                        "wealth",
                        "relationships",
                        "caution",
                        "advice",
                    ],
                    "properties": {
                        "index": {
                            "type": "integer",
                        },
                        "title": {
                            "type": "string",
                        },
                        "theme": {
                            "type": "string",
                        },
                        "career": {
                            "type": "string",
                        },
                        "wealth": {
                            "type": "string",
                        },
                        "relationships": {
                            "type": "string",
                        },
                        "caution": {
                            "type": "string",
                        },
                        "advice": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 3,
                            "items": {
                                "type": "string",
                            },
                        },
                    },
                },
            },
        },
    }


# ============================================================
# Prompt
# ============================================================


def build_decade_luck_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    count: int = (
        DEFAULT_PERIOD_COUNT
    ),
) -> Dict[str, str]:
    """
    Responses API用 instructions / input を生成。
    """

    facts = build_decade_luck_facts(
        reading_context,
        count=count,
    )

    interpretation_context = (
        build_decade_interpretation_context(
            reading_context
        )
    )

    consultation = (
        _safe_dict(
            consultation_context
        )
        if consultation_context
        is not None
        else {}
    )

    instructions = """
あなたは四柱推命鑑定書の
「大運（10年運）」専用鑑定担当です。

あなたの役割は、
すでに計算済みの大運を
顧客向けの自然な日本語で
解釈することです。

絶対条件:

- 大運を再計算しない。
- 大運の順序を変更しない。
- 大運の干支を変更しない。
- 開始年齢・終了年齢を変更しない。
- 通変星を再計算しない。
- 五行を再計算しない。
- 用神を再判定しない。
- 身強身弱を再判定しない。
- 格局を再判定しない。
- 入力にない具体的な出来事を断定しない。
- 将来を保証しない。
- 医学的診断を行わない。
- 投資利益を保証しない。
- 顧客の相談内容と関係がある場合は、
  自然に鑑定へ反映する。
- 不安を煽る表現を避ける。
- 同じ定型句や同じ語尾を
  機械的に繰り返さない。

大運は
「確定した未来」ではなく、
その10年間で活かしやすいテーマや
注意しやすい傾向として説明してください。

periodsは入力された順序のまま返してください。

indexだけは入力値をそのまま返してください。
干支や年齢などの計算済み事実は
出力JSONへ書かないでください。
最終的にシステム側で結合します。

文章は顧客向けの自然な日本語にしてください。
""".strip()

    input_text = f"""
以下の計算済みデータだけを根拠として、
現在大運から先の大運鑑定を作成してください。

【大運の計算済み事実】

{_pretty_json(facts)}

【命式解釈用データ】

{_pretty_json(interpretation_context)}

【相談情報】

{_pretty_json(consultation)}

【鑑定方針】

overview:
現在から長期的に見た人生の流れを
300〜500字程度でまとめてください。

各period:

title:
その10年間を一言で表す
顧客向けタイトル。

theme:
その10年間の中心テーマを
150〜250字程度。

career:
仕事・社会的役割について
150〜250字程度。

wealth:
金運・収入・資源管理について
150〜250字程度。
投資利益を保証しないこと。

relationships:
人間関係について
120〜220字程度。

caution:
その10年間で注意したいことを
120〜220字程度。

advice:
顧客が実行できる具体策を
2〜3件。

現在大運は「今どう活かすか」を重視し、
未来の大運は
「どんな準備をしておくと活かしやすいか」
という視点も含めてください。

JSON以外は返さないでください。
""".strip()

    return {
        "instructions": (
            instructions
        ),
        "input": input_text,
    }


# ============================================================
# Payload
# ============================================================


def build_decade_luck_payload(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    model: Optional[str] = None,
    count: int = (
        DEFAULT_PERIOD_COUNT
    ),
    max_output_tokens: int = (
        DEFAULT_DECADE_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
) -> Dict[str, Any]:
    """
    OpenAI Responses API payloadを生成する。
    API通信は行わない。
    """

    if not isinstance(
        max_output_tokens,
        int,
    ):
        raise TypeError(
            "max_output_tokensはintで"
            "指定してください。"
        )

    if max_output_tokens <= 0:
        raise ValueError(
            "max_output_tokensは1以上で"
            "指定してください。"
        )

    resolved_model = resolve_model(
        model
    )

    facts = build_decade_luck_facts(
        reading_context,
        count=count,
    )

    period_count = facts[
        "period_count"
    ]

    prompt = build_decade_luck_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        count=count,
    )

    raw_schema = (
        build_decade_luck_output_schema(
            period_count=(
                period_count
            )
        )
    )

    strict_schema = (
        _prepare_strict_json_schema(
            raw_schema
        )
    )

    payload = {
        "model": resolved_model,
        "instructions": (
            prompt[
                "instructions"
            ]
        ),
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": (
                            "input_text"
                        ),
                        "text": (
                            prompt[
                                "input"
                            ]
                        ),
                    }
                ],
            }
        ],
        "max_output_tokens": (
            max_output_tokens
        ),
        "reasoning": {
            "effort": (
                reasoning_effort
            ),
        },
        "store": bool(
            store
        ),
        "text": {
            "format": {
                "type": (
                    "json_schema"
                ),
                "name": (
                    JSON_SCHEMA_NAME
                ),
                "schema": (
                    strict_schema
                ),
                "strict": True,
            }
        },
    }

    return {
        "payload": payload,
        "facts": facts,
        "schema": raw_schema,
        "model": resolved_model,
        "period_count": (
            period_count
        ),
        "method": (
            READING_DECADE_LUCK_METHOD
        ),
        "status": (
            "request_ready"
        ),
    }


# ============================================================
# Parsing
# ============================================================


def parse_decade_luck_json(
    text: Any,
) -> Dict[str, Any]:
    """
    AI JSON文字列をdictへ変換する。
    """

    if not isinstance(
        text,
        str,
    ):
        raise ReadingDecadeLuckResponseError(
            "AI出力が文字列ではありません。"
        )

    stripped = text.strip()

    if not stripped:
        raise ReadingDecadeLuckResponseError(
            "AI出力が空です。"
        )

    try:
        parsed = json.loads(
            stripped
        )
    except json.JSONDecodeError as exc:
        raise ReadingDecadeLuckResponseError(
            "大運AI出力をJSONとして"
            "解析できませんでした。"
            f" {exc}"
        ) from exc

    if not isinstance(
        parsed,
        Mapping,
    ):
        raise ReadingDecadeLuckResponseError(
            "大運AI出力のトップレベルは"
            "objectである必要があります。"
        )

    return deepcopy(
        dict(
            parsed
        )
    )


# ============================================================
# Validation
# ============================================================


def validate_decade_luck_response(
    parsed: Mapping[
        str,
        Any,
    ],
    facts: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    AI出力を検証する。

    index順序を計算済み大運と照合する。
    """

    parsed = _require_mapping(
        parsed,
        "parsed",
    )

    facts = _require_mapping(
        facts,
        "facts",
    )

    overview = (
        _require_non_empty_text(
            parsed.get(
                "overview"
            ),
            "overview",
        )
    )

    raw_periods = parsed.get(
        "periods"
    )

    if not isinstance(
        raw_periods,
        list,
    ):
        raise ReadingDecadeLuckResponseError(
            "periodsはlistで"
            "ある必要があります。"
        )

    expected_periods = _safe_list(
        facts.get(
            "periods"
        )
    )

    if (
        len(
            raw_periods
        )
        != len(
            expected_periods
        )
    ):
        raise ReadingDecadeLuckResponseError(
            "periods件数が"
            "計算済み大運件数と一致しません。"
        )

    required_text_fields = (
        "title",
        "theme",
        "career",
        "wealth",
        "relationships",
        "caution",
    )

    validated = []

    for position, (
        ai_period,
        fact_period,
    ) in enumerate(
        zip(
            raw_periods,
            expected_periods,
        ),
        start=1,
    ):
        if not isinstance(
            ai_period,
            Mapping,
        ):
            raise ReadingDecadeLuckResponseError(
                f"periods[{position - 1}]が"
                "objectではありません。"
            )

        expected_index = (
            fact_period.get(
                "index"
            )
        )

        ai_index = ai_period.get(
            "index"
        )

        if (
            ai_index
            != expected_index
        ):
            raise ReadingDecadeLuckResponseError(
                "大運indexが"
                "計算済みデータと一致しません。"
                f" expected={expected_index},"
                f" actual={ai_index}"
            )

        clean = {
            "index": ai_index,
        }

        for field in (
            required_text_fields
        ):
            clean[
                field
            ] = (
                _require_non_empty_text(
                    ai_period.get(
                        field
                    ),
                    (
                        f"periods["
                        f"{position - 1}"
                        f"].{field}"
                    ),
                )
            )

        advice = ai_period.get(
            "advice"
        )

        if not isinstance(
            advice,
            list,
        ):
            raise ReadingDecadeLuckResponseError(
                f"periods[{position - 1}]"
                ".adviceはlistで"
                "ある必要があります。"
            )

        if not (
            2
            <= len(
                advice
            )
            <= 3
        ):
            raise ReadingDecadeLuckResponseError(
                f"periods[{position - 1}]"
                ".adviceは2〜3件必要です。"
            )

        clean[
            "advice"
        ] = [
            _require_non_empty_text(
                item,
                (
                    f"periods["
                    f"{position - 1}"
                    "].advice"
                ),
            )
            for item in advice
        ]

        validated.append(
            clean
        )

    return {
        "overview": overview,
        "periods": validated,
        "valid": True,
    }


# ============================================================
# Merge AI interpretation + engine facts
# ============================================================


def merge_decade_luck_result(
    validated: Mapping[
        str,
        Any,
    ],
    facts: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    AI文章へ計算済み大運情報を再結合する。

    protected factsは必ずengine側を採用。
    """

    validated = _require_mapping(
        validated,
        "validated",
    )

    facts = _require_mapping(
        facts,
        "facts",
    )

    ai_periods = _safe_list(
        validated.get(
            "periods"
        )
    )

    fact_periods = _safe_list(
        facts.get(
            "periods"
        )
    )

    if (
        len(
            ai_periods
        )
        != len(
            fact_periods
        )
    ):
        raise ReadingDecadeLuckResponseError(
            "AI結果と大運事実の"
            "件数が一致しません。"
        )

    merged = []

    for ai_period, fact_period in zip(
        ai_periods,
        fact_periods,
    ):
        ai_period = _safe_dict(
            ai_period
        )

        fact_period = _safe_dict(
            fact_period
        )

        # -----------------------------------------------
        # protected facts
        # engine側を必ず正とする
        # -----------------------------------------------

        item = {
            "index": fact_period.get(
                "index"
            ),
            "ganzhi": fact_period.get(
                "ganzhi"
            ),
            "stem": fact_period.get(
                "stem"
            ),
            "branch": fact_period.get(
                "branch"
            ),
            "stem_element": (
                fact_period.get(
                    "stem_element"
                )
            ),
            "branch_element": (
                fact_period.get(
                    "branch_element"
                )
            ),
            "stem_ten_god": (
                fact_period.get(
                    "stem_ten_god"
                )
            ),
            "start_age": (
                fact_period.get(
                    "start_age"
                )
            ),
            "end_age": (
                fact_period.get(
                    "end_age"
                )
            ),
            "stem_useful_relation": (
                _safe_dict(
                    fact_period.get(
                        "stem_useful_relation"
                    )
                )
            ),
            "branch_useful_relation": (
                _safe_dict(
                    fact_period.get(
                        "branch_useful_relation"
                    )
                )
            ),

            # -------------------------------------------
            # AI interpretation
            # -------------------------------------------

            "title": ai_period.get(
                "title"
            ),
            "theme": ai_period.get(
                "theme"
            ),
            "career": ai_period.get(
                "career"
            ),
            "wealth": ai_period.get(
                "wealth"
            ),
            "relationships": (
                ai_period.get(
                    "relationships"
                )
            ),
            "caution": ai_period.get(
                "caution"
            ),
            "advice": _safe_list(
                ai_period.get(
                    "advice"
                )
            ),
        }

        merged.append(
            item
        )

    return {
        "overview": (
            validated.get(
                "overview"
            )
        ),
        "direction": facts.get(
            "direction"
        ),
        "direction_japanese": (
            facts.get(
                "direction_japanese"
            )
        ),
        "start_age": facts.get(
            "start_age"
        ),
        "period_count": len(
            merged
        ),
        "periods": merged,
    }


# ============================================================
# Generation
# ============================================================


def generate_decade_luck_reading(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    count: int = (
        DEFAULT_PERIOD_COUNT
    ),
    max_output_tokens: int = (
        DEFAULT_DECADE_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
) -> ReadingDecadeLuckResult:
    """
    現在＋未来大運のAI鑑定を生成する。
    """

    generation = (
        build_decade_luck_payload(
            reading_context,
            consultation_context=(
                consultation_context
            ),
            model=model,
            count=count,
            max_output_tokens=(
                max_output_tokens
            ),
            reasoning_effort=(
                reasoning_effort
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

    _raise_if_unusable_response(
        response
    )

    text = _extract_output_text(
        response
    )

    parsed = parse_decade_luck_json(
        text
    )

    validated = (
        validate_decade_luck_response(
            parsed,
            generation[
                "facts"
            ],
        )
    )

    merged = merge_decade_luck_result(
        validated,
        generation[
            "facts"
        ],
    )

    metadata = _response_metadata(
        response
    )

    response_status = metadata[
        "response_status"
    ]

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

    return ReadingDecadeLuckResult(
        overview=_text(
            merged.get(
                "overview"
            )
        ),
        periods=tuple(
            deepcopy(
                merged[
                    "periods"
                ]
            )
        ),
        model=generation[
            "model"
        ],
        response_id=metadata[
            "response_id"
        ],
        response_status=(
            response_status
        ),
        usage=_safe_dict(
            metadata[
                "usage"
            ]
        ),
        status=result_status,
    )


def generate_decade_luck_dict(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    count: int = (
        DEFAULT_PERIOD_COUNT
    ),
    max_output_tokens: int = (
        DEFAULT_DECADE_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
) -> Dict[str, Any]:
    """
    dict返却の便利API。
    """

    result = generate_decade_luck_reading(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        client=client,
        api_key=api_key,
        model=model,
        count=count,
        max_output_tokens=(
            max_output_tokens
        ),
        reasoning_effort=(
            reasoning_effort
        ),
        store=store,
    )

    return result.to_dict()


# ============================================================
# Metadata
# ============================================================


def get_reading_decade_luck_metadata(
) -> Dict[str, Any]:
    return {
        "version": (
            READING_DECADE_LUCK_VERSION
        ),
        "method": (
            READING_DECADE_LUCK_METHOD
        ),
        "status": (
            READING_DECADE_LUCK_STATUS
        ),
        "default_period_count": (
            DEFAULT_PERIOD_COUNT
        ),
        "default_max_output_tokens": (
            DEFAULT_DECADE_MAX_OUTPUT_TOKENS
        ),
        "recalculates_astrology": False,
        "ai_controls_protected_facts": False,
    }


# ============================================================
# Public API
# ============================================================


__all__ = [
    "READING_DECADE_LUCK_VERSION",
    "READING_DECADE_LUCK_METHOD",
    "READING_DECADE_LUCK_STATUS",
    "DEFAULT_PERIOD_COUNT",
    "DEFAULT_DECADE_MAX_OUTPUT_TOKENS",
    "ReadingDecadeLuckError",
    "ReadingDecadeLuckDataError",
    "ReadingDecadeLuckResponseError",
    "ReadingDecadeLuckResult",
    "select_decade_luck_periods",
    "build_decade_luck_facts",
    "build_decade_interpretation_context",
    "build_decade_luck_output_schema",
    "build_decade_luck_prompt",
    "build_decade_luck_payload",
    "parse_decade_luck_json",
    "validate_decade_luck_response",
    "merge_decade_luck_result",
    "generate_decade_luck_reading",
    "generate_decade_luck_dict",
    "get_reading_decade_luck_metadata",
]
