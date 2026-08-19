import os
from fastapi import FastAPI,UploadFile,Form
from core.agent import agent_chat
from core.rag import process_and_store
from schemas import ChatRequest,ChatResponse
from fastapi.middleware.cors import CORSMiddleware
from core.auth_service import register,login,get_current_user
from schemas import RegisterRequest,LoginRequest
from contextlib import asynccontextmanager
from core.user_repository import init_db
from fastapi import Depends

#uvicorn app:app --reload

@asynccontextmanager
async def lifespan(app):
    """应用启动时初始化数据库"""
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发阶段）
    allow_methods=["*"],  # 允许所有方法（GET/POST等）
    allow_headers=["*"],  # 允许所有请求头
)
os.makedirs("uploads", exist_ok=True)

@app.post("/api/chat",response_model=ChatResponse)
async def chat(data:ChatRequest, user_uuid: str = Depends(get_current_user)):
    response = agent_chat(data.question, data.mode, data.session_id,user_uuid)
    return {
        "code": 0,
        "message": "成功",
        "data": {"answer": response}
    }

@app.post("/api/upload")
async def upload(file:UploadFile, session_id:str = Form("default"), scope:str = Form("account"),
                 user_uuid: str = Depends(get_current_user)):
    file_path = f"./uploads/{file.filename}"
    with open(file_path,"wb")as f:
        f.write(await file.read())
    # rag操作（scope: account=账号级共享 / session=会话级）
    chunk_count, status =process_and_store(file_path, user_uuid, scope, session_id)

    if status == "duplicate":
        return {"code": 1, "message": "文件已存在，未重复入库", "data": {"file_name":
                                                                            file.filename}}

    return {
        "code": 0,
        "message": "上传成功",
        "data": {"file_name": file.filename, "chunk_count": chunk_count}
    }

@app.post("/api/register")
def api_register(data: RegisterRequest):
    try:
        result = register(data.username, data.password, data.nickname)
        return {"code": 0, "message": "注册成功", "data": result}
    except ValueError as e:
        return {"code": 1, "message": str(e), "data": None}
    except RuntimeError as e:   # ← 单独处理系统错误
        return {"code": 500, "message": str(e), "data": None}


@app.post("/api/login")
def api_login(data: LoginRequest):
  try:
      result = login(data.username, data.password)
      return {"code": 0, "message": "登录成功", "data": result}
  except ValueError as e:
      return {"code": 1, "message": str(e), "data": None}

@app.get("/api/me")
def api_me(user_uuid: str = Depends(get_current_user)):
    """测试接口：返回当前登录用户的 UUID"""
    return {
        "code": 0,
        "message": "认证成功",
        "data": {"user_uuid": user_uuid}
    }