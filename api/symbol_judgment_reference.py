"""Optional customer-Web sidecar for the B research reference evaluation.

This module does not alter the frozen reading product or the existing reading
body.  The server-side flag is deliberately off unless explicitly enabled.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from html import escape
import os
from typing import Any

from scripts.symbol_judgment_b_production_adapter import (
    ADAPTER_VERSION,
    DISPLAY_NAME,
    run_reference_evaluation,
)


FEATURE_FLAG_ENV = "YAKUMO_B_REFERENCE_EVALUATION_ENABLED"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})

_REFERENCE_CSS = """
<style>
.yakumo-reference{margin:28px auto;max-width:900px;padding:24px;border:1px solid #d8c5ad;border-radius:12px;background:#fffaf1;color:#302820}
.yakumo-reference h2{margin:0 0 8px;color:#5d3b25}.yakumo-reference-note{color:#75685c;margin:0 0 18px}
.yakumo-reference-state{display:inline-block;margin:0 0 14px;padding:4px 9px;border-radius:999px;background:#eee2d3;font-weight:700}
.yakumo-reference-state--error{background:#f8deda;color:#862f2b}.yakumo-reference-state--hold{background:#eee7d5;color:#67521e}
.yakumo-reference-list{display:grid;gap:12px}.yakumo-reference-item{padding:14px;border:1px solid #e5d8c8;border-radius:9px;background:#fff}
.yakumo-reference-item h3{margin:0 0 7px;font-size:1.05rem}.yakumo-reference-symbol{display:inline-block;min-width:5.5em;color:#5d3b25;font-weight:700}
.yakumo-reference-item p{margin:5px 0}.yakumo-reference-meta{font-size:.9rem;color:#75685c;overflow-wrap:anywhere}
.yakumo-reference-foot{margin:16px 0 0;font-size:.9rem;color:#75685c}
@media(max-width:680px){.yakumo-reference{margin:20px 0;padding:18px}.yakumo-reference-item{padding:12px}}
</style>
"""


def reference_evaluation_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return True only for an explicit server-side opt-in value."""
    source = os.environ if environ is None else environ
    return source.get(FEATURE_FLAG_ENV, "").strip().lower() in _TRUE_VALUES


def _disabled_sidecar() -> dict[str, Any]:
    return {"status": "disabled", "enabled": False, "adapter": ADAPTER_VERSION, "display": None}


def _error_sidecar(exc: Exception) -> dict[str, Any]:
    exception_type = type(exc).__name__
    return {
        "status": "error",
        "enabled": True,
        "adapter": ADAPTER_VERSION,
        "error": {"type": exception_type},
        "display": {
            "display_name": DISPLAY_NAME,
            "status": "error",
            "items": [{
                "symbol": None,
                "display_symbol": "評価エラー",
                "target": "全体",
                "reason": f"参考評価の処理に失敗しました（{exception_type}）。既存の鑑定結果はそのまま表示しています。",
                "applied_rules": [],
                "assumptions": [],
            }],
            "model_version": "取得不能",
            "uncertainties": ["Bモデル評価処理に失敗"],
            "notice": "研究用の参考評価です。記号だけで転職・投資その他の意思決定を勧めません。",
        },
    }


def build_reference_sidecar(
    engine_result: Any,
    *,
    enabled: bool | None = None,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the research boundary only when the server flag is enabled."""
    active = reference_evaluation_enabled() if enabled is None else enabled
    if not active:
        return _disabled_sidecar()
    try:
        evaluator = run_reference_evaluation if runner is None else runner
        return dict(evaluator(engine_result, enabled=True))
    except Exception as exc:  # An integration fault must not replace the reading.
        return _error_sidecar(exc)


def _text(value: Any, fallback: str = "―") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value), quote=True)


def render_reference_sidecar_html(sidecar: Mapping[str, Any]) -> str:
    """Render customer-Web-only HTML; disabled output is intentionally empty."""
    status = sidecar.get("status")
    if status == "disabled":
        return ""
    display = sidecar.get("display")
    if not isinstance(display, Mapping):
        display = _error_sidecar(RuntimeError("missing display payload"))["display"]
        status = "error"

    state_label = {"success": "参考評価", "hold": "判定保留", "error": "評価エラー"}.get(
        str(status), "判定保留"
    )
    state_class = "error" if status == "error" else "hold" if status == "hold" else "success"
    rendered_items: list[str] = []
    items = display.get("items", [])
    if not isinstance(items, list):
        items = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        symbol = item.get("symbol")
        shown_symbol = symbol if symbol in {"○", "△", "×"} else item.get("display_symbol", "判定保留")
        reason = item.get("reason")
        if symbol == "◎":
            # AGENTS.md forbids publishing ◎ until its rule is established.
            # Keep the research score untouched, but never expose it as a
            # customer-facing established mark.
            shown_symbol = "判定保留"
            reason = (
                "最高評価候補ですが、その判定規則が未確立のため顧客表示を保留します。"
                f" 研究モデルの算定理由: {reason or '理由未記載'}"
            )
        if status == "error":
            shown_symbol = "評価エラー"
        rules = item.get("applied_rules", [])
        rules_text = "、".join(str(rule) for rule in rules) if isinstance(rules, list) and rules else "なし"
        assumptions = item.get("assumptions", [])
        assumption_texts = []
        if isinstance(assumptions, list):
            for assumption in assumptions:
                if isinstance(assumption, Mapping):
                    assumption_texts.append(
                        f"{assumption.get('rule_id', '規則不明')}: {assumption.get('basis', '根拠未記載')}"
                    )
        assumptions_text = " / ".join(assumption_texts) if assumption_texts else "なし（明示された研究用仮定なし）"
        rendered_items.append(
            '<article class="yakumo-reference-item">'
            f'<h3><span class="yakumo-reference-symbol">{_text(shown_symbol)}</span>{_text(item.get("target"), "全体")}</h3>'
            f'<p><strong>理由・根拠：</strong>{_text(reason, "判定根拠を確定できませんでした。")}</p>'
            f'<p class="yakumo-reference-meta"><strong>適用規則：</strong>{_text(rules_text)}</p>'
            f'<p class="yakumo-reference-meta"><strong>研究用仮定：</strong>{_text(assumptions_text)}</p>'
            '</article>'
        )
    if not rendered_items:
        rendered_items.append(
            '<article class="yakumo-reference-item"><h3><span class="yakumo-reference-symbol">判定保留</span>全体</h3>'
            '<p><strong>理由・根拠：</strong>表示可能な参考評価がありません。</p></article>'
        )
    uncertainties = display.get("uncertainties", [])
    uncertainty_text = " / ".join(str(value) for value in uncertainties) if isinstance(uncertainties, list) and uncertainties else "なし"
    return (
        _REFERENCE_CSS
        + '<section class="yakumo-reference" aria-labelledby="yakumo-reference-title">'
        + f'<h2 id="yakumo-reference-title">{_text(display.get("display_name"), DISPLAY_NAME)}</h2>'
        + '<p class="yakumo-reference-note">原典観測とは区別した、八雲式の研究用参考評価です。</p>'
        + f'<p class="yakumo-reference-state yakumo-reference-state--{state_class}">{_text(state_label)}</p>'
        + f'<div class="yakumo-reference-list">{"".join(rendered_items)}</div>'
        + f'<p class="yakumo-reference-foot"><strong>モデル：</strong>{_text(display.get("model_version"))}<br>'
        + f'<strong>未対応・不確実性：</strong>{_text(uncertainty_text)}<br>{_text(display.get("notice"))}</p>'
        + '</section>'
    )


def _engine_result_from_product(product: Any) -> Any:
    if isinstance(product, Mapping):
        return product.get("engine_result")
    to_dict = getattr(product, "to_dict", None)
    if callable(to_dict):
        snapshot = to_dict()
        if isinstance(snapshot, Mapping):
            return snapshot.get("engine_result")
    return None


def append_reference_sidecar(
    document: str,
    engine_result: Any,
    *,
    enabled: bool | None = None,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> str:
    """Append an isolated sidecar without allowing failures to remove the reading."""
    try:
        sidecar = build_reference_sidecar(engine_result, enabled=enabled, runner=runner)
        fragment = render_reference_sidecar_html(sidecar)
    except Exception:  # Rendering itself must never replace the existing reading.
        return document
    if not fragment:
        return document
    marker = "</body>"
    return document.replace(marker, fragment + marker, 1) if marker in document else document + fragment


def append_product_reference_sidecar(document: str, product: Any, *, enabled: bool | None = None) -> str:
    active = reference_evaluation_enabled() if enabled is None else enabled
    if not active:
        return document
    try:
        engine_result = _engine_result_from_product(product)
    except Exception as exc:
        fragment = render_reference_sidecar_html(_error_sidecar(exc))
        return document.replace("</body>", fragment + "</body>", 1) if "</body>" in document else document + fragment
    return append_reference_sidecar(document, engine_result, enabled=True)


__all__ = [
    "FEATURE_FLAG_ENV", "append_product_reference_sidecar", "append_reference_sidecar",
    "build_reference_sidecar", "reference_evaluation_enabled", "render_reference_sidecar_html",
]
