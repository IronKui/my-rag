import os
import uuid
import logging
from fastapi import FastAPI,UploadFile,Form

logger = logging.getLogger(__name__)
from core.agent import agent_chat
from core.rag import process_and_store
from schemas import ChatRequest,ChatResponse
from fastapi.middleware.cors import CORSMiddleware
from core.auth_service import register,login,get_current_user
from core.user_repository import create_session, get_sessions_by_user, get_session_by_id, update_session_time, delete_session, save_message, get_messages_by_session, rename_session, get_user_files, get_user_file_by_id, soft_delete_file
from core.rag import get_vectorstore
from core.cache import clear_user_cache
from schemas import RegisterRequest,LoginRequest,RenameRequest
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
    # 延迟创建：session_id 为空或 "default" 时，创建新会话（用第一条消息命名）
    if not data.session_id or data.session_id == "default":
        new_session_id = f"sess_{uuid.uuid4().hex[:12]}"
        create_session(user_uuid, new_session_id, data.question)
        session_id = new_session_id
    else:
        session_id = data.session_id
        # 校验会话归属 + 更新时间
        if not get_session_by_id(user_uuid, session_id):
            return {"code": 1, "message": "会话不存在或无权限", "data": None}
        update_session_time(user_uuid, session_id)

    response = agent_chat(data.question, data.mode, session_id, user_uuid)
    # 保存完整对话历史（用户可见，不受上下文压缩影响）
    save_message(user_uuid, session_id, "user", data.question)
    save_message(user_uuid, session_id, "assistant", response)
    return {
        "code": 0,
        "message": "成功",
        "data": {"answer": response, "session_id": session_id}
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

@app.get("/api/sessions")
def api_sessions(user_uuid: str = Depends(get_current_user)):
    """获取当前用户的会话列表，按更新时间倒序"""
    sessions = get_sessions_by_user(user_uuid)
    return {
        "code": 0,
        "message": "成功",
        "data": [
            {
                "session_id": s["session_id"],
                "session_name": s["session_name"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"]
            }
            for s in sessions
        ]
    }

@app.get("/api/sessions/{session_id}/history")
def api_session_history(session_id: str, user_uuid: str = Depends(get_current_user)):
    """获取某会话的历史消息（从 messages 表读完整历史，不受压缩影响）"""
    # 校验会话归属
    if not get_session_by_id(user_uuid, session_id):
        return {"code": 1, "message": "会话不存在或无权限", "data": None}
    messages = get_messages_by_session(user_uuid, session_id)
    history = [{"role": m["role"], "content": m["content"]} for m in messages]
    return {
        "code": 0,
        "message": "成功",
        "data": {"messages": history}
    }

@app.put("/api/sessions/{session_id}")
def api_rename_session(session_id: str, data: RenameRequest, user_uuid: str = Depends(get_current_user)):
    """重命名会话"""
    if not get_session_by_id(user_uuid, session_id):
        return {"code": 1, "message": "会话不存在或无权限", "data": None}
    rename_session(user_uuid, session_id, data.session_name)
    return {"code": 0, "message": "会话已重命名", "data": None}

@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str, user_uuid: str = Depends(get_current_user)):
    """删除会话"""
    if not get_session_by_id(user_uuid, session_id):
        return {"code": 1, "message": "会话不存在或无权限", "data": None}
    delete_session(user_uuid, session_id)
    return {"code": 0, "message": "会话已删除", "data": None}

@app.get("/api/files")
def api_files(user_uuid: str = Depends(get_current_user)):
    """获取当前用户的文件列表"""
    files = get_user_files(user_uuid)
    return {
        "code": 0,
        "message": "成功",
        "data": [
            {
                "id": f["id"],
                "filename": f["filename"],
                "file_hash": f["file_hash"],
                "file_size": f["file_size"],
                "chunk_count": f["chunk_count"],
                "scope": f["scope"],
                "session_id": f["session_id"],
                "created_at": f["created_at"]
            }
            for f in files
        ]
    }

@app.delete("/api/files/{file_id}")
def api_delete_file(file_id: int, user_uuid: str = Depends(get_current_user)):
    """删除文件：先删向量，再软删记录"""
    file = get_user_file_by_id(user_uuid, file_id)
    if not file:
        return {"code": 404, "message": "文件不存在或无权限", "data": None}
    if file["status"] == "deleted":
        return {"code": 400, "message": "文件已删除", "data": None}

    # 1. 从向量库物理删除（按 file_hash 删该文件的所有向量块）
    try:
        vs = get_vectorstore()
        vs.delete(where={"file_hash": file["file_hash"]})
    except Exception as e:
        logger.error(f"向量删除失败: {e}")
        return {"code": 500, "message": "删除失败，请稍后重试", "data": None}

    # 2. 软删文件记录
    soft_delete_file(user_uuid, file_id)
    # 3. 清缓存（知识库变动，避免旧检索结果）
    clear_user_cache(user_uuid)
    return {"code": 0, "message": "文件已删除", "data": None}