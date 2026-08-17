import sqlite3
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR/"data/users.db"

def get_connection():
    """
    获取数据库连接
    """
    conn = sqlite3.connect(str(DB_DIR))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    初始化数据库，建表
    """
    conn =get_connection()
    cur =conn.cursor()

    #user表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_uuid TEXT NOT NULL UNIQUE ,
        username TEXT NOT NULL UNIQUE,
        nickname TEXT DEFAULT '',
        password_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    #session 表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()
    print("数据库初始话完毕")


def create_user(username: str, password_hash: str, nickname: str = "") -> str:
    """插入新用户，没传昵称自动生成，返回用户id"""
    #查重
    if get_user_by_username(username):
        raise ValueError(f"该用户名已被占用")

    #没有昵称就用用户名
    if not nickname:
        nickname = f"用户{username}"

    #生成uuid
    user_uuid = str(uuid.uuid4())

    #插入执行
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(user_uuid, username ,nickname,password_hash) VALUES (?,?,?,?)",
            (user_uuid, username, nickname, password_hash)
        )
        conn.commit()
        return user_uuid
    except sqlite3.IntegrityError as e:
        # 极低概率：user_uuid 冲突
        raise RuntimeError("注册失败，请重试")
    finally:
        conn.close()

def get_user_by_username(username: str, include_deleted: bool = False):
    conn = get_connection()
    cur = conn.cursor()
    if include_deleted:
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    else:
        cur.execute("SELECT * FROM users WHERE username = ? AND status = 'active'", (username,))
    user = cur.fetchone()
    conn.close()
    return user