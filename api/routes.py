"""
api/routes.py

四柱推命 API ルーター。

既存API
-------
POST /api/v1/chart
    命式計算API

追加API
-------
GET /reading/status
    AI鑑定APIの状態確認

POST /reading
    命式計算からAI鑑定生成までを実行

設計方針
--------
・既存の /api/v1/chart を変更しない
・AI鑑定APIは api.reading_routes に分離する
・このファイルでは各routerを統合するだけにする
"""

from fastapi import APIRouter

from api.models import ChartRequest
from api.reading_routes import (
    router as reading_router,
)
from engine.chart import (
    calculate_chart,
)


# ============================================================
# Main router
# ============================================================


router = APIRouter()


# ============================================================
# Existing chart API
# ============================================================


@router.post(
    "/api/v1/chart",
    operation_id="calculateShichusuimeiChart",
)
def chart(
    req: ChartRequest,
):
    """
    四柱推命の命式を計算する。

    AI鑑定は行わず、
    engine.chart の計算結果を返す。
    """

    return {
        "success": True,
        "result": calculate_chart(
            req
        ),
    }


# ============================================================
# AI reading API
# ============================================================


router.include_router(
    reading_router
)


# ============================================================
# Public API
# ============================================================


__all__ = [
    "router",
]
