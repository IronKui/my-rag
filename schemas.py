from pydantic import BaseModel
from typing import Literal
 # ====== agent请求模型 ======
class ChatRequest(BaseModel):
    question:str
    mode: Literal["default", "learning", "interview", "roleplay"] = "default"
    session_id:str = "default"
class ChatResponse(BaseModel):
    code:int = 0
    message:str ="成功"
    data:dict

  # ====== 账号请求模型 ======
class RegisterRequest(BaseModel):
  username: str
  password: str
  nickname: str = ""

class LoginRequest(BaseModel):
  username: str
  password: str

class RenameRequest(BaseModel):
  session_name: str


