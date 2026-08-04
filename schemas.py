from pydantic import BaseModel

#请求模型
class ChatRequest(BaseModel):
    question:str
    session_id:str = "default"

class ChatResponse(BaseModel):
    code:int = 0
    message:str ="成功"
    data:dict

