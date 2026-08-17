import jwt
import os

from dotenv import load_dotenv
from datetime import datetime, timedelta
from passlib.context import CryptContext
from core.user_repository import create_user,get_user_by_username
from fastapi import Depends, HTTPException, Header

load_dotenv()

# ========== JWT 配置（从环境变量读取） ==========
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 第二个参数是默认值
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", 1440))

def create_token(user_uuid: str) -> str:
    """生成 JWT token"""
    payload = {
        "sub": user_uuid,  # 用户标识（用 uuid）
        "exp": datetime.now() + timedelta(minutes=TOKEN_EXPIRE_MINUTES),  # 过期时间
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    """校验 token，返回 user_uuid；无效返回 None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        return None

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def register(username, password, nickname=""):
    password_hash = hash_password(password)
    user_uuid = create_user(username, password_hash, nickname)  # 返回 uuid
    token = create_token(user_uuid)  # 用 uuid 生成 token
    return {"user_uuid": user_uuid, "token": token}


def login(username, password):
    user = get_user_by_username(username)
    print(f"user 类型: {type(user)}")
    print(f"user 内容: {user}")
    if not user:
        raise ValueError("用户名不存在")
    if not verify_password(password, user["password_hash"]):
        raise ValueError("密码错误")
    if user["status"] == "deleted":
        raise ValueError("账号已注销")
    token = create_token(user["user_uuid"])
    return {"user_uuid": user["user_uuid"], "token": token}



def get_current_user(authorization: str = Header(None)):
  """依赖：校验 token，返回 user_uuid"""
  if not authorization or not authorization.startswith("Bearer "):
      raise HTTPException(status_code=401, detail="未提供token")
  token = authorization.replace("Bearer ", "")
  user_uuid = verify_token(token)
  if not user_uuid:
      raise HTTPException(status_code=401, detail="token无效或已过期")
  return user_uuid