import os
from fastapi import FastAPI,UploadFile,Form
from core.agent import agent_chat
from core.rag import process_and_store
from schemas import ChatRequest,ChatResponse
from fastapi.middleware.cors import CORSMiddleware
#uvicorn app:app --reload
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发阶段）
    allow_methods=["*"],  # 允许所有方法（GET/POST等）
    allow_headers=["*"],  # 允许所有请求头
)
os.makedirs("uploads", exist_ok=True)
@app.post("/api/chat",response_model=ChatResponse)
async def chat(data:ChatRequest):
    response = agent_chat(data.question, data.mode, data.session_id,data.user_id)
    return {
        "code": 0,
        "message": "成功",
        "data": {"answer": response}
    }

@app.post("/api/upload")
async def upload(file:UploadFile,session_id:str = Form("default"), user_id: str = Form("default")):
    file_path = f"./uploads/{file.filename}"
    with open(file_path,"wb")as f:
        f.write(await file.read())
    # rag操作
    chunk_count, status =process_and_store(file_path,user_id)

    if status == "duplicate":
        return {"code": 1, "message": "文件已存在，未重复入库", "data": {"file_name":
                                                                            file.filename}}

    return {
        "code": 0,
        "message": "上传成功",
        "data": {"file_name": file.filename, "chunk_count": chunk_count}
    }