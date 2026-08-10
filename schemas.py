from pydantic import BaseModel
from typing import Literal
#请求模型
class ChatRequest(BaseModel):
    question:str
    mode: Literal["default", "learning", "interview", "roleplay"] = "default"
    session_id:str = "default"
    user_id:str="default"
class ChatResponse(BaseModel):
    code:int = 0
    message:str ="成功"
    data:dict

