import os
from fastapi import FastAPI,UploadFile,Form
from core.agent import agent_chat
from schemas import ChatRequest
#uvicorn app:app --reload
app = FastAPI()
os.makedirs("uploads", exist_ok=True)
@app.post("/api/chat")
async def chat(data:ChatRequest):
    response = agent_chat(data.question,data.session_id)
    return {
        "question":f"你说了： {data.question}",
        "answer":f"助手回复： {response}"
    }

@app.post("/api/upload")
async def upload(file:UploadFile,session_id:str = Form("default")):
    file_path = f"./uploads/{file.filename}"
    with open(file_path,"wb")as f:
        f.write(await file.read())
    return {
        "code":0,
        "message":"上传成功",
        "data":{"file_name":file.filename}
    }