"""
文件索引管理模块
按用户维护文件索引（JSON 文件），用于去重判断、同名重命名、溯源。
索引目录：./data/indexes/{user_id}_index.json
"""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime

INDEX_DIR = Path("./data/indexes")
INDEX_DIR.mkdir(parents=True, exist_ok=True)


def get_index_path(user_id: str) -> Path:
    """获取某用户的索引文件路径"""
    return INDEX_DIR / f"{user_id}_index.json"


def load_index(user_id: str) -> dict:
    """加载某用户的索引，文件不存在时返回空结构"""
    path = get_index_path(user_id)
    if not path.exists():
        return {"files": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(user_id: str, index: dict):
    """保存某用户的索引"""
    path = get_index_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def get_file_by_hash(user_id: str, file_hash: str) -> dict | None:
    """按内容哈希查找文件（硬重复判断）"""
    index = load_index(user_id)
    return index["files"].get(file_hash)


def get_file_by_source(user_id: str, source: str) -> dict | None:
    """按原始文件名查找（同名判断）"""
    index = load_index(user_id)
    for f in index["files"].values():
        if f["filename"] == source:
            return f
    return None


def add_file_to_index(user_id: str, file_hash: str, file_info: dict):
    """新文件入库后，更新索引"""
    index = load_index(user_id)
    index["files"][file_hash] = file_info
    save_index(user_id, index)


def auto_rename(source: str) -> str:
    """同名文件自动重命名：笔记.pdf → 笔记(1).pdf → 笔记(2).pdf"""
    p = Path(source)
    stem = p.stem
    suffix = p.suffix

    # 如果已是 笔记(1) 这种格式，提取编号
    num = 1
    if "(" in stem and stem.endswith(")"):
        try:
            num = int(stem[stem.rfind("(") + 1:-1]) + 1
            base = stem[:stem.rfind("(")].strip()
        except ValueError:
            num = 1
            base = stem
    else:
        base = stem

    return f"{base}({num}){suffix}"


def compute_file_hash(filepath: str) -> str:
    """计算文件内容的 SHA-256 哈希"""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
