"""
Redis 缓存模块
用于热点检索结果缓存，提升重复查询响应速度。
"""
import json
import hashlib

import redis
from langchain_core.documents import Document

from core.logger import setup_logger

logger = setup_logger(__name__)

# Redis 连接
_redis_client = None
CACHE_TTL = 300  # 缓存 5 分钟


def get_redis_client():
    """获取 Redis 客户端（懒加载单例）"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True, protocol=2)
            _redis_client.ping()  # 验证连接
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败，缓存功能禁用: {e}")
            _redis_client = None
    return _redis_client


def _build_key(user_id: str, session_id: str, query: str, k: int) -> str:
    """构建缓存 key：包含用户/会话维度，防止数据串"""
    query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
    return f"rag:{user_id}:{session_id}:{query_hash}:{k}"


def _doc_to_dict(doc: Document) -> dict:
    """Document → dict（序列化）"""
    return {"page_content": doc.page_content, "metadata": doc.metadata}


def _dict_to_doc(d: dict) -> Document:
    """dict → Document（反序列化）"""
    return Document(page_content=d["page_content"], metadata=d.get("metadata", {}))


def get_cached_search(user_id: str, session_id: str, query: str, k: int):
    """从缓存读取检索结果，未命中返回 None"""
    client = get_redis_client()
    if not client:
        return None
    key = _build_key(user_id, session_id, query, k)
    try:
        data = client.get(key)
        if data:
            logger.info(f"[cache] 命中缓存: {query[:30]}...")
            doc_dicts = json.loads(data)
            return [_dict_to_doc(d) for d in doc_dicts]
    except Exception as e:
        logger.warning(f"[cache] 读取缓存失败: {e}")
    return None


def set_cached_search(user_id: str, session_id: str, query: str, k: int, results: list):
    """写入检索结果缓存"""
    client = get_redis_client()
    if not client:
        return
    key = _build_key(user_id, session_id, query, k)
    try:
        doc_dicts = [_doc_to_dict(d) for d in results]
        client.setex(key, CACHE_TTL, json.dumps(doc_dicts, ensure_ascii=False))
        logger.info(f"[cache] 写入缓存: {query[:30]}...")
    except Exception as e:
        logger.warning(f"[cache] 写入缓存失败: {e}")


def clear_user_cache(user_id: str):
    """清空某用户的缓存（文件变动时调用，避免旧数据）"""
    client = get_redis_client()
    if not client:
        return
    try:
        # 删除该用户前缀的所有 key
        keys = client.keys(f"rag:{user_id}:*")
        if keys:
            client.delete(*keys)
            logger.info(f"[cache] 清空用户 {user_id} 的缓存，共 {len(keys)} 条")
    except Exception as e:
        logger.warning(f"[cache] 清空缓存失败: {e}")
