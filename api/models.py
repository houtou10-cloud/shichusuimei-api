from pydantic import BaseModel
from typing import Optional

class ChartRequest(BaseModel):
    birth_date:str
    birth_time:Optional[str]=None
    birth_place:str
    gender:str
