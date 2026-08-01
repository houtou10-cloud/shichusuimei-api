from fastapi import APIRouter
from api.models import ChartRequest
from engine.chart import calculate_chart

router=APIRouter()

@router.post("/api/v1/chart")
def chart(req: ChartRequest):
    return {"success":True,"result":calculate_chart(req)}
